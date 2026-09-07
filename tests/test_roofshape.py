"""A roof as a surface the sun can be asked about.

`test_roofs.py` covers what a roof does to the shadow a building throws. This
covers the other half: what the sun does to the roof itself, which needs the
pitches to face somewhere rather than to average into one height.
"""
from __future__ import annotations

import math

import pytest

from ninanatur.garden.roofs import Roof
from ninanatur.garden.roofshape import RoofSurface, surface_of

#: 12 m east-west by 8 m north-south, centred on the origin. Its long axis runs
#: east-west, so a ridge along it puts one pitch to the north and one to the
#: south — the case the whole feature exists for.
HOUSE = [(-6.0, -4.0), (6.0, -4.0), (6.0, 4.0), (-6.0, 4.0)]


def _gable() -> RoofSurface:
    surface = surface_of(HOUSE, Roof.GABLE, height_m=9.0, eaves_m=6.0)
    assert surface is not None
    return surface


# --- where the ridge runs ---------------------------------------------------

def test_the_ridge_runs_along_the_long_axis() -> None:
    """Assumed, because nothing in the data says. It is what German houses
    overwhelmingly do and what anyone drawing a plan would expect."""
    (x0, y0), (x1, y1) = _gable().ridge
    assert abs(y0) < 1e-9 and abs(y1) < 1e-9, "the ridge sits on the east-west centre line"
    assert {round(x0), round(x1)} == {-6, 6}


def test_a_hip_stops_its_ridge_short_so_the_ends_slope_too() -> None:
    hip = surface_of(HOUSE, Roof.HIP, height_m=9.0, eaves_m=6.0)
    assert hip is not None
    (x0, _y0), (x1, _y1) = hip.ridge
    # One span (4 m) off each end of a 12 m building.
    assert {round(x0), round(x1)} == {-2, 2}
    # And the end of the building is genuinely lower than the ridge.
    assert hip.height_at(5.5, 0.0) < hip.ridge_m


def test_a_gables_ends_are_walls_rather_than_pitches() -> None:
    """The one place a gable and a hip disagree, and the reason both exist."""
    gable, hip = _gable(), surface_of(HOUSE, Roof.HIP, 9.0, 6.0)
    assert hip is not None
    assert gable.height_at(5.5, 0.0) == pytest.approx(9.0)
    assert hip.height_at(5.5, 0.0) < 9.0


# --- what the surface is at a point -----------------------------------------

def test_the_ridge_is_the_recorded_height_and_the_eaves_the_eaves() -> None:
    gable = _gable()
    assert gable.height_at(0.0, 0.0) == pytest.approx(9.0)
    assert gable.height_at(0.0, 4.0) == pytest.approx(6.0)
    assert gable.height_at(0.0, -4.0) == pytest.approx(6.0)


def test_halfway_down_a_pitch_is_halfway_up_the_rise() -> None:
    assert _gable().height_at(0.0, 2.0) == pytest.approx(7.5)


def test_the_pitch_is_the_rise_over_the_span() -> None:
    # 3 m of rise over a 4 m span.
    assert _gable().pitch_deg == pytest.approx(math.degrees(math.atan(3 / 4)), abs=0.01)


# --- which way each pitch faces ---------------------------------------------

def test_the_north_pitch_climbs_south_and_the_south_pitch_climbs_north() -> None:
    """The whole point. Aspect is uphill, and uphill on a roof is towards the
    ridge — so a point on the north pitch has its own roof standing between it
    and the southern sky, which is exactly why it is the darker side."""
    gable = _gable()

    north_slope, north_aspect = gable.slope_aspect_at(0.0, 3.0)
    south_slope, south_aspect = gable.slope_aspect_at(0.0, -3.0)

    assert north_slope == pytest.approx(south_slope)
    assert north_aspect == pytest.approx(180.0, abs=0.5), "climbs south"
    assert south_aspect == pytest.approx(0.0, abs=0.5), "climbs north"


def test_a_rotated_house_rotates_its_pitches_with_it() -> None:
    """Nothing is axis-aligned in a real garden."""
    turned = [
        (x * math.cos(math.radians(30)) - y * math.sin(math.radians(30)),
         x * math.sin(math.radians(30)) + y * math.cos(math.radians(30)))
        for x, y in HOUSE
    ]
    surface = surface_of(turned, Roof.GABLE, 9.0, 6.0)
    assert surface is not None
    # The pitch still faces across the ridge, now turned by the same 30°.
    _slope, aspect = surface.slope_aspect_at(-1.5, 2.6)
    assert aspect == pytest.approx(150.0, abs=3.0)


def test_the_ridge_line_itself_blocks_nothing() -> None:
    """It falls away on both sides. Flat is the honest answer at a single line,
    and it is one cell out of a roof."""
    assert _gable().slope_aspect_at(0.0, 0.0) == (0.0, 0.0)


# --- the shapes this model will not guess at --------------------------------

def test_a_flat_roof_is_one_plane_at_the_recorded_height() -> None:
    flat = surface_of(HOUSE, Roof.FLAT, 9.0, None)
    assert flat is not None
    assert flat.pitched is False
    assert flat.height_at(5.0, 3.0) == pytest.approx(9.0)


@pytest.mark.parametrize("roof", [Roof.PENT, Roof.MIX, Roof.OTHER, Roof.UNKNOWN])
def test_a_shape_whose_fall_is_unknown_is_not_given_one(roof: Roof) -> None:
    """A pent roof has one pitch and nothing says which way it faces; the other
    three are not identified at all. Half a chance of pointing the sunny side
    into the north is worse than declining to say."""
    surface = surface_of(HOUSE, roof, 9.0, 6.0)
    assert surface is not None
    assert surface.pitched is False
    assert surface.slope_aspect_at(0.0, 3.0) == (0.0, 0.0)


def test_a_building_with_no_recorded_height_gets_no_roof() -> None:
    """Skipped by the shading model since Wave 8. Inventing a roof here would
    put a confident number on the map for the building the model knows least."""
    assert surface_of(HOUSE, Roof.GABLE, None, None) is None


def test_a_pitch_too_shallow_to_matter_is_left_flat() -> None:
    """It changes the sun by minutes, and the direction it would be applied in
    is an assumption rather than a measurement."""
    shallow = surface_of(HOUSE, Roof.GABLE, height_m=6.2, eaves_m=6.0)
    assert shallow is not None
    assert shallow.pitched is False
