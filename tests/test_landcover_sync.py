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
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import geo as geo_routes
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
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    app.dependency_overrides[get_connection] = lambda: made
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


def test_a_failed_fetch_leaves_the_light_alone_and_is_asked_again(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    assert calls["n"] == 2


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
