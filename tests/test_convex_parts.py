"""Footprints as convex parts, whatever was drawn (doc 117).

The raster asks every shadow question of a convex part, so the split has to be
exact and has to survive what the plan and the map import actually produce:
walls drawn as lines (spurs at their inner corners, and bevelled joints whose
two corners differ in the last bit), outlines that cross themselves, corners
all on one line, and the outlines GEOS refuses to triangulate.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest
import shapely
from concave_shapes import scene
from shapely.geometry import Polygon

from ninanatur.garden.polyline import band_of
from ninanatur.solar.convex_parts import SAME_M, THIN_M, convex_parts, solid_of
from ninanatur.solar.light import bed_light_value
from ninanatur.solar.position import Location
from ninanatur.solar.raster import parts_of
from ninanatur.solar.reach import is_convex
from ninanatur.solar.shading import Obstacle, Point

Ring = list[tuple[float, float]]


def _union(parts: tuple[tuple[tuple[float, float], ...], ...]) -> shapely.Geometry:
    return shapely.union_all([Polygon(p) for p in parts])


def _exact(ring: Ring) -> None:
    """Every part convex, no edge without a direction, and together exactly
    the shape the outline encloses."""
    parts = convex_parts(ring)
    assert parts, ring
    for part in parts:
        assert is_convex(list(part)), part
        for a, b in zip(part, part[1:] + part[:1], strict=True):
            assert math.dist(a, b) > SAME_M, (part, a, b)
    solid = shapely.union_all(solid_of(ring))
    assert _union(parts).symmetric_difference(solid).area < 1e-4, ring


def test_a_convex_outline_is_its_own_part_and_an_l_is_two() -> None:
    box = [(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)]
    assert len(convex_parts(box)) == 1
    assert len(convex_parts([(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (4.0, 4.0), (4.0, 10.0),
                             (0.0, 10.0)])) == 2


def test_random_outlines_split_exactly_crossing_ones_included() -> None:
    rng = random.Random(117)
    for _ in range(150):
        for outline in scene(rng):
            _exact(outline)
    for _ in range(150):
        # Corners in any order: tangled, crossing, the way a slip of the
        # finger drags one.
        tangled = [(round(rng.uniform(-8, 8), 2), round(rng.uniform(-8, 8), 2))
                   for _ in range(rng.randint(4, 12))]
        _exact(tangled)


def test_a_wall_drawn_as_a_line_splits_without_a_directionless_edge() -> None:
    """A straight joint is bevelled into two corners one bit apart; the edge
    between them had a normal of 1e-17 and cut half the hedge out of its own
    shadow (review, 2026-09-22)."""
    hedge = band_of([(-7.1, -8.15), (-5.7, -5.35), (-4.7, -3.35), (-3.1, -0.15), (-1.3, 3.45)],
                    width=0.5)
    _exact(hedge)
    for part in parts_of([Obstacle(footprint=hedge, height=2.0)]):
        assert all(abs(math.hypot(*n) - 1.0) < 1e-9 for n in part.normals)


def test_the_spur_at_a_wall_lines_inner_corner_is_no_corner() -> None:
    wall = band_of([(0.0, 10.0), (0.0, 0.0), (10.0, 0.0)], width=0.3)
    _exact(wall)
    assert len(convex_parts(wall)) == 2


def test_an_outline_closed_on_its_first_point_is_the_same_outline() -> None:
    ell = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (4.0, 4.0), (4.0, 10.0), (0.0, 10.0)]
    assert convex_parts([*ell, ell[0]]) == convex_parts(ell)


def test_a_bow_tie_is_its_two_triangles() -> None:
    bow = [(0.0, 0.0), (4.0, 4.0), (4.0, 0.0), (0.0, 4.0)]
    _exact(bow)
    assert _union(convex_parts(bow)).area == pytest.approx(8.0)


def test_corners_on_one_line_are_a_thin_wall_not_nothing() -> None:
    """Three corners on a line enclose nothing; the old field cast their
    shadow, so a band a centimetre wide does."""
    line = [(-2.0, 0.0), (3.0, 0.0), (8.0, 0.0)]
    parts = convex_parts(line)
    assert parts and _union(parts).area == pytest.approx(10.0 * THIN_M, rel=0.05)
    # A 3 m wall south of a bed shades it: it counted as nothing (review).
    berlin = Location(52.52, 13.40)
    walled = bed_light_value(berlin, Point(3.0, 1.0), [Obstacle(footprint=line, height=3.0)])
    assert walled.sun_hours < bed_light_value(berlin, Point(3.0, 1.0), []).sun_hours - 1


def test_an_outline_geos_will_not_triangulate_is_split_anyway() -> None:
    """A repaired crossing outline on which GEOS says "unable to find a convex
    corner": it failed the whole garden's grid. Asked again snapped to a
    micrometre, it splits."""
    ring = [tuple(p) for p in json.loads(
        (Path(__file__).parent / "fixtures" / "triangulation_refused.json").read_text())]
    with pytest.raises(shapely.errors.GEOSException):
        for polygon in solid_of(ring):
            shapely.constrained_delaunay_triangles(polygon)
    _exact(ring)
