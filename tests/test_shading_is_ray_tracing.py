"""The ground projection is exact, and here is the proof rather than the claim.

Asked directly: is overlap handled? Is a tree's shadow stopped when it falls on
a taller building?

The model never asks where a shadow lands. It asks, per obstacle, *does this
thing stand between this point and the sun* — a question that does not care what
else is in the way. Occlusion between obstacles cannot change the union, because
a point is lit exactly when no obstacle blocks its ray.

That is an argument. This file is the measurement: the same scenes answered by
the model and by marching the ray to the sun in three dimensions, which is what
the model is a shortcut for. It exists because Wave 16 rewrites this hot path
for speed — hoisting sun positions, precomputing shadow polygons, rejecting by
bounding box — and an optimisation of geometry needs something that fails when
the geometry changes.
"""
from __future__ import annotations

import math
import random

from ninanatur.garden.footprint import covers
from ninanatur.solar.position import SunPosition
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle, Point, is_shaded

#: Fine enough that a 3 m building cannot be stepped over at a low sun.
STEP_M = 0.05
#: Past this the sun is either blocked by the horizon or by nothing at all.
REACH_M = 300.0


def ray_reaches_sun(
    point: Point,
    obstacles: list[Obstacle],
    sun: SunPosition,
    height_above_ground: float = 0.0,
) -> bool:
    """March from the point towards the sun and see what it runs into.

    Obstacles are vertical prisms: inside the footprint and below the height is
    solid, everything else is air.
    """
    azimuth = math.radians(sun.azimuth)
    dx, dy = math.sin(azimuth), math.cos(azimuth)
    dz = math.tan(math.radians(sun.altitude))
    distance = STEP_M
    while distance < REACH_M:
        x = point.x + dx * distance
        y = point.y + dy * distance
        z = height_above_ground + dz * distance
        for obstacle in obstacles:
            if z < obstacle.height and covers(obstacle.footprint, (x, y)):
                return False
        distance += STEP_M
    return True


def _rect(cx: float, cy: float, w: float, d: float) -> list[tuple[float, float]]:
    return [(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2),
            (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)]


def test_the_projection_agrees_with_a_ray_in_three_dimensions() -> None:
    """Random scenes of overlapping buildings, both ways round."""
    random.seed(7)
    checked = 0

    for _ in range(300):
        obstacles = [
            Obstacle(
                footprint=_rect(
                    random.uniform(-25, 25), random.uniform(-25, 25),
                    random.uniform(3, 15), random.uniform(3, 15),
                ),
                height=random.uniform(2, 15),
            )
            for _ in range(random.randint(2, 5))
        ]
        sun = SunPosition(
            altitude=random.uniform(MIN_ALTITUDE + 3, 60),
            azimuth=random.uniform(0, 360),
        )
        point = Point(random.uniform(-25, 25), random.uniform(-25, 25))
        # A point inside a building is not a question about shade.
        if any(covers(o.footprint, (point.x, point.y)) for o in obstacles):
            continue

        checked += 1
        model = any(is_shaded(point, o, sun) for o in obstacles)
        assert model is not ray_reaches_sun(point, obstacles, sun), (
            f"disagreed at {point} with sun {sun.altitude:.0f}/{sun.azimuth:.0f}"
        )

    assert checked > 200, "the scenes have to actually exercise it"


def test_a_tree_behind_a_taller_house_changes_nothing() -> None:
    """The case as it was asked.

    The tree's ground shadow runs straight through the house and out the other
    side, which sounds wrong and is not: the house is taller, so its own shadow
    covers everything the tree's does and more. The union is right without
    anybody having modelled the interception.
    """
    sun = SunPosition(altitude=20.0, azimuth=180.0)
    tree = Obstacle(footprint=_rect(0, 10, 6, 6), height=8.0)
    house = Obstacle(footprint=_rect(0, 20, 12, 10), height=12.0)
    point = Point(0, 34)

    assert is_shaded(point, tree, sun), "the tree's projection does reach past the house"
    assert is_shaded(point, house, sun), "and so does the house's, further"
    assert not ray_reaches_sun(point, [tree, house], sun)


def test_a_tree_taller_than_the_shed_in_front_of_it_still_shades() -> None:
    """The other way round, which is the case that would break a model that
    stopped a shadow at the first thing it met."""
    sun = SunPosition(altitude=25.0, azimuth=180.0)
    tree = Obstacle(footprint=_rect(0, 8, 5, 5), height=14.0)
    shed = Obstacle(footprint=_rect(0, 14, 4, 3), height=2.2)
    point = Point(0, 32)

    assert not is_shaded(point, shed, sun), "the shed's own shadow stops well short"
    assert is_shaded(point, tree, sun), "the tree's passes over its roof and lands"
    assert not ray_reaches_sun(point, [tree, shed], sun)


def test_a_raised_bed_stands_above_a_low_fence() -> None:
    """The narrow band where being raised is the whole answer.

    A 1.2 m fence at a 30 degree sun throws 2.1 m of shadow along the ground and
    0.7 m onto a bed 80 cm up. A point 1.5 m behind it is shaded at ground level
    and lit on the bed, and nowhere else does the correction change anything —
    which is why the random test below could not see it. Sixty scattered points
    hit a 1.4 m ring almost never, and it passed while the correction was
    removed. Checked by removing it again.
    """
    sun = SunPosition(altitude=30.0, azimuth=180.0)
    fence = Obstacle(footprint=_rect(0, 10, 6, 0.2), height=1.2)
    behind = Point(0, 11.6)

    assert is_shaded(behind, fence, sun), "on the ground it is in the fence's shadow"
    assert not is_shaded(behind, fence, sun, 0.8), "80 cm up it stands above it"
    assert ray_reaches_sun(behind, [fence], sun, 0.8)
    assert not ray_reaches_sun(behind, [fence], sun)


def test_a_raised_bed_agrees_across_random_scenes_too() -> None:
    """Broad rather than sharp: this one says nothing changed elsewhere."""
    random.seed(11)
    for _ in range(60):
        obstacles = [
            Obstacle(footprint=_rect(random.uniform(-15, 15), random.uniform(-15, 15),
                                     random.uniform(3, 10), random.uniform(3, 10)),
                     height=random.uniform(1.5, 10))
            for _ in range(random.randint(1, 3))
        ]
        sun = SunPosition(altitude=random.uniform(MIN_ALTITUDE + 3, 55),
                          azimuth=random.uniform(0, 360))
        point = Point(random.uniform(-15, 15), random.uniform(-15, 15))
        if any(covers(o.footprint, (point.x, point.y)) for o in obstacles):
            continue
        raised = 0.8

        model = any(is_shaded(point, o, sun, raised) for o in obstacles)
        assert model is not ray_reaches_sun(point, obstacles, sun, raised)
