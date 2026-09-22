"""The land around a garden, fetched after the answer (doc 114): how the
background fetches are bounded, keyed and kept to the garden that asked.

Split from `test_landcover_sync.py` when the review of 2026-09-21 added these.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import nullcontext
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import ratelimit
from ninanatur.api.deps import get_connection
from ninanatur.garden import landcover_sync
from ninanatur.geo.osm_landcover import OsmArea
from ninanatur.geo.projection import LatLon, Metres, to_latlon
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

BED = {"name": "Beet", "polygon": [[0, 0], [6, 0], [6, 4], [0, 4]],
       "soil_type": "loam", "moisture": "fresh"}
STORED = LatLon(52.4056, 13.2101)


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


def _refuse(*_a: Any, **_k: Any) -> list[OsmArea]:
    raise RuntimeError("Overpass sagt nein")


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


def test_a_new_gardens_fetch_is_never_skipped_for_room(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the import knows the exact anchor; a skipped creation fetch came
    back later from the rounded one, metres off (review, 2026-09-21)."""
    client = TestClient(app)
    busy = [_drawn(client, 52.5171 + i / 1000, 13.3889) for i in range(2)]
    new = _drawn(client, 52.52, 13.39)
    asked: list[float] = []

    def full(*_box: float, centre: LatLon, **_k: Any) -> list[OsmArea]:
        asked.append(centre.lat)
        if len(asked) == 1:
            landcover_sync.fetch_later(busy[1])        # the room is full now
        elif len(asked) == 2:
            landcover_sync.add_later(new, LatLon(52.52, 13.39), [[0, 0], [10, 0], [10, 10]])
        return []

    monkeypatch.setattr(landcover_sync, "landcover_in", full)
    landcover_sync.fetch_later(busy[0])
    assert asked[-1] == 52.52, "the new garden's fetch ran with both slots taken"
    assert conn.execute("SELECT COUNT(*) FROM garden_landcover").fetchone()[0] == 3


def test_a_skipped_fetch_does_not_log_the_share_token(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    """The token is the one secret a garden has; the log names it by a hash."""
    client = TestClient(app)
    token = _drawn(client, 52.5171, 13.3889)

    def again(*_box: float, **_k: Any) -> list[OsmArea]:
        landcover_sync.fetch_later(token)
        return []

    monkeypatch.setattr(landcover_sync, "landcover_in", again)
    with caplog.at_level("INFO", logger="ninanatur.garden.landcover_sync"):
        landcover_sync.fetch_later(token)
    assert "skipped" in caplog.text
    assert token[:6] not in caplog.text


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
