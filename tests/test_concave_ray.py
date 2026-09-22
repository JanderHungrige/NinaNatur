"""Concave outlines, against a ray marched in three dimensions (doc 115).

`test_shading_is_ray_tracing.py` proved the projection for rectangles, and
rectangles are exactly the outlines on which the convex hull was right. An
L-shaped house, a house with a garage built on, a courtyard: the hull covered
their open corners at every sun, and nothing failed. Here the same instrument
meets the outlines OpenStreetMap actually draws (`concave_shapes.py`) through
both ways the model asks: `is_shaded` for one point, the grid's
`ShadowAt.covers_point` for a cell standing at its own height.

Two points in three are drawn where the hull and the exact shadow can
disagree — in an outline's notches, and in the hull of the outline and its
swept copy — and each test counts the samples on which they do. Drawn uniformly, four points in
four hundred landed there, and a reverted fix passed (review, 2026-09-22).

Where moving the point 6 cm changes the model's answer, the sample is on the
shadow's edge and the ray's 5 cm step cannot settle it; it is left out and
counted. Only the point moves: nudging the sun as well moved a low shadow's tip
by metres, and hid a 3 % error in its length.
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable

import pytest
from concave_shapes import Outline, scene

from ninanatur.garden.footprint import covers
from ninanatur.solar.field import _shadow_at, shadow_field
from ninanatur.solar.light import bed_light_value
from ninanatur.solar.position import Location, SunPosition
from ninanatur.solar.reach import is_convex
from ninanatur.solar.shading import Obstacle, Point, is_shaded, shadow_hull

Answer = Callable[[float, float], bool]
STEP_M = 0.05
FINE_M = 0.002
NUDGE_M = 0.06
NUDGES = [(NUDGE_M * math.cos(k * math.pi / 4), NUDGE_M * math.sin(k * math.pi / 4))
          for k in range(8)]
#: Samples on which the exact shadow and the hull disagree, at least.
HULL_WRONG_AT_LEAST = 50
SCENES = 800


def _ray_blocked(x: float, y: float, z: float, prisms: list[tuple[Outline, float]],
                 sun: SunPosition, step: float = STEP_M) -> bool:
    """March towards the sun until the ray is above every roof."""
    az, rise = math.radians(sun.azimuth), math.tan(math.radians(sun.altitude))
    dx, dy = math.sin(az), math.cos(az)
    reach = (max(top for _, top in prisms) - z) / rise
    d = step
    while d <= reach:
        height = z + rise * d
        for outline, top in prisms:
            if height < top and covers(outline, (x + dx * d, y + dy * d)):
                return True
        d += step
    return False


def _ray(x: float, y: float, z: float, prisms: list[tuple[Outline, float]],
         sun: SunPosition, model: bool) -> bool:
    """The marched ray; where it disagrees with the model, marched again at
    2 mm. A corner sharper than the step is crossed between two steps — a
    random star has such spikes — and a 5 cm ray reads it as air."""
    blocked = _ray_blocked(x, y, z, prisms, sun)
    return blocked if blocked == model else _ray_blocked(x, y, z, prisms, sun, FINE_M)


def _steady(answer: Answer, x: float, y: float) -> bool | None:
    """The model's answer, or None where moving the point 6 cm changes it."""
    first = answer(x, y)
    return None if any(answer(x + ex, y + ey) != first for ex, ey in NUDGES) else first


def _where_it_matters(rng: random.Random, prisms: list[tuple[Outline, float]],
                      sun: SunPosition) -> tuple[float, float]:
    """A third anywhere; a third in an outline's notches (its own hull, outside
    it), where the hull shaded open ground; a third in the hull it sweeps."""
    pick = rng.random()
    if pick < 1 / 3:
        return rng.uniform(-22, 22), rng.uniform(-22, 22)
    outline, top = rng.choice(prisms)
    # A millimetre's sweep is the outline's own hull.
    height = 0.001 if pick < 2 / 3 else top
    hull = shadow_hull(Obstacle(footprint=outline, height=height), sun)
    xs, ys = [p[0] for p in hull], [p[1] for p in hull]
    for _ in range(50):
        x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
        if covers(hull, (x, y)) and not covers(outline, (x, y)):
            return x, y
    return rng.uniform(-22, 22), rng.uniform(-22, 22)


