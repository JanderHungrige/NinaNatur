"""Which way a surveyed roof falls, read off its faces (doc 94).

Coordinates here are a tile's own: metres east and north, height up. A gable
twelve metres east-west and eight north-south, eaves at 6 m, ridge at 9 m.
"""
from __future__ import annotations

import pytest

from ninanatur.garden.roofs import Roof
from ninanatur.geo.roof_faces import fall_of

Point = tuple[float, float, float]

#: Ridge east-west along y = 4: one face falls south, one north.
SOUTH_FACE: list[Point] = [(0, 0, 6), (12, 0, 6), (12, 4, 9), (0, 4, 9)]
NORTH_FACE: list[Point] = [(0, 4, 9), (12, 4, 9), (12, 8, 6), (0, 8, 6)]
#: The same footprint with the ridge north-south along x = 6.
WEST_FACE: list[Point] = [(0, 0, 6), (6, 0, 9), (6, 8, 9), (0, 8, 6)]
EAST_FACE: list[Point] = [(6, 0, 9), (12, 0, 6), (12, 8, 6), (6, 8, 9)]


def _gap(a: float, b: float, period: float = 360.0) -> float:
    d = abs(a - b) % period
    return min(d, period - d)


def test_a_gable_falls_at_right_angles_to_its_ridge() -> None:
    fall = fall_of(Roof.GABLE, [SOUTH_FACE, NORTH_FACE])
    assert fall is not None
    # A gable falls both ways; its value is the one in [0, 180): north.
    assert 0.0 <= fall < 180.0
    assert _gap(fall, 0.0, 180.0) < 0.01


def test_a_ridge_across_the_long_side_is_read_as_it_is() -> None:
    """The case the long-axis assumption gets wrong: the faces fall east and
    west across a building that is longer east-west than north-south."""
    fall = fall_of(Roof.GABLE, [WEST_FACE, EAST_FACE])
    assert fall is not None
    assert _gap(fall, 90.0, 180.0) < 0.01


def test_a_hip_is_read_by_its_highest_edge() -> None:
    hip = [
        [(0, 0, 6), (12, 0, 6), (8, 4, 9), (4, 4, 9)],   # south, a trapezoid
        [(12, 8, 6), (0, 8, 6), (4, 4, 9), (8, 4, 9)],   # north, a trapezoid
        [(0, 8, 6), (0, 0, 6), (4, 4, 9)],               # west end
        [(12, 0, 6), (12, 8, 6), (8, 4, 9)],             # east end
    ]
    fall = fall_of(Roof.HIP, hip)
    assert fall is not None
    assert _gap(fall, 0.0, 180.0) < 0.01


def test_a_pyramid_has_no_ridge_to_read() -> None:
    top = (5.0, 5.0, 9.0)
    pyramid = [
        [(0, 0, 6), (10, 0, 6), top], [(10, 0, 6), (10, 10, 6), top],
        [(10, 10, 6), (0, 10, 6), top], [(0, 10, 6), (0, 0, 6), top],
    ]
    assert fall_of(Roof.HIP, pyramid) is None


def test_a_pent_falls_the_one_way_its_face_does() -> None:
    to_the_north = [(0, 0, 9), (10, 0, 9), (10, 6, 6), (0, 6, 6)]
    to_the_south = [(0, 0, 6), (10, 0, 6), (10, 6, 9), (0, 6, 9)]
    north = fall_of(Roof.PENT, [to_the_north])
    south = fall_of(Roof.PENT, [to_the_south])
    assert north is not None and _gap(north, 0.0) < 0.01
    assert south is not None and _gap(south, 180.0) < 0.01


def test_a_pent_whose_faces_fall_both_ways_is_not_placed() -> None:
    assert fall_of(Roof.PENT, [SOUTH_FACE, NORTH_FACE]) is None


def test_a_highest_edge_the_faces_contradict_is_not_trusted() -> None:
    """A small cross-gable standing above the main ridge: its ridge is the
    highest edge and runs north-south, while nearly all of the roof falls north
    and south. Two readings ten degrees or more apart mean neither is used."""
    cross = [
        [(5, 1, 8.8), (6, 1, 9.6), (6, 3, 9.6), (5, 3, 8.8)],
        [(6, 1, 9.6), (7, 1, 8.8), (7, 3, 8.8), (6, 3, 9.6)],
    ]
    assert fall_of(Roof.GABLE, [SOUTH_FACE, NORTH_FACE, *cross]) is None


@pytest.mark.parametrize("roof", [Roof.FLAT, Roof.MIX, Roof.OTHER, Roof.UNKNOWN])
def test_a_roof_without_one_fall_is_given_none(roof: Roof) -> None:
    assert fall_of(roof, [SOUTH_FACE, NORTH_FACE]) is None
