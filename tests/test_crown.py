"""A crown is an ellipsoid on a trunk — Wave 26, feature 6 (doc 121).

Checked against what does not share its arithmetic: a chord through the
centre has the length the ellipsoid's own axes give it; a ray marched through
it in centimetres measures the same crossing, from outside it or from within;
the grid and a point agree, on uneven cells and with the crown off the grid;
the drawn shadow is where the ray meets the crown. And against the plan's
promise: no crossing passes less than the share the old cylinder passed.

Every crown here is an ellipsoid and not a ball, one tall and one flat — the
first version of these tests cast only spheres, and swapping a crown's two
semi-axes anywhere passed them all (review, 2026-09-28).
"""
from __future__ import annotations

import math
import random

import numpy as np
import pytest

from ninanatur.solar.crown import Crown, CrownSolid, chord, outline, passing, standing
from ninanatur.solar.position import SunPosition
from ninanatur.solar.raster import Directions, parts_of, point_sums
from ninanatur.solar.raster_grid import Cells, grid_sums
from ninanatur.solar.shading import Obstacle, Point, is_shaded, shadow_offset, shadow_rings

#: A tree of 12 m, its crown 6 m across and starting at 2 m: 3 m round, 5 m
#: high, its middle 7 m up.
TALL = Crown(x=3.0, y=-2.0, radius=3.0, base=2.0, top=12.0)
#: A spreading crown, 10 m across and 4 m deep, from 6 m up.
FLAT = Crown(x=-6.0, y=6.0, radius=5.0, base=6.0, top=10.0)
CROWNS = (TALL, FLAT)


def _toward(sun: SunPosition) -> tuple[float, float, float]:
    az = math.radians(sun.azimuth)
    return math.sin(az), math.cos(az), 1.0 / math.tan(math.radians(sun.altitude))


def _unit(sun: SunPosition) -> tuple[float, float, float]:
    h, az = math.radians(sun.altitude), math.radians(sun.azimuth)
    return math.cos(h) * math.sin(az), math.cos(h) * math.cos(az), math.sin(h)


def _marched(solid: CrownSolid, x: float, y: float, z: float, sun: SunPosition) -> float:
    """The crossing's length, walked in centimetres along the ray: the
    instrument, not the model (doc 115)."""
    ux, uy, uz = _unit(sun)
    inside = 0
    for step in range(int(80 / 0.01)):
        s = step * 0.01
        px, py, pz = x + ux * s, y + uy * s, z + uz * s
        if ((px - solid.cx) ** 2 + (py - solid.cy) ** 2) / solid.rh ** 2 \
                + (pz - solid.cz) ** 2 / solid.rv ** 2 <= 1.0:
            inside += 1
    return inside * 0.01


def _through_centre(solid: CrownSolid, sun: SunPosition) -> float:
    """The model's chord along this sun's ray through the crown's middle."""
    ux, uy, uz = _unit(sun)
    back = 40.0
    return float(chord(solid, solid.cx - ux * back, solid.cy - uy * back,
                       solid.cz - uz * back, *_toward(sun)))


def test_a_chord_through_the_centre_is_what_the_axes_make_it() -> None:
    """Along a unit direction u through its middle, an ellipsoid's chord is
    2 / √(u_h²/r_h² + u_z²/r_v²) — nothing the quadratic shares."""
    for crown in CROWNS:
        solid = standing(crown, 0.0)
        for altitude, azimuth in ((3.0, 180.0), (20.0, 90.0), (45.0, 200.0), (70.0, 250.0),
                                  (89.5, 135.0)):
            sun = SunPosition(altitude=altitude, azimuth=azimuth)
            ux, uy, uz = _unit(sun)
            expected = 2.0 / math.sqrt((ux * ux + uy * uy) / solid.rh ** 2
                                       + uz * uz / solid.rv ** 2)
            assert _through_centre(solid, sun) == pytest.approx(expected, rel=1e-6), (crown, sun)
    # A ray that passes beside it crosses nothing.
    assert float(chord(standing(TALL, 0.0), 20.0, 0.0, 0.0,
                       *_toward(SunPosition(45.0, 180.0)))) == 0.0


