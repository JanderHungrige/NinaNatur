"""The surroundings of a garden made before they were fetched (doc 114).

They come on the shade rebuild, from the stored anchor — rounded to four
places, so a few metres off the streets and houses the import placed from the
exact one. Where the garden holds OpenStreetMap's streets, the offset is read
off them.
"""
from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterator
from contextlib import nullcontext
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import geo as geo_routes
from ninanatur.api import ratelimit
from ninanatur.api.deps import get_connection
from ninanatur.garden import landcover_sync
from ninanatur.garden.landcover_sync import street_offset
from ninanatur.geo.osm_landcover import OsmArea
from ninanatur.geo.osm_streets import OsmStreet
from ninanatur.geo.projection import LatLon, Metres, centroid, to_latlon
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

BED = {"name": "Beet", "polygon": [[0, 0], [6, 0], [6, 4], [0, 4]],
       "soil_type": "loam", "moisture": "fresh"}
OUTLINE = [
    {"lat": 52.4055, "lon": 13.2100},
    {"lat": 52.4055, "lon": 13.21029},
    {"lat": 52.40568, "lon": 13.21029},
    {"lat": 52.40568, "lon": 13.2100},
]
EXACT = centroid([LatLon(p["lat"], p["lon"]) for p in OUTLINE])
STORED = LatLon(round(EXACT.lat, 4), round(EXACT.lon, 4))
#: A bending lane south of the plot, as OpenStreetMap has it.
LANE = OsmStreet(osm_id=5, name="Am Weinberg", width_m=6.0, centreline=[
    to_latlon(Metres(x, y), EXACT) for x, y in ((-60, -25), (-20, -22), (15, -26), (55, -31))])


@pytest.fixture()
def conn(monkeypatch: pytest.MonkeyPatch) -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    app.dependency_overrides[get_connection] = lambda: made
    # The fetch runs after the answer, on a connection of its own: here, this one.
    monkeypatch.setattr(landcover_sync, "background_connection", lambda: nullcontext(made))
    yield made
    app.dependency_overrides.clear()


def _asking(monkeypatch: pytest.MonkeyPatch, areas: list[OsmArea]) -> list[LatLon]:
    """Stub the fetch with these areas; the centres it was asked about."""
    asked: list[LatLon] = []

    def landcover(*_box: float, centre: LatLon, **_k: Any) -> list[OsmArea]:
        asked.append(centre)
        return areas

    monkeypatch.setattr(landcover_sync, "landcover_in", landcover)
    return asked


def _drawn(client: TestClient, latitude: float, longitude: float) -> str:
    token = str(client.post("/api/v1/gardens", json={
        "name": "G", "latitude": latitude, "longitude": longitude}).json()["share_token"])
    client.post(f"/api/v1/gardens/{token}/beds", json=BED)
    return token