def _hull_says(prisms: list[tuple[Outline, float]], sun: SunPosition, x: float, y: float,
               z: float) -> bool:
    """What the hull alone answered, before 2026-09-22."""
    return any(covers(shadow_hull(Obstacle(footprint=o, height=top - z), sun), (x, y))
               for o, top in prisms if top > z)


def _one_point(prisms: list[tuple[Outline, float]], z: float, sun: SunPosition) -> Answer:
    """The model as a bed's point asks it, `z` the bed's height."""
    houses = [Obstacle(footprint=o, height=top) for o, top in prisms]
    return lambda x, y: any(is_shaded(Point(x, y), house, sun, z) for house in houses)


def _one_cell(prisms: list[tuple[Outline, float]], z: float, sun: SunPosition) -> Answer:
    """The model as the grid asks it: every outline swept onto the lowest
    ground (zero), as `shadow_field` sweeps them, and the cell at height z."""
    shadows = [_shadow_at(Obstacle(footprint=o, height=top, base=0.0), sun, 6)
               for o, top in prisms]
    return lambda x, y: any(s.covers_point(x, y, z) for s in shadows)


Model = Callable[[list[tuple[Outline, float]], float, SunPosition], Answer]


def _agree(seed: int, model: Model, height: Callable[[random.Random], float],
           floor: Callable[[random.Random], float]) -> None:
    """The model against the ray over random scenes, and how often the hull
    would have been wrong on them."""
    rng = random.Random(seed)
    checked = edges = hull_wrong = 0
    for _ in range(SCENES):
        prisms = [(o, height(rng)) for o in scene(rng)]
        sun, z = _sun(rng), floor(rng)
        x, y = _where_it_matters(rng, prisms, sun)
        if any(covers(o, (x, y)) and z < top for o, top in prisms):
            continue
        steady = _steady(model(prisms, z, sun), x, y)
        if steady is None:
            edges += 1
            continue
        checked += 1
        assert steady == _ray(x, y, z, prisms, sun, steady), (
            f"({x:.2f}, {y:.2f}, {z:.2f}), sun {sun.altitude:.1f}/{sun.azimuth:.1f}, {prisms}")
        hull_wrong += _hull_says(prisms, sun, x, y, z) and not steady
    assert checked > SCENES * 0.6 and edges < checked / 10, (checked, edges, hull_wrong)
    assert hull_wrong >= HULL_WRONG_AT_LEAST, hull_wrong


def _sun(rng: random.Random) -> SunPosition:
    return SunPosition(altitude=rng.uniform(8, 60), azimuth=rng.uniform(0, 360))


def test_the_shapes_are_concave() -> None:
    rng = random.Random(3)
    outlines = [o for _ in range(200) for o in scene(rng)]
    assert sum(not is_convex(o) for o in outlines) > 0.9 * len(outlines)


def test_one_point_agrees_with_the_ray_round_concave_houses() -> None:
    """On the ground, and on a bed raised 0.8 m."""
    _agree(26, _one_point, lambda r: r.uniform(2.5, 12), lambda r: r.choice([0.0, 0.0, 0.8]))


def test_a_cell_agrees_with_the_ray_on_any_ground() -> None:
    """Houses on ground of their own, up to 2 m above the lowest, and cells
    half on the lowest ground, half above it. A concave outline takes the exact
    reach at every height; only a convex one leaves the lowest ground to the
    polygon."""
    _agree(62, _one_cell, lambda r: r.uniform(0, 2) + r.uniform(2.5, 12),
           lambda r: r.choice([0.0, r.uniform(0, 2)]))


def test_the_corner_of_an_l_gets_its_four_hours() -> None:
    """The case the wave's plan measured on 2026-09-07 (plan 03, E1): a 10 × 10 m
    house, 9 m high, with its north-east quarter open, in Wuppertal. A bed in
    the open quarter read 0.00 h under the hull; it gets about four — by the
    bed's own sample and by the grid alike."""
    wuppertal = Location(51.25, 7.15)
    ell = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 5.0), (5.0, 10.0), (0.0, 10.0)]
    hull = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 10.0), (0.0, 10.0)]
    corner = Point(7.5, 7.5)
    house = [Obstacle(footprint=ell, height=9.0)]
    exact = bed_light_value(wuppertal, corner, house).sun_hours
    assert 3.8 < exact < 4.3
    grid = shadow_field(wuppertal, house).sun_hours_at(corner.x, corner.y)
    assert grid == pytest.approx(exact, abs=0.01)
    assert bed_light_value(wuppertal, corner, [Obstacle(footprint=hull, height=9.0)]).sun_hours == 0
