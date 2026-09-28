"""Marking where a shadow really ended, through the API — doc 122.

A mark is an observation: of a thing of this garden's that casts, at a moment
that has passed, with the sun up. Only that is kept; the model's reading of
it is worked out on every read, so it follows the model — and the gardener's
correction of the height it disagreed with.

The server's clock is set here (`api.shadow_marks.now`), so nothing depends on
the hour the suite runs at: a "tomorrow" built from the real clock fell in the
night half the time, and was refused for the dark instead (review, 2026-09-28).
"""
from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import shadow_marks as routes
from ninanatur.api.deps import get_connection
from ninanatur.garden.shadow_marks import MAX_MARKS, add_mark
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.position import Location, sun_position
from ninanatur.web.app import app

#: Wuppertal, midsummer, late morning: the sun well up in the south-east.
PLACE = Location(51.2562, 7.1508)
SEEN = "2026-06-21T09:30:00+00:00"
#: The server's clock in these tests: the same day, noon.
NOON = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)


@pytest.fixture()
def conn(monkeypatch: pytest.MonkeyPatch) -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    monkeypatch.setattr(routes, "now", lambda: NOON)
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


def _garden(client: TestClient, x: float = 0.0) -> tuple[str, int]:
    """A garden with a shed 3 × 2.5 m and 2.4 m high, standing at (x, 0)."""
    token: str = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": PLACE.latitude,
        "longitude": PLACE.longitude}).json()["share_token"]
    body = client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "shed", "x": x, "y": 0.0}).json()
    return token, int(body["obstacles"][-1]["obstacle_id"])


def _mark(client: TestClient, token: str, element: int, x: float, y: float,
          seen: str = SEEN) -> Any:
    return client.post(f"/api/v1/gardens/{token}/shadow-marks", json={
        "element_id": element, "x": x, "y": y, "seen_at": seen})


def _far_corner(height: float, x: float = 0.0) -> tuple[float, float]:
    """Worked out by hand: where the shed's north-western corner casts at the
    mark's moment — the corner away from a south-eastern sun."""
    sun = sun_position(PLACE, datetime.fromisoformat(SEEN))
    reach = height / math.tan(math.radians(sun.altitude))
    away = math.radians(sun.azimuth)
    return x - 1.5 - math.sin(away) * reach, 1.25 - math.cos(away) * reach


