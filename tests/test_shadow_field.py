"""The precomputed field must answer exactly what the slow path answers.

`bed_light_value` is the reference. It has been right since Wave 3 and it is
checked against three-dimensional ray tracing in `test_shading_is_ray_tracing`.
The field is a faster arrangement of the same arithmetic, and the only thing
worth asserting about a faster arrangement is that it did not change the answer.

It exists because a grid needs a thousand points and the slow path costs 125 ms
each. What was hoisted: the sun's position, which depends on nothing about the
point, and every shadow polygon, which depends on nothing about the point
either. What was added: a bounding box in front of each point-in-polygon test.
"""
from __future__ import annotations

import random

from ninanatur.solar.field import shadow_field
from ninanatur.solar.light import bed_light_value
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle, Point

BERLIN = Location(latitude=52.5, longitude=13.4)


def _rect(cx: float, cy: float, w: float, d: float) -> list[tuple[float, float]]:
    return [(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2),
            (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)]


def test_the_field_agrees_with_the_slow_path() -> None:
    random.seed(3)
    obstacles = [
        Obstacle(footprint=_rect(random.uniform(-20, 20), random.uniform(-20, 20),
                                 random.uniform(4, 12), random.uniform(4, 12)),
                 height=random.uniform(2, 14))
        for _ in range(6)
    ]
    field = shadow_field(BERLIN, obstacles)

    for _ in range(12):
        point = Point(random.uniform(-20, 20), random.uniform(-20, 20))
        slow = bed_light_value(BERLIN, point, obstacles).sun_hours
        fast = field.sun_hours_at(point.x, point.y)
        assert round(fast, 2) == slow, f"disagreed at {point}: {fast} vs {slow}"


def test_it_agrees_for_a_raised_bed_too() -> None:
    """The height belongs to the field rather than the point, because it changes
    every polygon. A garden with beds at two heights needs two fields — which is
    still two, not one per point."""
    obstacles = [Obstacle(footprint=_rect(0, 6, 8, 1), height=1.2)]
    raised = 0.8
    field = shadow_field(BERLIN, obstacles, height_above_ground=raised)

    for y in (2.0, 4.0, 5.5, 7.0):
        point = Point(0.0, y)
        slow = bed_light_value(BERLIN, point, obstacles,
                               height_above_ground=raised).sun_hours
        assert round(field.sun_hours_at(point.x, point.y), 2) == slow


def test_an_empty_garden_is_full_sun_either_way() -> None:
    field = shadow_field(BERLIN, [])
    assert round(field.sun_hours_at(0, 0), 2) == bed_light_value(
        BERLIN, Point(0, 0), []
    ).sun_hours


def test_an_obstacle_shorter_than_the_bed_it_stands_beside_is_dropped() -> None:
    """A 1.2 m fence casts nothing onto a bed 1.5 m up, so it need not be in the
    field at all — and leaving it in would mean building a polygon per sample
    for something that can never shade anything."""
    fence = Obstacle(footprint=_rect(0, 5, 6, 0.2), height=1.2)

    field = shadow_field(BERLIN, [fence], height_above_ground=1.5)

    assert all(not shadows for shadows in field.moments)


def test_the_field_is_faster_than_asking_the_slow_path_each_time() -> None:
    """Not a benchmark — a guard on the shape of the thing.

    The point of the field is that a second point costs almost nothing. If a
    change ever puts per-point work back into it, the ratio collapses and this
    fails long before anybody notices a slow page.
    """
    import time

    obstacles = [
        Obstacle(footprint=_rect(10 + i, 10, 8, 6), height=8.0) for i in range(12)
    ]
    field = shadow_field(BERLIN, obstacles)

    start = time.perf_counter()
    for i in range(20):
        field.sun_hours_at(i * 0.5, 0.0)
    per_point = (time.perf_counter() - start) / 20

    start = time.perf_counter()
    bed_light_value(BERLIN, Point(0, 0), obstacles)
    slow = time.perf_counter() - start

    assert per_point * 5 < slow, (
        f"the field is meant to be far cheaper per point: {per_point*1000:.2f} ms "
        f"against {slow*1000:.1f} ms"
    )
