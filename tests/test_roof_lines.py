"""The lines that draw a roof, from the server's roof model (doc 98).

The plan knows a roof's type, but where its ridge runs is the roof model's
answer (`roofshape.surface_of`, doc 94). A drawing that worked it out again
would be a second answer, so the model says which lines to draw.
"""
from __future__ import annotations

import pytest

from ninanatur.garden.roof_lines import inside_parts, roof_lines
from ninanatur.garden.roofs import Roof
from ninanatur.garden.roofshape import Line

#: 10 m east-west, 6 m north-south, centred on the origin.
BOX = [(-5.0, -3.0), (5.0, -3.0), (5.0, 3.0), (-5.0, 3.0)]
SQUARE = [(-3.0, -3.0), (3.0, -3.0), (3.0, 3.0), (-3.0, 3.0)]


def _rounded(lines: list[Line]) -> set[frozenset[tuple[float, float]]]:
    """Each line as its two ends, in either order, to the millimetre."""
    return {frozenset((round(x, 3) + 0.0, round(y, 3) + 0.0) for x, y in line) for line in lines}


def test_a_gable_is_its_ridge_from_wall_to_wall() -> None:
    lines = roof_lines(BOX, Roof.GABLE, height_m=9.0, eaves_m=6.0)
    assert _rounded(lines) == {frozenset({(-5.0, 0.0), (5.0, 0.0)})}


def test_a_hip_is_its_shortened_ridge_and_four_hips() -> None:
    lines = roof_lines(BOX, Roof.HIP, height_m=9.0, eaves_m=6.0)
    assert _rounded(lines) == {
        frozenset({(-2.0, 0.0), (2.0, 0.0)}),
        frozenset({(-2.0, 0.0), (-5.0, -3.0)}), frozenset({(-2.0, 0.0), (-5.0, 3.0)}),
        frozenset({(2.0, 0.0), (5.0, -3.0)}), frozenset({(2.0, 0.0), (5.0, 3.0)}),
    }


def test_a_square_hip_is_four_hips_to_a_point() -> None:
    lines = roof_lines(SQUARE, Roof.HIP, height_m=9.0, eaves_m=6.0)
    corners = [(-3.0, -3.0), (3.0, -3.0), (3.0, 3.0), (-3.0, 3.0)]
    assert _rounded(lines) == {frozenset({(0.0, 0.0), corner}) for corner in corners}


def test_a_surveyed_pent_is_its_upper_edge() -> None:
    # Falling south: its high edge is the northern one.
    lines = roof_lines(BOX, Roof.PENT, height_m=6.0, eaves_m=3.0, fall_deg=180.0)
    assert _rounded(lines) == {frozenset({(-5.0, 3.0), (5.0, 3.0)})}


def test_a_ridge_follows_the_survey_not_the_long_side() -> None:
    # Falling east and west: the ridge runs north-south across the short way.
    lines = roof_lines(BOX, Roof.GABLE, height_m=9.0, eaves_m=6.0, fall_deg=90.0)
    assert _rounded(lines) == {frozenset({(0.0, -3.0), (0.0, 3.0)})}


def test_what_the_model_draws_as_a_plane_has_no_lines() -> None:
    assert roof_lines(BOX, Roof.FLAT, height_m=9.0) == []
    assert roof_lines(BOX, Roof.UNKNOWN, height_m=9.0) == []
    assert roof_lines(BOX, Roof.PENT, height_m=9.0) == []  # nobody surveyed its fall
    assert roof_lines(BOX, Roof.GABLE, height_m=None) == []  # nobody said how high
    # A pitch under five degrees is flat to the model, and so to the drawing.
    assert roof_lines(BOX, Roof.GABLE, height_m=9.0, eaves_m=8.9) == []


# --- a house that is not a rectangle (the owner, 2026-09-21) -------------------
#
# "Bei schrägen, nicht rechteckigen Häusern zeichnet das Dach manchmal über das
# Haus hinaus. Vor allem beim Walmdach." The model's rectangle is wider than such
# a house, and its corners lie outside the walls.

