"""A roof casts as a roof — Wave 26, feature 5 (doc 120).

Checked against a ray marched through the roof's own solid, as doc 115 asks:
the model and the drawing must both agree with what the sun actually meets.
And against the shape itself — a gable's shadow is its ridge's along the
ridge and its eaves' across it, which one averaged height gets wrong in both
directions. The houses stand away from the origin: centred on it, a wrong
offset in a roof's planes cancelled out and passed (review, 2026-09-28).
"""
from __future__ import annotations

import math
import random
from dataclasses import replace

import numpy as np
import pytest

from ninanatur.garden.casting import casting
from ninanatur.garden.footprint import covers
from ninanatur.garden.models import Element
from ninanatur.garden.roofs import Roof, shading_height
from ninanatur.garden.roofshape import surface_of
from ninanatur.solar.position import SunPosition
from ninanatur.solar.raster import Part, covered, parts_of
from ninanatur.solar.shading import Obstacle, shadow_rings
from ninanatur.solar.sweep import RoofSolid

Ring = list[tuple[float, float]]
#: Where the houses stand: far enough from the origin that no term cancels.
AWAY = (37.0, -21.0)


def _at(outline: Ring, dx: float = AWAY[0], dy: float = AWAY[1]) -> Ring:
    return [(x + dx, y + dy) for x, y in outline]


#: 12 m east–west, 10 m north–south: its ridge runs along the long axis, east
#: to west, so the pitches face north and south.
HOUSE = _at([(-6.0, -5.0), (6.0, -5.0), (6.0, 5.0), (-6.0, 5.0)])
#: A square, whose hip roof is a pyramid: its ridge is a point.
SQUARE = _at([(-5.0, -5.0), (5.0, -5.0), (5.0, 5.0), (-5.0, 5.0)])
#: A trapezoid and an L, whose ridge — the roof's rectangle's — runs outside
#: the walls: the shapes the drawing got wrong (review, 2026-09-22).
TRAPEZOID = _at([(-6.0, -5.0), (6.0, -5.0), (3.0, 5.0), (-3.0, 5.0)])
ELL = _at([(-6.0, -5.0), (6.0, -5.0), (6.0, 0.0), (0.0, 0.0), (0.0, 5.0), (-6.0, 5.0)])


def _roofed(footprint: Ring, roof: Roof, height: float, eaves: float,
            fall: float | None = None) -> Obstacle:
    surface = surface_of(footprint, roof, height, eaves, fall)
    assert surface is not None
    solid = RoofSolid(planes=surface.planes(), ridge=surface.ridge, eaves=surface.eaves_m)
    return Obstacle(footprint=footprint, height=height, roof=solid)


def _marched(obstacle: Obstacle, x: float, y: float, sun: SunPosition,
             z: float = 0.0) -> bool:
    """Whether the ray from (x, y, z) towards the sun meets the roof's solid,
    walked in centimetres — the instrument, not the model (doc 115)."""
    assert obstacle.roof is not None
    east, north = math.sin(math.radians(sun.azimuth)), math.cos(math.radians(sun.azimuth))
    rise = math.tan(math.radians(sun.altitude))
    reach = (obstacle.height - z) / rise + 1.0
    for step in np.arange(0.0, reach, 0.01):
        px, py, pz = x + east * step, y + north * step, z + rise * step
        if covers(obstacle.footprint, (px, py)) and pz <= obstacle.roof.height_at(px, py):
            return True
    return False


def _counted(parts: list[Part], x: float, y: float, sun: SunPosition, z: float = 0.0) -> bool:
    """What the light model makes of the same point (`raster.covered`)."""
    east, north = math.sin(math.radians(sun.azimuth)), math.cos(math.radians(sun.azimuth))
    cot = 1.0 / math.tan(math.radians(sun.altitude))
    return any(bool(covered(part, np.array([[x]]), np.array([[y]]), np.full((1, 1), z),
                            east, north, cot)[0, 0]) for part in parts)