def test_the_crossing_is_the_one_a_marched_ray_measures() -> None:
    """From the ground, from under a raised bed's height, and from inside
    the crown — a bed's surface in a shrub, a roof cell under a tree."""
    rng = random.Random(121)
    for crown in CROWNS:
        solid = standing(crown, 0.0)
        for _ in range(120):
            sun = SunPosition(altitude=rng.uniform(5.0, 62.0),
                              azimuth=rng.uniform(60.0, 300.0))
            x, y = rng.uniform(-20.0, 20.0), rng.uniform(-20.0, 20.0)
            z = rng.choice([0.0, 0.0, 1.5])
            assert float(chord(solid, x, y, z, *_toward(sun))) == pytest.approx(
                _marched(solid, x, y, z, sun), abs=0.03), (crown, x, y, z, sun)
        for _ in range(60):
            sun = SunPosition(altitude=rng.uniform(5.0, 62.0),
                              azimuth=rng.uniform(60.0, 300.0))
            angle, reach = rng.uniform(0, 2 * math.pi), rng.uniform(0.0, 0.6)
            x = crown.x + reach * solid.rh * math.cos(angle)
            y = crown.y + reach * solid.rh * math.sin(angle)
            z = solid.cz + rng.uniform(-0.6, 0.6) * solid.rv
            assert float(chord(solid, x, y, z, *_toward(sun))) == pytest.approx(
                _marched(solid, x, y, z, sun), abs=0.03), (crown, x, y, z, sun)


def test_the_longest_chord_passes_the_old_share_and_every_other_passes_more() -> None:
    """The plan's promise (doc 121), for the longest chord the crown really
    has — along its long axis, the tall crown's vertical and the flat one's
    horizontal — and for random ones."""
    rng = random.Random(7)
    for crown, along in ((TALL, SunPosition(89.9, 180.0)), (FLAT, SunPosition(0.01, 180.0))):
        solid = standing(crown, 0.0)
        longest = _through_centre(solid, along)
        assert longest == pytest.approx(10.0, abs=1e-3)
        assert float(passing(0.2, solid, np.array(longest))) == pytest.approx(0.2, abs=1e-4)
        for _ in range(300):
            sun = SunPosition(altitude=rng.uniform(1.0, 89.0), azimuth=rng.uniform(0.0, 360.0))
            depth = chord(solid, rng.uniform(-20.0, 20.0), rng.uniform(-20.0, 20.0),
                          rng.uniform(0.0, 12.0), *_toward(sun))
            assert float(passing(0.2, solid, depth)) >= 0.2 - 1e-9
        assert float(passing(0.2, solid, np.array(0.0))) == 1.0, "a ray that misses passes it all"
        assert float(passing(0.0, solid, np.array(0.5))) == 0.0, "a crown that passes nothing"


def test_a_low_sun_passes_under_a_crown_on_its_trunk() -> None:
    """The cylinder shaded the ground under a crown at every angle. A crown
    whose base is at 2 m lets a 10° sun in beneath it, and puts a high sun's
    shade where a ray meets it: north of the trunk, not at its foot. (From
    the foot of this crown, 7 m below its middle, a 55° sun passes beside
    it and a 62° one crosses it.)"""
    crown = Obstacle(footprint=_circle(TALL), height=TALL.top, transmission=0.2, crown=TALL)
    cylinder = Obstacle(footprint=_circle(TALL), height=TALL.top, transmission=0.2)
    low = SunPosition(altitude=10.0, azimuth=180.0)
    below = Point(TALL.x, TALL.y)
    assert is_shaded(below, cylinder, low)
    assert not is_shaded(below, crown, low)
    assert not is_shaded(below, crown, SunPosition(altitude=55.0, azimuth=180.0))
    assert is_shaded(below, crown, SunPosition(altitude=62.0, azimuth=180.0))
    high = SunPosition(altitude=60.0, azimuth=180.0)
    through_centre = Point(TALL.x, TALL.y + 7.0 / math.tan(math.radians(60.0)))
    assert is_shaded(through_centre, crown, high)


def _circle(crown: Crown, points: int = 24) -> list[tuple[float, float]]:
    return [(crown.x + crown.radius * math.cos(a), crown.y + crown.radius * math.sin(a))
            for a in np.linspace(0, 2 * math.pi, points, endpoint=False)]