#: A corner house: 10 m along the street, 6 m along its oblique end walls.
TRAPEZOID = [(-5.0, -3.0), (5.0, -3.0), (3.0, 3.0), (-3.0, 3.0)]
#: An L: 10 × 6 with the north-east 4 × 3 cut out.
ELL = [(-5.0, -3.0), (5.0, -3.0), (5.0, 0.0), (1.0, 0.0), (1.0, 3.0), (-5.0, 3.0)]
#: A parallelogram, leaning east.
LEANING = [(0.0, 0.0), (10.0, 0.0), (13.0, 6.0), (3.0, 6.0)]


def _inside_or_on(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    for index, (ax, ay) in enumerate(polygon):
        bx, by = polygon[(index + 1) % len(polygon)]
        cross = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        within = (min(ax, bx) - 1e-6 <= x <= max(ax, bx) + 1e-6
                  and min(ay, by) - 1e-6 <= y <= max(ay, by) + 1e-6)
        if abs(cross) < 1e-6 and within:
            return True
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def _every_point_inside(lines: list[Line], polygon: list[tuple[float, float]]) -> bool:
    return all(
        _inside_or_on((a[0] + (b[0] - a[0]) * k / 20, a[1] + (b[1] - a[1]) * k / 20), polygon)
        for a, b in lines for k in range(21)
    )


@pytest.mark.parametrize("footprint", [TRAPEZOID, ELL, LEANING], ids=["trapezoid", "L", "leaning"])
@pytest.mark.parametrize("roof", [Roof.HIP, Roof.GABLE])
def test_no_roof_line_leaves_the_house(footprint: list[tuple[float, float]], roof: Roof) -> None:
    lines = roof_lines(footprint, roof, height_m=9.0, eaves_m=6.0)
    assert lines, "the roof is still drawn"
    assert _every_point_inside(lines, footprint)


def test_a_hip_runs_to_the_houses_own_corners() -> None:
    """Not to the rectangle's, two metres out in the garden past each oblique
    end wall."""
    lines = roof_lines(TRAPEZOID, Roof.HIP, height_m=9.0, eaves_m=6.0)
    ends = {(round(x, 3) + 0.0, round(y, 3) + 0.0) for line in lines for x, y in line}
    assert {(-5.0, -3.0), (5.0, -3.0), (3.0, 3.0), (-3.0, 3.0)} <= ends
    assert (5.0, 3.0) not in ends and (-5.0, 3.0) not in ends


def test_a_ridge_along_an_ls_notch_stays_whole() -> None:
    """Its east half runs along the notch's wall, which is still the house."""
    lines = roof_lines(ELL, Roof.GABLE, height_m=9.0, eaves_m=6.0)
    assert _rounded(lines) == {frozenset({(-5.0, 0.0), (5.0, 0.0)})}, "along the notch's wall"


def test_a_line_across_a_notch_comes_back_in_two_pieces() -> None:
    notched = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (6.0, 4.0), (6.0, 2.0),
               (4.0, 2.0), (4.0, 4.0), (0.0, 4.0)]
    pieces = inside_parts(((-1.0, 3.0), (11.0, 3.0)), notched)
    assert _rounded(pieces) == {frozenset({(0.0, 3.0), (4.0, 3.0)}),
                                frozenset({(6.0, 3.0), (10.0, 3.0)})}


def test_a_line_on_a_wall_is_kept() -> None:
    """A pent's upper edge lies on its wall, where it cannot be seen."""
    assert _rounded(inside_parts(((-5.0, 3.0), (5.0, 3.0)), BOX)) == {
        frozenset({(-5.0, 3.0), (5.0, 3.0)})}


def test_a_line_wholly_outside_is_not_drawn() -> None:
    assert inside_parts(((6.0, 0.0), (9.0, 0.0)), BOX) == []
