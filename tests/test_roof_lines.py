"""The lines that draw a roof, from the server's roof model (doc 98).

The plan knows a roof's type, but where its ridge runs is the roof model's
answer (`roofshape.surface_of`, doc 94). A drawing that worked it out again
would be a second answer, so the model says which lines to draw.
"""
from __future__ import annotations

from ninanatur.garden.roofs import Roof
from ninanatur.garden.roofshape import Line, roof_lines

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