def _inside(rings: list[Ring], x: float, y: float) -> bool:
    """Inside a frame drawn in one path under the non-zero rule."""
    winding = 0
    for ring in rings:
        for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True):
            if ay <= y < by and (bx - ax) * (y - ay) - (x - ax) * (by - ay) > 0:
                winding += 1
            elif by <= y < ay and (bx - ax) * (y - ay) - (x - ax) * (by - ay) < 0:
                winding -= 1
    return winding != 0


def _near(outline: Ring, rng: random.Random) -> tuple[float, float]:
    """A point within 25 m of the house, outside it."""
    while True:
        x, y = AWAY[0] + rng.uniform(-25.0, 25.0), AWAY[1] + rng.uniform(-25.0, 25.0)
        if not covers(outline, (x, y)):
            return x, y


@pytest.mark.parametrize(("roof", "fall"), [(Roof.GABLE, None), (Roof.HIP, None),
                                            (Roof.PENT, 180.0)])
def test_the_model_counts_the_shadow_the_ray_meets(roof: Roof, fall: float | None) -> None:
    house = _roofed(HOUSE, roof, 9.0, 5.0, fall)
    parts, rng, disagreed = parts_of([house]), random.Random(120), []
    for _ in range(400):
        sun = SunPosition(altitude=rng.uniform(6.0, 70.0), azimuth=rng.uniform(60.0, 300.0))
        x, y = _near(HOUSE, rng)
        if _counted(parts, x, y, sun) != _marched(house, x, y, sun):
            disagreed.append((round(x, 2), round(y, 2), round(sun.altitude, 1)))
    assert not disagreed, disagreed[:5]


@pytest.mark.parametrize("base", [0.0, 120.0])
@pytest.mark.parametrize(("roof", "fall"), [(Roof.GABLE, None), (Roof.HIP, None),
                                            (Roof.PENT, 90.0)])
def test_the_slow_reference_answers_what_the_raster_does(roof: Roof, fall: float | None,
                                                         base: float) -> None:
    """A roof's reference is `shading.is_shaded`, arithmetic of its own; it
    must agree with the raster on flat ground and on a hillside 120 m up."""
    from ninanatur.solar.shading import Point, is_shaded

    house = replace(_roofed(HOUSE, roof, 9.0, 5.0, fall), base=base)
    parts, rng = parts_of([house]), random.Random(117)
    for _ in range(300):
        sun = SunPosition(altitude=rng.uniform(6.0, 70.0), azimuth=rng.uniform(60.0, 300.0))
        x, y = _near(HOUSE, rng)
        raised = rng.choice([0.0, 0.0, 1.5])
        assert is_shaded(Point(x, y), house, sun, raised) == _counted(
            parts, x, y, sun, base + raised), (x, y, sun, raised)


def test_a_roofs_planes_stand_where_the_house_stands() -> None:
    """Read straight off the planes, on a house away from the origin: a sign
    wrong in a plane's offset lowered a whole roof below ground, and every
    other check read the same wrong planes and agreed (review, 2026-09-28)."""
    x0, y0 = AWAY
    gable = surface_of(HOUSE, Roof.GABLE, 9.0, 5.0)
    assert gable is not None and len(gable.planes()) == 2
    assert gable.height_at(x0, y0) == pytest.approx(9.0)          # the ridge
    assert gable.height_at(x0 + 3.0, y0 + 5.0) == pytest.approx(5.0)  # the north eaves
    assert gable.height_at(x0 - 2.0, y0 - 2.5) == pytest.approx(7.0)  # halfway down
    pent = surface_of(HOUSE, Roof.PENT, 9.0, 5.0, 180.0)  # falling south
    assert pent is not None and len(pent.planes()) == 1, "a pent has one face"
    assert pent.height_at(x0, y0 + 5.0) == pytest.approx(9.0)     # its upper edge
    assert pent.height_at(x0, y0 - 5.0) == pytest.approx(5.0)     # its lower
    assert pent.height_at(x0, y0) == pytest.approx(7.0)


