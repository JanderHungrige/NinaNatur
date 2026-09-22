"""OpenStreetMap's areas cut to the plan, in garden metres (doc 114)."""
from __future__ import annotations

import pytest

from ninanatur.geo.landcover_clip import (
    LANDCOVER_MARGIN_M,
    Box,
    box_around,
    clip_to_box,
    degrees_of,
    in_garden,
    signed_area,
)
from ninanatur.geo.osm_landcover import OsmArea
from ninanatur.geo.projection import LatLon, Metres, to_latlon

ANCHOR = LatLon(lat=52.3962, lon=13.2322)
BOX = Box(-50.0, -50.0, 50.0, 50.0)


def _area(*rings: list[tuple[float, float]], inners: tuple[list[tuple[float, float]], ...] = (),
          kind: str = "wood") -> OsmArea:
    """An area whose rings are given in garden metres around ANCHOR."""
    def degrees(ring: list[tuple[float, float]]) -> list[LatLon]:
        return [to_latlon(Metres(x, y), ANCHOR) for x, y in ring]

    return OsmArea(osm_id=1, kind=kind, outers=[degrees(r) for r in rings],
                   inners=[degrees(r) for r in inners])


def _square(x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def test_a_ring_across_the_edge_is_cut_along_it() -> None:
    cut = clip_to_box(_square(30, -10, 80, 10), BOX)
    assert max(x for x, _ in cut) == pytest.approx(50.0)
    assert signed_area(cut) == pytest.approx(20 * 20)


def test_a_forest_around_the_whole_box_becomes_the_box() -> None:
    [area] = in_garden([_area(_square(-900, -900, 900, 900))], ANCHOR, BOX)
    [ring] = area.rings
    assert signed_area(ring) == pytest.approx(100 * 100)
    assert {x for x, _ in ring} == {-50.0, 50.0}


def test_an_area_outside_the_box_is_left_out() -> None:
    assert in_garden([_area(_square(200, 200, 300, 300))], ANCHOR, BOX) == []


def test_a_sliver_along_the_edge_is_no_colour() -> None:
    """Ten centimetres of a field inside the box is a cut artefact, not a field."""
    assert in_garden([_area(_square(49.9, -5, 90, 5))], ANCHOR, BOX) == []
    # Two metres of it is a field.
    assert len(in_garden([_area(_square(48.0, -5, 90, 5))], ANCHOR, BOX)) == 1


def test_points_are_decimetres() -> None:
    [area] = in_garden([_area(_square(1.234, 2.345, 20.987, 30.012))], ANCHOR, BOX)
    for x, y in area.rings[0]:
        assert (round(x, 1), round(y, 1)) == (x, y)


def test_outer_rings_run_anticlockwise_and_holes_clockwise() -> None:
    """For the nonzero rule: two overlapping lawns stay one lawn, a hole a hole."""
    clockwise = list(reversed(_square(-40, -40, 40, 40)))
    hole = _square(-10, -10, 10, 10)
    [area] = in_garden([_area(clockwise, inners=(hole,))], ANCHOR, BOX)
    outer, inner = area.rings
    assert signed_area(outer) > 0
    assert signed_area(inner) < 0


def test_a_hole_outside_the_box_goes_with_it() -> None:
    [area] = in_garden([_area(_square(-40, -40, 40, 40), inners=(_square(60, 60, 70, 70),))],
                       ANCHOR, BOX)
    assert len(area.rings) == 1


def test_a_shift_moves_every_point_by_it() -> None:
    """Areas placed from the rounded anchor, moved back onto the garden's streets."""
    [plain] = in_garden([_area(_square(0, 0, 20, 20))], ANCHOR, BOX)
    [moved] = in_garden([_area(_square(0, 0, 20, 20))], ANCHOR, BOX, shift=(3.0, -2.0))
    for (px, py), (mx, my) in zip(plain.rings[0], moved.rings[0], strict=True):
        assert (mx, my) == pytest.approx((px - 3.0, py + 2.0), abs=0.11)


def test_the_box_is_the_plot_and_the_margin() -> None:
    box = box_around([(-10.0, -5.0), (12.0, 8.0)])
    assert box == Box(-10 - LANDCOVER_MARGIN_M, -5 - LANDCOVER_MARGIN_M,
                      12 + LANDCOVER_MARGIN_M, 8 + LANDCOVER_MARGIN_M)


def test_the_query_box_is_the_same_box_in_degrees() -> None:
    south, west, north, east = degrees_of(BOX, ANCHOR)
    assert south < ANCHOR.lat < north
    assert west < ANCHOR.lon < east
    assert (north - south) * 111_320 == pytest.approx(100.0, rel=1e-6)
