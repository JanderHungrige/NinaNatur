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
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import shadow_marks as routes
from ninanatur.api.deps import get_connection
from ninanatur.garden.models import Element, Garden
from ninanatur.garden.roofs import DEFAULT_EAVES_FRACTION
from ninanatur.garden.shadow_marks import ShadowMark, _as_height, readings
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.position import Location, SunPosition, sun_position
from ninanatur.solar.shading import Obstacle
from ninanatur.solar.shadow_edge import Reading, reach_past, read_edge
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


def _garden_of(*elements: Element) -> Garden:
    return Garden(garden_id=1, share_token="t", owner_id=None, name="G",
                  latitude=PLACE.latitude, longitude=PLACE.longitude, created_at="",
                  updated_at="", elements=list(elements))


def _gable(height: float, eaves: float) -> Element:
    return Element(element_id=4, kind="house", shape="polygon", x=0.0, y=0.0, height=height,
                   points=[[-6.0, -5.0], [6.0, -5.0], [6.0, 5.0], [-6.0, 5.0]], roof="gable",
                   eaves_m=eaves, eaves_source="user")


def _read(thing: Element, y: float, seen: str = SEEN) -> Reading:
    mark = ShadowMark(mark_id=1, element_id=thing.element_id, x=0.0, y=y,
                      seen_at=datetime.fromisoformat(seen))
    [found] = readings(_garden_of(thing), [mark])
    assert found is not None
    return found


def test_a_gable_cast_flat_says_the_height_a_lower_ridge_needs() -> None:
    """Eaves as high as the ridge — the map's storeys, no height tag — cast
    as a 6 m block. Its shadow seen 0.4 m shorter: lowered, it is a lower
    block, and the height a block's. Probed upward only, a metre more pitched
    the roof, its eaves kept the edge, and no height was said (review of
    45eb56a)."""
    cot = 1.0 / math.tan(math.radians(sun_position(PLACE, datetime.fromisoformat(SEEN)).altitude))
    reading = _read(_gable(6.0, 6.0), 5.0 + 6.0 * cot - 0.4)

    assert reading.height_m == pytest.approx(0.4 / cot, abs=0.01)
    assert _read(_gable(6.0 - reading.height_m, 6.0), 5.0 + 6.0 * cot - 0.4).offset_m < 0.01


def test_eaves_that_only_just_cast_the_edge_say_no_lower_ridge_can_help() -> None:
    """At the equinox's 40° the given 5 m eaves cast the far edge, a hand's
    breadth past the ridge's: a shadow seen shorter than the model's is
    nothing a lower ridge moves, and no height is said. Probed upward, a
    taller ridge overtook the eaves and "0,4 m zu hoch" was said — a height
    that, typed in, left the edge where it was (review of 45eb56a)."""
    equinox = "2026-09-20T11:24:50+00:00"
    cot = 1.0 / math.tan(math.radians(
        sun_position(PLACE, datetime.fromisoformat(equinox)).altitude))
    reading = _read(_gable(9.0, 5.0), 5.0 + 5.0 * cot - 0.4, equinox)

    assert reading.edge == "far" and reading.along_m > 0
    assert reading.height_m is None


def test_a_crown_s_height_moves_its_base_with_it() -> None:
    """A drawn lime, its crown base assumed at a third of its height: the
    height a mark says, typed in, puts the crown's edge on the mark — seen
    longer and shorter. Had the base stayed where it was, it missed by 5 cm."""
    tree = Element(element_id=5, kind="tree", shape="circle", x=0.0, y=0.0, width=8.0,
                   height=12.0)
    for beyond in (0.5, -0.5):
        edge = max(p[1] for ring in _read(tree, 20.0).rings for p in ring)
        reading = _read(tree, edge + beyond)
        assert reading.height_m is not None
        corrected = replace(tree, height=12.0 - reading.height_m)
        assert _read(corrected, edge + beyond).offset_m < 0.02, beyond


def test_a_height_is_never_said_faster_than_a_block_moves_or_from_too_little() -> None:
    """A gap between two shadows closing moves the edge further than a block
    could, which read as nearly no height; it is taken at a block's rate. And
    what a height hardly moves says no height: the number would be more than
    four times a block's."""
    sun = SunPosition(altitude=45.0, azimuth=180.0)
    reading = read_edge(_block(2.4), sun, 1.0, 2.0 + 2.4 + 0.3)
    assert reading is not None
    assert _as_height(reading, 3.0).height_m == pytest.approx(-0.3)
    assert _as_height(reading, 0.2).height_m is None
    assert _as_height(reading, 0.5).height_m == pytest.approx(-0.6)


#: A U open to the north, its arms 2 m wide with a 2 m gap: at a 40° sun from
#: the west, 1.2 m high, the left arm's shadow stops 0.57 m short of the right.
U_SHAPE = Obstacle(footprint=[(0.0, 0.0), (6.0, 0.0), (6.0, 8.0), (4.0, 8.0), (4.0, 2.0),
                              (2.0, 2.0), (2.0, 8.0), (0.0, 8.0)], height=1.2)


def test_the_edge_a_change_leaves_where_it_was_is_found_behind_the_point() -> None:
    """From a hair outside the left arm's edge, eastwards: that edge — which
    no change moved — is the one; not the right arm's, four metres on."""
    sun = SunPosition(altitude=40.0, azimuth=270.0)
    edge_x = 2.0 + 1.2 / math.tan(math.radians(40.0))

    assert reach_past(U_SHAPE, sun, (edge_x + 1e-9, 5.0)) == pytest.approx(0.0, abs=1e-6)
    assert reach_past(U_SHAPE, sun, (edge_x - 0.3, 5.0)) == pytest.approx(0.3)


def test_a_lower_block_s_edge_lies_behind_by_cot_h() -> None:
    sun = SunPosition(altitude=40.0, azimuth=180.0)
    cot = 1.0 / math.tan(math.radians(40.0))
    edge = (1.0, 2.0 + 2.4 * cot)

    assert reach_past(_block(1.4), sun, edge, back=True) == pytest.approx(cot)
    assert reach_past(_block(2.4), sun, edge, back=True) == pytest.approx(0.0, abs=1e-9)