def test_a_hips_corner_is_flat_where_it_used_to_dip() -> None:
    """The height came from the distance to the ridge *segment*, which curves
    round its ends: a hip's corners sat below its own planes (doc 120). The
    old surface and the planes agree at the corner and on the ridge; between
    them the planes stand higher."""
    x0, y0 = AWAY
    surface = surface_of(HOUSE, Roof.HIP, 9.0, 5.0)
    assert surface is not None and surface.hipped
    assert surface.height_at(x0 + 6.0, y0 + 5.0) == pytest.approx(5.0)
    assert surface.height_at(x0, y0) == pytest.approx(9.0)
    # (4, 4): the north face, 4 m from the ridge line — the cone said 5.0.
    assert surface.height_at(x0 + 4.0, y0 + 4.0) == pytest.approx(5.8)
    pitch, aspect = surface.slope_aspect_at(x0 + 4.0, y0 + 4.0)
    assert pitch == pytest.approx(math.degrees(math.atan(0.8)))
    assert aspect == pytest.approx(180.0), "the north face climbs south"


def test_a_gable_shades_by_its_ridge_along_it_and_by_its_eaves_across_it() -> None:
    """One averaged height (`RISE_KEPT`, 7 m here) is wrong both ways: too far
    where the roof has already come down, too short under the ridge."""
    x0, y0 = AWAY
    house = _roofed(HOUSE, Roof.GABLE, 9.0, 5.0)
    parts, guess = parts_of([house]), shading_height(9.0, Roof.GABLE, 5.0)
    assert guess == 7.0

    high = SunPosition(altitude=45.0, azimuth=180.0)  # cot 1: the eaves decide
    assert _counted(parts, x0, y0 + 9.5, high) and not _counted(parts, x0, y0 + 10.5, high)
    assert 5.0 + guess > 10.5, "the block's shadow reached further"

    low = SunPosition(altitude=20.0, azimuth=180.0)  # cot 2.75: the ridge does
    cot = 1.0 / math.tan(math.radians(20.0))
    ridge_reach, block_reach = 9.0 * cot, 5.0 + guess * cot
    assert ridge_reach > block_reach, (ridge_reach, block_reach)
    assert _counted(parts, x0, y0 + (ridge_reach + block_reach) / 2, low)
    assert not _counted(parts, x0, y0 + ridge_reach + 0.5, low)


@pytest.mark.parametrize(("outline", "roof", "fall"), [
    (HOUSE, Roof.GABLE, None), (HOUSE, Roof.GABLE, 180.0), (HOUSE, Roof.PENT, 172.0),
    (HOUSE, Roof.HIP, None), (SQUARE, Roof.HIP, None),
    (TRAPEZOID, Roof.GABLE, None), (TRAPEZOID, Roof.HIP, None),
    (ELL, Roof.GABLE, None), (ELL, Roof.HIP, None), (ELL, Roof.PENT, 180.0),
])
def test_the_plan_draws_the_shadow_the_model_counts(outline: Ring, roof: Roof,
                                                    fall: float | None) -> None:
    """Feature 1's rule, kept for roofs (doc 116): a point is inside the drawn
    frame exactly when the model counts it shaded. It was not — an L's hull
    filled its own notch, a ridge that ended a millionth of a metre outside
    the wall was left out, and a hip's ridge was never drawn at all."""
    house = _roofed(outline, roof, 9.0, 5.0, fall)
    parts, rng = parts_of([house]), random.Random(5)
    for _ in range(40):
        sun = SunPosition(altitude=rng.uniform(8.0, 65.0), azimuth=rng.uniform(70.0, 290.0))
        rings = shadow_rings([house], sun)
        for _point in range(60):
            x, y = _near(outline, rng)
            assert _inside(rings, x, y) == _counted(parts, x, y, sun), (x, y, sun)


@pytest.mark.parametrize("outline", [HOUSE, SQUARE])
def test_a_hips_ridge_throws_the_far_end_of_its_shadow(outline: Ring) -> None:
    """A hip's ridge ends — a pyramid's apex — lie inside its walls, where
    three planes meet, and they throw the farthest shadow. Cast only where its
    lines crossed the walls, a hip was drawn at its eaves (review, 2026-09-28)."""
    x0, y0 = AWAY
    house = _roofed(outline, Roof.HIP, 9.0, 5.0)
    sun = SunPosition(altitude=20.0, azimuth=180.0)
    cot = 1.0 / math.tan(math.radians(20.0))
    eaves_reach, ridge_reach = 5.0 + 5.0 * cot, 9.0 * cot
    between = y0 + (eaves_reach + ridge_reach) / 2
    assert _counted(parts_of([house]), x0, between, sun)
    assert _inside(shadow_rings([house], sun), x0, between)