def test_a_mark_is_kept_and_read_against_the_models_shadow(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token, shed = _garden(client)

    made = _mark(client, token, shed, 2.0, 5.0)

    assert made.status_code == 201, made.text
    body = made.json()
    assert (body["element_id"], body["x"], body["y"], body["seen_at"]) == (
        shed, 2.0, 5.0, SEEN)
    reading = body["reading"]
    assert reading["altitude"] > 30 and 90 < reading["azimuth"] < 180, "a late morning sun"
    assert reading["rings"] and reading["offset_m"] > 0
    assert client.get(f"/api/v1/gardens/{token}/shadow-marks").json() == [body]


def test_the_models_edge_is_where_a_hand_puts_the_sheds_shadow(conn: sqlite3.Connection) -> None:
    """Business rule 2, pinned absolutely: the reading is the shadow the light
    model casts — here a 2.4 m block, the shed's height, its corner's shadow
    worked out from the sun by hand."""
    client = TestClient(app)
    token, shed = _garden(client)

    reading = _mark(client, token, shed, *_far_corner(2.4)).json()["reading"]

    assert reading["offset_m"] < 0.02


def test_a_shadow_seen_further_reads_the_shed_too_low_until_it_is_corrected(
    conn: sqlite3.Connection,
) -> None:
    """Seen a metre further than the model casts, straight away from the sun:
    the shed reads as too low. Its height corrected to what the shadow says,
    the same mark reads again — and nearly nothing."""
    client = TestClient(app)
    token, shed = _garden(client)
    sun = sun_position(PLACE, datetime.fromisoformat(SEEN))
    away = math.radians(sun.azimuth)
    fx, fy = _far_corner(2.4)
    beyond = _mark(client, token, shed, fx - math.sin(away) * 0.6,
                   fy - math.cos(away) * 0.6).json()["reading"]
    assert beyond["edge"] == "far" and beyond["model_longer"] is False
    assert beyond["height_m"] == pytest.approx(-0.6 * math.tan(math.radians(sun.altitude)),
                                               abs=0.02)

    taller = 2.4 - beyond["height_m"]
    client.patch(f"/api/v1/gardens/{token}/obstacles/{shed}", json={"height": taller})
    [again] = client.get(f"/api/v1/gardens/{token}/shadow-marks").json()

    assert again["reading"]["offset_m"] < 0.03


def test_a_mark_beside_the_shadow_reads_a_turn_about_the_shed(conn: sqlite3.Connection) -> None:
    """Off the origin, so the angle is the thing's; 12 m high, so its shadow
    is long enough for a miss beside it to be a turn and not a miss towards
    it. Beside the middle of the shadow's right-hand side, looking along it,
    the model's edge lies to the left — turned anticlockwise."""
    client = TestClient(app)
    token, shed = _garden(client, x=10.0)
    client.patch(f"/api/v1/gardens/{token}/obstacles/{shed}", json={"height": 12.0})
    sun = sun_position(PLACE, datetime.fromisoformat(SEEN))
    away = math.radians(sun.azimuth)
    reach = 12.0 / math.tan(math.radians(sun.altitude))
    fall = (-math.sin(away), -math.cos(away))
    right = (fall[1], -fall[0])
    corners = [(10.0 + dx, dy) for dx in (-1.5, 1.5) for dy in (-1.25, 1.25)]
    cx, cy = max(corners, key=lambda c: c[0] * right[0] + c[1] * right[1])
    side = (cx + fall[0] * reach / 2 + right[0] * 1.5, cy + fall[1] * reach / 2 + right[1] * 1.5)
    reading = _mark(client, token, shed, *side).json()["reading"]

    assert reading["edge"] == "side"
    assert reading["offset_m"] == pytest.approx(1.5, abs=0.02)
    assert reading["across_m"] > 0 and reading["turned_deg"] > 0


def test_a_mark_about_the_future_or_the_night_is_refused(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token, shed = _garden(client)

    tomorrow = (NOON + timedelta(days=1)).replace(hour=11).isoformat()
    assert _mark(client, token, shed, 2.0, 5.0, tomorrow).status_code == 422
    assert _mark(client, token, shed, 2.0, 5.0, "2026-06-21T23:00:00+00:00").status_code == 422
    naive = client.post(f"/api/v1/gardens/{token}/shadow-marks", json={
        "element_id": shed, "x": 2.0, "y": 5.0, "seen_at": "2026-06-21T09:30:00"})
    assert naive.status_code == 422, "a moment without its offset is no moment"
    assert client.get(f"/api/v1/gardens/{token}/shadow-marks").json() == []


def test_a_phone_clock_a_few_minutes_fast_is_not_the_future(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token, shed = _garden(client)

    assert _mark(client, token, shed, 2.0, 5.0,
                 (NOON + timedelta(minutes=4)).isoformat()).status_code == 201
    assert _mark(client, token, shed, 2.0, 5.0,
                 (NOON + timedelta(minutes=6)).isoformat()).status_code == 422


def test_a_moment_the_model_cannot_place_is_refused_not_a_crash(conn: sqlite3.Connection) -> None:
    """Year 1 east of Greenwich cannot even be turned into UTC; the sun's
    formula is good for this century and the last (review, 2026-09-28)."""
    client = TestClient(app)
    token, shed = _garden(client)

    for seen in ("0001-01-01T03:00:00+05:00", "1000-06-21T09:30:00+00:00",
                 "1999-06-21T09:30:00+00:00"):
        assert _mark(client, token, shed, 2.0, 5.0, seen).status_code == 422, seen


def test_a_mark_is_kept_in_utc_whatever_clock_sent_it(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token, shed = _garden(client)

    made = _mark(client, token, shed, 2.0, 5.0, "2026-06-21T11:30:00+02:00").json()

    assert made["seen_at"] == SEEN


def test_only_a_thing_of_this_garden_that_casts_can_be_marked(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token, _shed = _garden(client)
    _other, theirs = _garden(client)
    lawn = client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "lawn", "x": 10.0, "y": 0.0}).json()["obstacles"][-1]["obstacle_id"]

    assert _mark(client, token, theirs, 2.0, 5.0).status_code == 404
    assert _mark(client, token, lawn, 12.0, 0.0).status_code == 404


def test_a_garden_lists_its_own_marks_and_nobody_elses(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    mine, my_shed = _garden(client)
    theirs, their_shed = _garden(client)
    _mark(client, mine, my_shed, 2.0, 5.0)
    _mark(client, theirs, their_shed, 3.0, 6.0)

    assert [m["element_id"] for m in client.get(
        f"/api/v1/gardens/{mine}/shadow-marks").json()] == [my_shed]
    assert [m["element_id"] for m in client.get(
        f"/api/v1/gardens/{theirs}/shadow-marks").json()] == [their_shed]


def test_a_garden_keeps_fifty_not_a_diary(conn: sqlite3.Connection) -> None:
    """Fifty, as the doc says; kept through the store, since fifty marks in
    ten minutes is more than the route's own allowance."""
    client = TestClient(app)
    token, shed = _garden(client)
    garden_id = conn.execute("SELECT garden_id FROM garden WHERE share_token = ?",
                             (token,)).fetchone()[0]
    for _ in range(50):
        assert add_mark(conn, garden_id, shed, 2.0, 5.0, datetime.fromisoformat(SEEN))

    assert MAX_MARKS == 50
    refused = _mark(client, token, shed, 2.0, 5.0)
    assert refused.status_code == 409 and "50" in refused.json()["detail"]
    assert add_mark(conn, garden_id, shed, 2.0, 5.0, datetime.fromisoformat(SEEN)) is None


def test_marks_go_with_their_thing_and_their_garden(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token, shed = _garden(client)
    mark = _mark(client, token, shed, 2.0, 5.0).json()["mark_id"]

    assert client.delete(f"/api/v1/gardens/{token}/shadow-marks/{mark}").status_code == 204
    assert client.delete(f"/api/v1/gardens/{token}/shadow-marks/{mark}").status_code == 404
    assert client.delete(f"/api/v1/gardens/{token}/shadow-marks/{2**63}").status_code == 422
    _mark(client, token, shed, 2.0, 5.0)
    client.delete(f"/api/v1/gardens/{token}/obstacles/{shed}")
    assert client.get(f"/api/v1/gardens/{token}/shadow-marks").json() == []
    _token, other = _garden(client)
    _mark(client, _token, other, 2.0, 5.0)
    client.delete(f"/api/v1/gardens/{_token}")
    assert conn.execute("SELECT COUNT(*) FROM shadow_mark").fetchone()[0] == 0