def test_a_rebuild_fetches_them_once_for_a_garden_that_has_none(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = _asking(monkeypatch, [])
    client = TestClient(app)
    token = _drawn(client, 52.5171, 13.3889)
    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 200
    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 200
    # Nothing mapped is an answer too, and is not asked for again.
    assert asked == [LatLon(52.5171, 13.3889)]
    assert conn.execute("SELECT placed_by FROM garden_landcover").fetchone()[0] == "anchor"


def test_a_garden_from_before_the_precise_anchor_gets_none(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Its stored place is up to 6.6 km off; its neighbourhood would be another's."""
    asked = _asking(monkeypatch, [])
    client = TestClient(app)
    token = _drawn(client, 52.5, 13.4)
    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 200
    assert asked == []


def test_a_failed_fetch_leaves_the_light_alone_and_waits_before_asking_again(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every press used to pay for the failure again, with retries, while
    somebody waited for the light (review, 2026-09-21)."""
    calls = {"n": 0}

    def refuse(*_a: Any, **_k: Any) -> list[OsmArea]:
        calls["n"] += 1
        raise RuntimeError("Overpass sagt nein")

    monkeypatch.setattr(landcover_sync, "landcover_in", refuse)
    client = TestClient(app)
    token = _drawn(client, 52.5171, 13.3889)
    first = client.post(f"/api/v1/gardens/{token}/light")
    assert first.status_code == 200 and first.json() is not None
    client.post(f"/api/v1/gardens/{token}/light")
    assert calls["n"] == 1, "a failure is not asked again straight away"
    monkeypatch.setattr(landcover_sync, "FAILURE_PAUSE_S", 0)
    client.post(f"/api/v1/gardens/{token}/light")
    assert calls["n"] == 2, "and is asked again once the pause is over"


def test_a_new_garden_does_not_inherit_a_deleted_ones_pause(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SQLite gives a deleted garden's id to the next one; the pause is the old
    garden's, not the id's (review, 2026-09-21)."""
    monkeypatch.setattr(landcover_sync, "landcover_in", _refuse)
    client = TestClient(app)
    first = _drawn(client, 52.5171, 13.3889)
    client.post(f"/api/v1/gardens/{first}/light")
    assert client.delete(f"/api/v1/gardens/{first}").status_code == 204
    asked = _asking(monkeypatch, [])
    second = _drawn(client, 52.5171, 13.3889)
    assert conn.execute("SELECT garden_id FROM garden").fetchone()[0] == 1, "the same id"
    client.post(f"/api/v1/gardens/{second}/light")
    assert len(asked) == 1


def test_the_fetch_after_the_answer_holds_no_heavy_slot(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The slots are for computing. A request-scoped slot lived until the
    background task had finished waiting on Overpass (review, 2026-09-21)."""
    free: list[int] = []

    def landcover(*_box: float, **_k: Any) -> list[OsmArea]:
        free.append(ratelimit.HEAVY._value)  # type: ignore[attr-defined]
        return []

    monkeypatch.setattr(landcover_sync, "landcover_in", landcover)
    client = TestClient(app)
    token = _drawn(client, 52.5171, 13.3889)
    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 200
    assert free == [ratelimit.HEAVY_SLOTS]


def test_a_second_press_while_the_first_fetch_waits_asks_no_second_time(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The slot no longer holds the fetch, so nothing stopped a press during a
    slow Overpass from fetching the same land again (review, 2026-09-21)."""
    client = TestClient(app)
    token = _drawn(client, 52.5171, 13.3889)
    calls: list[LatLon] = []

    def slow(*_box: float, centre: LatLon, **_k: Any) -> list[OsmArea]:
        calls.append(centre)
        if len(calls) == 1:
            landcover_sync.fetch_later(token)  # the second press, meanwhile
        return []

    monkeypatch.setattr(landcover_sync, "landcover_in", slow)
    landcover_sync.fetch_later(token)
    assert len(calls) == 1


def test_no_more_than_two_fetches_run_at_once(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each holds a server thread while Overpass is slow; beyond the room, a
    fetch is skipped, and no failure is recorded for it."""
    client = TestClient(app)
    tokens = [_drawn(client, 52.5171 + i / 1000, 13.3889) for i in range(3)]
    started: list[float] = []

    def nested(*_box: float, centre: LatLon, **_k: Any) -> list[OsmArea]:
        started.append(centre.lat)
        if len(started) < len(tokens):
            landcover_sync.fetch_later(tokens[len(started)])
        return []

    monkeypatch.setattr(landcover_sync, "landcover_in", nested)
    landcover_sync.fetch_later(tokens[0])
    assert len(started) == landcover_sync.MAX_BACKGROUND_FETCHES == 2
    assert tokens[2] not in landcover_sync._failed_at


def test_a_garden_replaced_while_its_land_was_fetched_gets_none_of_it(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deleted during the fetch, its id went to a new garden elsewhere: the old
    garden's land must not become the new one's, nor its failure the new one's
    pause (review, 2026-09-21)."""
    client = TestClient(app)
    old = _drawn(client, 52.5171, 13.3889)
    new: list[str] = []

    def replaced(*_box: float, **_k: Any) -> list[OsmArea]:
        client.delete(f"/api/v1/gardens/{old}")
        new.append(_drawn(client, 48.1374, 11.5755))
        return [OsmArea(osm_id=1, kind="wood", inners=[], outers=[[
            to_latlon(Metres(x, y), STORED) for x, y in ((0, 0), (20, 0), (20, 20), (0, 20))]])]

    monkeypatch.setattr(landcover_sync, "landcover_in", replaced)
    landcover_sync.add_later(old, STORED, [[0, 0], [20, 0], [20, 20], [0, 20]])
    assert conn.execute("SELECT garden_id FROM garden").fetchone()[0] == 1, "the same id"
    assert conn.execute("SELECT COUNT(*) FROM garden_landcover").fetchone()[0] == 0
    assert not landcover_sync._failed_at


def test_the_light_does_not_wait_for_the_land(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The rebuild answers before the landcover is fetched: it is scheduled."""
    scheduled: list[int] = []
    monkeypatch.setattr(landcover_sync, "fetch_later", scheduled.append)
    client = TestClient(app)
    token = _drawn(client, 52.5171, 13.3889)
    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 200
    assert len(scheduled) == 1
    assert conn.execute("SELECT COUNT(*) FROM garden_landcover").fetchone()[0] == 0


def test_a_street_fetch_that_fails_still_keeps_the_land(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The offset is lost, placed from the anchor; the colours are not."""
    monkeypatch.setattr(geo_routes, "buildings_in", lambda *_a, **_k: [])
    monkeypatch.setattr(geo_routes, "streets_in", lambda *_a, **_k: [LANE])
    monkeypatch.setattr(landcover_sync, "landcover_in", _refuse)
    client = TestClient(app)
    token = client.post("/api/v1/gardens/from-map",
                        json={"name": "Alt", "outline": OUTLINE}).json()["garden"]["share_token"]
    monkeypatch.setattr(landcover_sync, "FAILURE_PAUSE_S", 0)
    _asking(monkeypatch, [])
    monkeypatch.setattr(landcover_sync, "streets_in", _refuse)
    client.post(f"/api/v1/gardens/{token}/light")
    assert conn.execute("SELECT placed_by FROM garden_landcover").fetchone()[0] == "anchor"


def test_a_map_gardens_streets_move_the_land_back_under_them(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Made before surroundings existed: the rebuild fetches them from the
    rounded anchor and reads the offset off the streets it imported."""
    monkeypatch.setattr(geo_routes, "buildings_in", lambda *_a, **_k: [])
    monkeypatch.setattr(geo_routes, "streets_in", lambda *_a, **_k: [LANE])
    # The creation fetch fails, as for every garden made before this feature.
    monkeypatch.setattr(landcover_sync, "landcover_in", _refuse)
    client = TestClient(app)
    made = client.post("/api/v1/gardens/from-map", json={"name": "Alt", "outline": OUTLINE})
    token = made.json()["garden"]["share_token"]

    wood = OsmArea(osm_id=1, kind="wood", inners=[], outers=[[
        to_latlon(Metres(x, y), EXACT) for x, y in ((30, 0), (50, 0), (50, 20), (30, 20))]])
    asked = _asking(monkeypatch, [wood])
    monkeypatch.setattr(landcover_sync, "streets_in", lambda *_a, **_k: [LANE])
    monkeypatch.setattr(landcover_sync, "FAILURE_PAUSE_S", 0)
    client.post(f"/api/v1/gardens/{token}/light")

    assert asked == [STORED]
    [area] = client.get(f"/api/v1/gardens/{token}/landcover").json()["areas"]
    xs = sorted({p[0] for p in area["rings"][0]})
    ys = sorted({p[1] for p in area["rings"][0]})
    # Where the exact anchor puts it, not 3 m east of that.
    assert (xs[0], xs[-1], ys[0], ys[-1]) == pytest.approx((30, 50, 0, 20), abs=0.15)
    assert conn.execute("SELECT placed_by FROM garden_landcover").fetchone()[0] == "streets"


def _refuse(*_a: Any, **_k: Any) -> list[OsmArea]:
    raise RuntimeError("Overpass sagt nein")


def test_the_offset_is_the_one_the_street_points_agree_on() -> None:
    lane = [(-60.0, -25.0), (-20.0, -22.0), (15.0, -26.0), (55.0, -31.0)]
    moved = [(x + 3.06, y - 1.11) for x, y in lane]
    assert street_offset(lane, moved) == pytest.approx((3.1, -1.1), abs=0.051)


def test_nodes_closer_than_the_offset_do_not_fool_it() -> None:
    """A curve drawn with a node every two metres: each point's nearest
    neighbour fetched again may be the wrong node, and the vote still holds."""
    curve = [(20 * math.cos(t / 10), 20 * math.sin(t / 10)) for t in range(20)]
    moved = [(x - 4.2, y + 2.9) for x, y in curve]
    assert street_offset(curve, moved) == pytest.approx((-4.2, 2.9), abs=0.051)


def test_too_few_points_agreeing_is_no_offset() -> None:
    assert street_offset([(0.0, 0.0), (30.0, 0.0)], [(1.0, 1.0), (31.0, 1.0)]) is None
    assert street_offset([(0.0, 0.0)] * 5, []) is None
