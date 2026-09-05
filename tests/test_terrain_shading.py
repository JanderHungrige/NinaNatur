"""Buildings standing on ground, checked against a ray marched in three dimensions.

Wave 16 proved its shadow projection this way and Wave 17 changes what that
projection means: the receiving point now has a height of its own, so the swept
polygon is no longer the whole answer. The polygon is swept onto the garden's
lowest ground — a superset — and a point standing higher gets an exact check.

An argument for why that is right is in the code. This is the measurement.
"""
from __future__ import annotations

import math
import random

import pytest

from ninanatur.garden.footprint import covers
from ninanatur.solar.field import shadow_field
from ninanatur.solar.position import Location, SunPosition
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle

STEP_M = 0.05
REACH_M = 300.0


def ray_reaches_sun(
    x: float, y: float, z: float, obstacles: list[Obstacle], sun: SunPosition
) -> bool:
    """March from a point at height z towards the sun.

    An obstacle is solid from the ground up to its top, **including the ground
    it stands on**. That is a modelling statement worth being explicit about: a
    shed on a bank three metres up is not a shed floating in air with light
    passing underneath, it is three metres of earth with a shed on top. The
    first version of this helper let rays through below the base and disagreed
    with the model in eleven scenes out of two hundred — the helper was wrong.
    """
    azimuth = math.radians(sun.azimuth)
    dx, dy = math.sin(azimuth), math.cos(azimuth)
    dz = math.tan(math.radians(sun.altitude))
    distance = STEP_M
    while distance < REACH_M:
        px, py = x + dx * distance, y + dy * distance
        pz = z + dz * distance
        for obstacle in obstacles:
            if pz < obstacle.top and covers(obstacle.footprint, (px, py)):
                return False
        distance += STEP_M
    return True


def _one_moment_field(
    obstacles: list[Obstacle], sun: SunPosition, floor: float
) -> object:
    """The field machinery, asked about a single hand-made sun position."""
    from ninanatur.solar.field import ShadowField, _shadow_at

    receiver = floor
    lifted = [
        Obstacle(footprint=o.footprint, height=o.top - receiver, base=receiver)
        for o in obstacles
        if o.top - receiver > 0
    ]
    return ShadowField(
        moments=[[_shadow_at(o, sun, 6) for o in lifted]],
        halves=[sun.azimuth < 180.0],
        days=1,
        year=2026,
    )


def _model_says_shaded(
    x: float, y: float, z: float, obstacles: list[Obstacle], sun: SunPosition, floor: float
) -> bool:
    field = _one_moment_field(obstacles, sun, floor)
    return field.sun_hours_at(x, y, z) == 0.0  # type: ignore[attr-defined]


def test_the_model_and_the_ray_agree_across_random_scenes() -> None:
    """Two hundred scenes with the point at a height of its own.

    A random scene rather than a chosen one, because a chosen one tests what its
    author already thought of.
    """
    rng = random.Random(1704)
    disagreements = []
    compared = 0
    for _ in range(200):
        cx, cy = rng.uniform(-15, 15), rng.uniform(-15, 15)
        w, d = rng.uniform(1, 8), rng.uniform(1, 8)
        base = rng.uniform(0.0, 4.0)
        obstacle = Obstacle(
            footprint=[(cx - w, cy - d), (cx + w, cy - d), (cx + w, cy + d), (cx - w, cy + d)],
            height=rng.uniform(1.5, 10.0),
            base=base,
        )
        sun = SunPosition(
            altitude=rng.uniform(MIN_ALTITUDE + 1, 60.0), azimuth=rng.uniform(60.0, 300.0)
        )
        px, py = rng.uniform(-20, 20), rng.uniform(-20, 20)
        pz = rng.uniform(0.0, 5.0)
        floor = 0.0
        if covers(obstacle.footprint, (px, py)):
            # Inside the solid. Not a garden point — you cannot plant inside a
            # wall — and the marching ray's answer there is a 5 cm stepping
            # artefact rather than a fact about the model.
            continue

        compared += 1
        lit = ray_reaches_sun(px, py, pz, [obstacle], sun)
        shaded = _model_says_shaded(px, py, pz, [obstacle], sun, floor)
        if lit == shaded:
            disagreements.append((px, py, pz, obstacle, sun))
    assert compared > 150, f"only {compared} scenes were actually compared"
    assert not disagreements, f"{len(disagreements)} scenes disagree, e.g. {disagreements[0]}"


def test_a_garden_uphill_of_a_house_sees_over_it() -> None:
    """The whole point of the feature, stated as one number.

    An 8 m house due south. Standing on its own level the garden is shaded most
    of the day; on ground level with its ridge it is not shaded at all.
    """
    house = Obstacle(footprint=[(-3, -8), (3, -8), (3, -4), (-3, -4)], height=8.0)
    field = shadow_field(Location(latitude=52.0, longitude=10.0), [house])

    at_the_bottom = field.sun_hours_at(0.0, 0.0, 0.0)
    halfway_up = field.sun_hours_at(0.0, 0.0, 4.0)
    level_with_the_ridge = field.sun_hours_at(0.0, 0.0, 8.0)

    assert at_the_bottom < halfway_up < level_with_the_ridge
    assert level_with_the_ridge == pytest.approx(field.sun_hours_at(0.0, 40.0, 0.0), abs=0.1)


def test_a_house_on_a_bank_casts_as_though_it_were_taller() -> None:
    """Three metres of ground under a 4 m shed shades like a 7 m one — which is
    the error the flat model made in every garden on a slope."""
    location = Location(latitude=52.0, longitude=10.0)
    footprint = [(-3, -8), (3, -8), (3, -5), (-3, -5)]

    on_the_flat = shadow_field(location, [Obstacle(footprint=footprint, height=4.0)])
    on_a_bank = shadow_field(location, [Obstacle(footprint=footprint, height=4.0, base=3.0)])
    as_if_taller = shadow_field(location, [Obstacle(footprint=footprint, height=7.0)])

    assert on_a_bank.sun_hours_at(0.0, 0.0) < on_the_flat.sun_hours_at(0.0, 0.0)
    assert on_a_bank.sun_hours_at(0.0, 0.0) == pytest.approx(
        as_if_taller.sun_hours_at(0.0, 0.0), abs=0.05
    )


def test_flat_ground_is_untouched_by_any_of_this() -> None:
    """Every garden built before Wave 17 stands on ground zero, and its answer
    must not have moved by a minute."""
    location = Location(latitude=52.0, longitude=10.0)
    wall = Obstacle(footprint=[(-5, -3), (5, -3), (5, -2.6), (-5, -2.6)], height=4.0)
    field = shadow_field(location, [wall])
    assert field.sun_hours_at(0.0, 0.0, 0.0) == field.sun_hours_at(0.0, 0.0)
