"""The shadow the plan draws is the shadow the light model counts (doc 116).

Until Wave 26 the day playback drew each obstacle's convex hull. For an
L-shaped house that fills the open corner the sun map has counted as sun since
2026-09-22, so the plan showed one shadow and the map another. A frame is now
the union of every shadow at that moment, as rings with their holes, and a
point is inside it exactly when `is_shaded` says so.
"""
from __future__ import annotations

import random
import sqlite3
from collections.abc import Iterator

import pytest
from concave_shapes import scene
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.garden.footprint import covers
from ninanatur.garden.polyline import band_of
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.position import SunPosition
from ninanatur.solar.reach import is_convex
from ninanatur.solar.shading import Obstacle, Point, is_shaded, shadow_hull, shadow_rings
from ninanatur.solar.sweep import shadow_shape
from ninanatur.web.app import app

Ring = list[tuple[float, float]]
ELL = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (4.0, 4.0), (4.0, 10.0), (0.0, 10.0)]
BOX = [(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0.0, 4.0)]
#: A house round a courtyard, its opening a metre wide in the east wall.
G = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (9.0, 4.0), (9.0, 1.0), (1.0, 1.0), (1.0, 9.0),
     (9.0, 9.0), (9.0, 6.0), (10.0, 6.0), (10.0, 10.0), (0.0, 10.0)]


def _drawn(rings: list[Ring], x: float, y: float) -> bool:
    """Inside a frame drawn in one path under the non-zero rule, as the page
    draws it: outlines wind one way and holes the other."""
    winding = 0
    for ring in rings:
        for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True):
            if ay <= y < by and (bx - ax) * (y - ay) - (x - ax) * (by - ay) > 0:
                winding += 1
            elif by <= y < ay and (bx - ax) * (y - ay) - (x - ax) * (by - ay) < 0:
                winding -= 1
    return winding != 0


def _agrees(houses: list[Obstacle], sun: SunPosition, x: float, y: float) -> bool | None:
    """Whether the frame and the model agree here; None on the shadow's edge,
    where moving 2 cm changes the model's answer."""
    model = any(is_shaded(Point(x, y), h, sun) for h in houses)
    if any(any(is_shaded(Point(x + ex, y + ey), h, sun) for h in houses) != model
           for ex, ey in ((0.02, 0), (-0.02, 0), (0, 0.02), (0, -0.02))):
        return None
    return _drawn(shadow_rings(houses, sun), x, y) == model


def test_the_open_corner_of_an_l_is_drawn_open() -> None:
    """The sun in the north-east, low enough for a 3 m house to reach 4 m."""
    house = Obstacle(footprint=ELL, height=3.0)
    sun = SunPosition(altitude=28.0, azimuth=45.0)
    rings = shadow_rings([house], sun)
    corner = (6.0, 6.0)  # in the open quarter, inside the hull
    assert not is_shaded(Point(*corner), house, sun)
    assert not _drawn(rings, *corner), "the hull drew it shaded"
    assert covers(shadow_hull(house, sun), corner), "which is what the hull did"
    behind = (-2.0, -2.0)  # south-west of the house, 2.8 m into its 5.6 m shadow
    assert _drawn(rings, *behind) and is_shaded(Point(*behind), house, sun)


def test_a_rectangle_draws_the_shadow_it_always_drew() -> None:
    house = Obstacle(footprint=BOX, height=5.0)
    sun = SunPosition(altitude=35.0, azimuth=200.0)
    [ring] = shadow_rings([house], sun)
    hull = shadow_hull(house, sun)
    assert {(round(x, 6), round(y, 6)) for x, y in ring} == {
        (round(x, 6), round(y, 6)) for x, y in hull}


def test_a_courtyard_the_sun_still_reaches_is_a_hole_in_the_shadow() -> None:
    """Sun from the north: the east wall's upper part sweeps south across the
    opening and closes it, and the courtyard's southern half is still lit."""
    house = Obstacle(footprint=G, height=3.0)
    sun = SunPosition(altitude=45.0, azimuth=0.0)  # a 3 m shadow, due south
    rings = shadow_rings([house], sun)
    assert len(rings) == 2, "an outline and one hole"
    lit = (5.0, 2.0)
    assert not is_shaded(Point(*lit), house, sun)
    assert not _drawn(rings, *lit)
    assert _drawn(rings, 5.0, 7.0) and is_shaded(Point(5.0, 7.0), house, sun)


def test_two_shadows_that_overlap_fill_the_overlap_once() -> None:
    """Each shadow is its own shape and they are not merged; drawn in one path
    under the non-zero rule, the overlap is inside both and filled once."""
    sun = SunPosition(altitude=30.0, azimuth=180.0)
    near = Obstacle(footprint=BOX, height=4.0)
    beside = Obstacle(footprint=[(x + 4.0, y) for x, y in BOX], height=4.0)
    rings = shadow_rings([near, beside], sun)
    assert len(rings) == 2
    assert _drawn(rings, 5.0, 6.0) and _drawn(rings, 1.0, 6.0) and _drawn(rings, 9.0, 6.0)
    assert not _drawn(rings, 12.0, 6.0)