def _crowned(crown: Crown) -> Obstacle:
    return Obstacle(footprint=_circle(crown), height=crown.top, transmission=0.2,
                    bare_transmission=0.75, crown=crown)


def _directions(seed: int, count: int, altitudes: tuple[float, float],
                azimuths: tuple[float, float] = (70.0, 290.0)) -> Directions:
    rng = random.Random(seed)
    return Directions(
        azimuth=np.array([rng.uniform(*azimuths) for _ in range(count)]),
        altitude=np.array([rng.uniform(*altitudes) for _ in range(count)]),
        month=np.array([3, 7] * (count // 2)), weight=np.full(count, 1 / count),
        group=np.zeros(count, dtype=int), groups=1)


def _cells(xs: np.ndarray, ys: np.ndarray, z: np.ndarray) -> Cells:
    rows, cols = z.shape
    return Cells(xs=xs, ys=ys, cell_m=float(xs[1] - xs[0]), z=z,
                 owner=np.full((rows, cols), -1), sky=np.full((rows, cols), -1),
                 rings=np.empty((0, 360)))


def test_the_grid_says_of_a_cell_what_the_point_says() -> None:
    parts = parts_of([_crowned(TALL), _crowned(FLAT)])
    assert [p.crown is not None for p in parts] == [True, True]
    directions = _directions(3, 40, (6.0, 60.0))
    xs = np.arange(-15.0, 18.0, 1.5)
    cells = _cells(xs, xs.copy(), np.full((len(xs), len(xs)), 0.4))
    grid = grid_sums(parts, directions, cells)
    for r in range(0, len(xs), 3):
        for c in range(0, len(xs), 3):
            point = point_sums(parts, directions, float(xs[c]), float(xs[r]), 0.4)
            assert float(grid[0, r, c]) == pytest.approx(float(point[0]), abs=1e-9), (r, c)


def test_the_grid_asks_every_cell_a_crown_can_reach_whatever_its_height() -> None:
    """The grid asks a crown only about the cells under the ellipse it throws,
    from the grid's highest cell to its lowest (`raster_grid._shade_crown`).
    Cells up to 11 m — on a roof beside the tree, in its crown's height — must
    each say what the point says, or that box was cut too tight."""
    parts = parts_of([_crowned(TALL), _crowned(FLAT)])
    directions = _directions(5, 60, (5.0, 62.0))
    rng = random.Random(5)
    xs = np.arange(-20.0, 26.0, 1.0)
    heights = np.array([[rng.choice([0.0, 0.0, 2.5, 7.0, 11.0]) for _ in xs] for _ in xs])
    grid = grid_sums(parts, directions, _cells(xs, xs.copy(), heights))
    for r in range(0, len(xs), 3):
        for c in range(0, len(xs), 3):
            point = point_sums(parts, directions, float(xs[c]), float(xs[r]),
                               float(heights[r, c]))
            assert float(grid[0, r, c]) == pytest.approx(float(point[0]), abs=1e-9), (r, c)


def test_a_crown_off_the_grid_casts_into_it_as_far_as_its_shadow_reaches() -> None:
    """Neighbours' trees beside the plot. The grid decides from the square
    round a crown and its top whether it can reach the cells at all
    (`raster_grid._reaching`): one south of the grid reaches in only with the
    shadow of its upper half, one east of it only with its rim — so the
    square must be the crown's whole width and the top its real top."""
    south = Crown(x=10.0, y=-35.0, radius=4.0, base=3.0, top=14.0)
    east = Crown(x=23.0, y=-13.0, radius=4.0, base=3.0, top=14.0)
    parts = parts_of([_crowned(south), _crowned(east)])
    directions = _directions(9, 20, (18.0, 22.0), azimuths=(180.0, 180.0))
    xs = np.arange(0.0, 20.5, 1.0)
    cells = _cells(xs, xs.copy(), np.zeros((len(xs), len(xs))))
    grid = grid_sums(parts, directions, cells)
    assert float(grid[0, 1, 10]) < 0.95, "the southern crown's upper half reaches in"
    assert float(grid[0, 10, 20]) < 0.95, "the eastern crown's rim reaches in"
    for r in range(len(xs)):
        for c in range(0, len(xs), 2) if r % 2 else range(len(xs)):
            point = point_sums(parts, directions, float(xs[c]), float(xs[r]), 0.0)
            assert float(grid[0, r, c]) == pytest.approx(float(point[0]), abs=1e-9), (r, c)


def test_the_plan_draws_the_shadow_where_the_ray_meets_the_crown() -> None:
    """Doc 116's rule for a crown: its drawn ellipse is where the model
    attenuates. Points within 5 cm of the rim are left out — the drawn ring
    holds the ellipse, a polygon round a curve."""
    rng = random.Random(11)
    for crown in CROWNS:
        cast, solid = _crowned(crown), standing(crown, 0.0)
        for _ in range(30):
            sun = SunPosition(altitude=rng.uniform(8.0, 62.0),
                              azimuth=rng.uniform(70.0, 290.0))
            [ring] = shadow_rings([cast], sun)
            per_metre = shadow_offset(1.0, sun)
            assert per_metre is not None
            for _point in range(50):
                x, y = rng.uniform(-25.0, 25.0), rng.uniform(-25.0, 25.0)
                if _near_rim(solid, per_metre, x, y):
                    continue
                assert _inside(ring, x, y) == is_shaded(Point(x, y), cast, sun), (x, y, sun)


def test_the_drawn_ring_holds_the_whole_ellipse() -> None:
    """A polygon through points on an ellipse cuts inside it between them;
    the ring is pushed out so it holds every shaded point, the rim included."""
    for crown in CROWNS:
        cast, solid = _crowned(crown), standing(crown, 0.0)
        sun = SunPosition(altitude=25.0, azimuth=160.0)
        [ring] = shadow_rings([cast], sun)
        per_metre = shadow_offset(1.0, sun)
        assert per_metre is not None
        fine = outline(solid, 0.0, per_metre, points=720)
        cx, cy = sum(p[0] for p in fine) / 720, sum(p[1] for p in fine) / 720
        # The exact ellipse, just inside it: the fine ring without its own push.
        near_rim = 0.9998 * math.cos(math.pi / 720)
        for px, py in fine:
            x, y = cx + (px - cx) * near_rim, cy + (py - cy) * near_rim
            assert _inside(ring, x, y), (crown, x, y)


def _near_rim(solid: CrownSolid, per_metre: tuple[float, float], x: float, y: float) -> bool:
    """Within 5 cm of the shadow ellipse's rim, sampled finely."""
    fine = outline(solid, 0.0, per_metre, points=720)
    return min(math.hypot(x - px, y - py) for px, py in fine) < 0.05


def _inside(ring: list[tuple[float, float]], x: float, y: float) -> bool:
    winding = 0
    for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True):
        if ay <= y < by and (bx - ax) * (y - ay) - (x - ax) * (by - ay) > 0:
            winding += 1
        elif by <= y < ay and (bx - ax) * (y - ay) - (x - ax) * (by - ay) < 0:
            winding -= 1
    return winding != 0


def test_the_sky_under_a_crown_opens_beneath_it() -> None:
    """The spot under a tree, where shade beds are planned, sees the low sky
    between the trunk and the crown (doc 121); under the cylinder it saw only
    what the leaves passed."""
    from ninanatur.solar.sky import sky_directions

    cylinder = Obstacle(footprint=_circle(TALL), height=TALL.top, transmission=0.2)
    sky = sky_directions(7)
    under_crown = float(point_sums(parts_of([_crowned(TALL)]), sky, TALL.x, TALL.y)[0])
    under_cylinder = float(point_sums(parts_of([cylinder]), sky, TALL.x, TALL.y)[0])
    assert under_cylinder == pytest.approx(0.2, abs=0.01)
    assert under_crown > under_cylinder + 0.1


def test_the_slow_field_refuses_a_crown() -> None:
    from ninanatur.solar.field import shadow_field
    from ninanatur.solar.position import Location

    with pytest.raises(ValueError, match="prisms"):
        shadow_field(Location(51.25, 7.15), [_crowned(TALL)], month=6)