def test_a_house_on_surveyed_ground_keeps_its_roof() -> None:
    """`standing_on` rebuilt an obstacle field by field and dropped the roof,
    so every house on terrain — most of them — cast as a block again, and a
    taller one than before the feature (review, 2026-09-22)."""
    from ninanatur.garden.ground import standing_on
    from ninanatur.geo.terrain import TerrainWindow

    x0, y0 = AWAY
    window = TerrainWindow(min_x=-50.0, min_y=-80.0, cell_m=1.0, cols=150, rows=150,
                           heights=[120.0] * 22_500, source="Test", licence="—",
                           attribution="—", vertical_step_m=0.01)
    [placed] = standing_on([_roofed(HOUSE, Roof.GABLE, 9.0, 5.0)], window)
    assert placed.roof is not None and placed.base == 120.0
    parts = parts_of([placed])
    assert [len(part.roof) for part in parts] == [2]
    sun = SunPosition(altitude=45.0, azimuth=180.0)  # the eaves decide, as on the flat
    assert not _counted(parts, x0, y0 + 10.5, sun, 120.0)
    assert _counted(parts, x0, y0 + 9.5, sun, 120.0)


def _element(roof: str, eaves: float = 5.0, fall: float | None = None) -> Element:
    return Element(element_id=1, kind="house", shape="polygon", x=0.0, y=0.0,
                   points=[list(p) for p in HOUSE], height=9.0, roof=roof, eaves_m=eaves,
                   roof_fall_deg=fall)


def test_what_each_roof_casts() -> None:
    """Planes where the model knows them; the height its cells stand on where
    a known shape is too shallow to pitch; `RISE_KEPT`'s guess only where
    nobody has said what the shape is (doc 120)."""
    gable = casting(_element("gable"))
    assert gable.roof is not None and gable.height == 9.0
    pent = casting(_element("pent", fall=180.0))
    assert pent.roof is not None and len(pent.roof.planes) == 1
    shallow = casting(_element("gable", eaves=8.8))  # 2.3°: under MIN_PITCH_DEG
    assert shallow.roof is None and shallow.height == 9.0, "as high as its cells stand"
    for unknown in ("mix", "other", "unknown"):
        block = casting(_element(unknown))
        assert block.roof is None
        assert block.height == shading_height(9.0, Roof(unknown), 5.0)
    unsurveyed = casting(_element("pent"))
    assert unsurveyed.roof is None and unsurveyed.height == shading_height(9.0, Roof.PENT, 5.0)


def test_the_slow_field_refuses_a_roof_rather_than_casting_a_block() -> None:
    """It rebuilt each obstacle field by field and dropped the roof, the bug
    `standing_on` had (review, 2026-09-28): it casts prisms, and says so."""
    from ninanatur.solar.field import shadow_field
    from ninanatur.solar.position import Location

    with pytest.raises(ValueError, match="prisms"):
        shadow_field(Location(51.25, 7.15), [_roofed(HOUSE, Roof.GABLE, 9.0, 5.0)], month=6)


def test_the_days_playback_draws_the_roof_the_model_counts() -> None:
    """`/shadows` kept its own copy of the old rule and drew a block of the
    averaged height while the map counted planes (review, 2026-09-28)."""
    from ninanatur.garden.models import Garden
    from ninanatur.solar.day import shadow_day

    element = _element("gable")
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="G", latitude=51.25,
                    longitude=7.15, created_at="", updated_at="", elements=[element])
    parts, rng = parts_of([casting(element)]), random.Random(26)
    frames = shadow_day(None, garden, month=6).frames
    assert frames
    for frame in frames[::3]:
        sun = SunPosition(altitude=frame.altitude, azimuth=frame.azimuth)
        rings = [[(float(x), float(y)) for x, y in ring] for ring in frame.polygons]
        for _ in range(60):
            x, y = _near(HOUSE, rng)
            assert _inside(rings, x, y) == _counted(parts, x, y, sun), (x, y, frame.minute)
