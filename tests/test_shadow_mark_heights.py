"""What a missed edge says about a height — doc 122, review of stage 3.

A mark's height was the way along the sun times tan h: right for a block,
whose top casts the far edge. Since roofs cast as roofs (doc 120) a gable's
far edge at a high sun is its eaves', and the ridge — the height the
gardener can correct — hardly moves it: "as though a metre lower" was then a
height no correction could satisfy. The height said now is what a metre more
of the thing moves that very point of the edge, as the model would make it a
metre taller: eaves the gardener gave stay put; eaves the model assumes rise.
"""
from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import shadow_marks as routes
from ninanatur.api.deps import get_connection
from ninanatur.garden.roofs import DEFAULT_EAVES_FRACTION
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.position import Location, SunPosition, sun_position
from ninanatur.solar.shading import Obstacle
from ninanatur.solar.shadow_edge import reach_past
from ninanatur.web.app import app

PLACE = Location(51.2562, 7.1508)
#: Midsummer, the moment the sun stands due south of Wuppertal, at 62°.
SEEN = "2026-06-21T11:33:10+00:00"
NOON = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)


def _block(height: float) -> Obstacle:
    return Obstacle(footprint=[(0.0, 0.0), (3.0, 0.0), (3.0, 2.0), (0.0, 2.0)], height=height)


def test_a_metre_more_moves_a_blocks_edge_by_cot_h_and_nothing_moves_it_by_nothing() -> None:
    """From a point on a 2.4 m block's far edge, straight away from a sun at
    40°: the same block's shadow ends there, a 3.4 m block's cot 40° further
    — measured along the shadow, not to whatever edge is nearest."""
    sun = SunPosition(altitude=40.0, azimuth=180.0)
    cot = 1.0 / math.tan(math.radians(40.0))
    edge = (1.0, 2.0 + 2.4 * cot)

    assert reach_past(_block(2.4), sun, edge) == pytest.approx(0.0, abs=1e-9)
    assert reach_past(_block(3.4), sun, edge) == pytest.approx(cot)
    # From the sunny side the shadow — the footprint and all — lies ahead.
    assert reach_past(_block(2.4), sun, (1.0, -1.0)) == pytest.approx(3.0 + 2.4 * cot)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    monkeypatch.setattr(routes, "now", lambda: NOON)
    app.dependency_overrides[get_connection] = lambda: made
    yield TestClient(app)
    app.dependency_overrides.clear()


def _house(client: TestClient, eaves: float | None) -> tuple[str, int]:
    """A house 12 m east–west and 10 m deep, gabled, its ridge 9 m high and
    running east to west: its long sides face the sun and away from it."""
    token: str = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": PLACE.latitude,
        "longitude": PLACE.longitude}).json()["share_token"]
    body = client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "house", "x": 0.0, "y": 0.0, "shape": "rect", "width": 12.0, "depth": 10.0,
        "height": 9.0}).json()
    house = int(body["obstacles"][-1]["obstacle_id"])
    roof: dict[str, Any] = {"roof": "gable"} | ({} if eaves is None else {"eaves_m": eaves})
    assert client.patch(f"/api/v1/gardens/{token}/obstacles/{house}",
                        json=roof).status_code == 200
    return token, house


def _mark_behind_the_eaves(client: TestClient, token: str, house: int, eaves: float,
                           beyond: float) -> Any:
    """Due north of the house, `beyond` past where its north eaves cast."""
    cot = 1.0 / math.tan(math.radians(sun_position(PLACE, datetime.fromisoformat(SEEN)).altitude))
    made = client.post(f"/api/v1/gardens/{token}/shadow-marks", json={
        "element_id": house, "x": 0.0, "y": 5.0 + eaves * cot + beyond, "seen_at": SEEN})
    assert made.status_code == 201, made.text
    return made.json()["reading"]


def test_eaves_the_gardener_gave_say_no_height_where_they_cast_the_edge(
    client: TestClient,
) -> None:
    """Eaves at 5 m cast the far edge at a 62° sun; the ridge's shadow ends
    3 m short of it, and a metre more of ridge still short. No height the
    gardener could type moves this edge, and none is said."""
    token, house = _house(client, eaves=5.0)

    reading = _mark_behind_the_eaves(client, token, house, 5.0, beyond=0.4)

    assert reading["edge"] == "far" and reading["offset_m"] == pytest.approx(0.4, abs=0.01)
    assert reading["height_m"] is None


def test_eaves_the_model_assumes_rise_with_the_height_the_mark_asks_for(
    client: TestClient,
) -> None:
    """Assumed at three quarters of the ridge, the eaves rise with it: a metre
    more of ridge moves their edge 0.75 × cot h, not cot h. The height the
    mark says, typed in, puts the edge on the mark."""
    token, house = _house(client, eaves=None)
    sun = sun_position(PLACE, datetime.fromisoformat(SEEN))
    cot = 1.0 / math.tan(math.radians(sun.altitude))

    reading = _mark_behind_the_eaves(client, token, house, DEFAULT_EAVES_FRACTION * 9.0,
                                     beyond=0.4)

    assert reading["edge"] == "far"
    assert reading["height_m"] == pytest.approx(-0.4 / (DEFAULT_EAVES_FRACTION * cot), abs=0.02)
    assert client.patch(f"/api/v1/gardens/{token}/obstacles/{house}",
                        json={"height": 9.0 - reading["height_m"]}).status_code == 200
    [again] = client.get(f"/api/v1/gardens/{token}/shadow-marks").json()
    assert again["reading"]["offset_m"] < 0.03