def test_every_frame_agrees_with_the_model_round_concave_houses() -> None:
    rng = random.Random(116)
    checked = 0
    for _ in range(300):
        houses = [Obstacle(footprint=o, height=rng.uniform(2.5, 12)) for o in scene(rng)]
        sun = SunPosition(altitude=rng.uniform(8, 60), azimuth=rng.uniform(0, 360))
        for _ in range(6):
            x, y = rng.uniform(-30, 30), rng.uniform(-30, 30)
            if any(covers(h.footprint, (x, y)) for h in houses):
                continue
            agrees = _agrees(houses, sun, x, y)
            if agrees is None:
                continue
            checked += 1
            assert agrees, (x, y, sun, [h.footprint for h in houses])
    assert checked > 1000


def test_outlines_wind_anticlockwise_holes_clockwise_and_a_closing_point_is_nothing() -> None:
    def area(ring: Ring) -> float:
        return sum(ax * by - bx * ay
                   for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True))
    outline, hole = shadow_shape(G, 0.0, -3.0)
    assert area(outline) > 0 > area(hole)
    assert shadow_shape([*ELL, ELL[0]], -2.0, 3.0) == shadow_shape(ELL, -2.0, 3.0)
    assert area(shadow_shape(list(reversed(ELL)), -2.0, 3.0)[0]) > 0, "whichever way it was drawn"


def test_a_wall_drawn_as_a_line_keeps_the_corner_it_turns_round() -> None:
    """A line's band has a spur at the inside of every corner, and read as no
    turn at all it made every turning wall convex: its hull shaded the corner
    in the model and on the plan (review, 2026-09-22)."""
    wall = band_of([(0.0, 10.0), (0.0, 0.0), (10.0, 0.0)], width=0.3)
    assert not is_convex(wall)
    house = Obstacle(footprint=wall, height=2.0)
    sun = SunPosition(altitude=40.0, azimuth=225.0)  # 2.4 m, towards the corner
    assert not is_shaded(Point(6.0, 6.0), house, sun)
    assert not _drawn(shadow_rings([house], sun), 6.0, 6.0)
    assert is_shaded(Point(1.0, 1.0), house, sun) and _drawn(shadow_rings([house], sun), 1.0, 1.0)


#: A shed whose outline crosses itself, as dragging a corner can leave one: the
#: union of its shadow threw in GEOS and failed the whole day (review).
TANGLED = [(7.34, 0.51), (2.42, 2.86), (3.61, 0.17), (4.19, 1.1), (7.03, 5.26)]
#: Figure-eights: one whose lobes cancel in a signed area, one that does not.
BOW_TIES = [[(0.0, 0.0), (4.0, 4.0), (4.0, 0.0), (0.0, 4.0)],
            [(0.0, 0.0), (4.0, 4.0), (4.0, 1.0), (0.0, 5.0)]]


def test_an_outline_that_crosses_itself_is_drawn_as_the_model_counts_it() -> None:
    rng = random.Random(9)
    checked = 0
    for outline in [TANGLED, *BOW_TIES]:
        for _ in range(12):
            house = Obstacle(footprint=outline, height=rng.uniform(1.0, 5.0))
            sun = SunPosition(altitude=rng.uniform(10, 60), azimuth=rng.uniform(0, 360))
            for _ in range(40):
                agrees = _agrees([house], sun, rng.uniform(-4, 12), rng.uniform(-4, 10))
                if agrees is not None:
                    checked += 1
                    assert agrees, (outline, sun)
    assert checked > 1200


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_the_day_the_page_plays_leaves_the_corner_open(client: TestClient) -> None:
    """Through `/shadows`, as the day player asks: every June frame in which
    the hull would have shaded the L's open corner draws it open, as the model
    counts it."""
    token = client.post("/api/v1/gardens", json={
        "name": "L", "latitude": 52.5171, "longitude": 13.3889}).json()["share_token"]
    made = client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "house", "x": 0.0, "y": 0.0, "shape": "polygon",
        "points": [list(p) for p in ELL], "height": 3.0})
    assert made.status_code in (200, 201), made.text
    frames = client.get(f"/api/v1/gardens/{token}/shadows?month=6").json()["frames"]
    house, corner = Obstacle(footprint=ELL, height=3.0), (6.0, 6.0)

    def hull_was_wrong(frame: dict[str, float]) -> bool:
        sun = SunPosition(frame["altitude"], frame["azimuth"])
        return covers(shadow_hull(house, sun), corner) and not is_shaded(Point(*corner), house, sun)

    hull_wrong = [f for f in frames if hull_was_wrong(f)]
    assert hull_wrong, "the June morning sun stands in the north-east"
    assert not any(_drawn(f["polygons"], *corner) for f in hull_wrong)


def test_a_tangled_shed_does_not_cost_the_day(client: TestClient) -> None:
    token = client.post("/api/v1/gardens", json={
        "name": "T", "latitude": 52.5171, "longitude": 13.3889}).json()["share_token"]
    client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "shed", "x": 0.0, "y": 0.0, "shape": "polygon",
        "points": [list(p) for p in TANGLED], "height": 4.5})
    for month in (5, 6, 7, 8):
        assert client.get(f"/api/v1/gardens/{token}/shadows?month={month}").status_code == 200
