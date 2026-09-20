"""The one light a drawing has (doc 99).

A plan in Draft Sketch draws the shadow the sun actually casts at one reference
moment. These are about that moment being the one it claims to be, and about
the offset pointing away from the sun rather than wherever the style felt like.
"""
from __future__ import annotations

import math

from ninanatur.garden.objects import ObjectKind
from ninanatur.solar.drawing import (
    REFERENCE_DAY,
    REFERENCE_MONTH,
    drawing_moment,
    drawing_shadow,
    drawing_sun,
)
from ninanatur.solar.position import Location

#: Wuppertal, where the garden that started this lives.
HOME = Location(latitude=51.2564, longitude=7.1501)


def test_the_moment_is_mid_afternoon_in_june_wherever_the_garden_is() -> None:
    """Three hours after solar noon, which is a different instant per longitude
    and the same sun everywhere."""
    for longitude in (-9.0, 0.0, 7.15, 24.0):
        moment = drawing_moment(longitude)
        assert (moment.month, moment.day) == (REFERENCE_MONTH, REFERENCE_DAY)
        # Solar noon is 12:00 minus the longitude's four minutes a degree.
        solar_hours = moment.hour + moment.minute / 60 + longitude / 15
        assert math.isclose(solar_hours, 15.0, abs_tol=1 / 60)


def test_the_sun_is_high_and_in_the_west() -> None:
    sun = drawing_sun(HOME)
    assert 40 < sun.altitude < 60, "June afternoon, not a winter dusk"
    # Clockwise from north: south is 180, west 270.
    assert 230 < sun.azimuth < 280


def test_a_shadow_points_away_from_the_sun_and_is_shorter_than_the_thing() -> None:
    sun = drawing_sun(HOME)
    offset = drawing_shadow(10.0, sun)
    assert offset is not None
    dx, dy = offset
    # The sun is in the west-south-west, so the shadow falls east-north-east.
    assert dx > 0 and dy > 0
    length = math.hypot(dx, dy)
    assert 0.5 < length / 10.0 < 1.2, "short, as a June afternoon makes it"
    # And it is the direction opposite the sun, to the degree.
    bearing = (math.degrees(math.atan2(dx, dy)) + 360) % 360
    assert math.isclose(bearing, (sun.azimuth + 180) % 360, abs_tol=0.5)


def test_twice_as_tall_casts_twice_as_far() -> None:
    sun = drawing_sun(HOME)
    short, tall = drawing_shadow(2.0, sun), drawing_shadow(4.0, sun)
    assert short is not None and tall is not None
    assert math.isclose(math.hypot(*tall), 2 * math.hypot(*short), rel_tol=1e-9)


def test_nothing_to_cast_means_no_shadow_at_all() -> None:
    """Never a default direction: the drawing leaves the mark out (doc 99)."""
    sun = drawing_sun(HOME)
    assert drawing_shadow(0.0, sun) is None
    assert drawing_shadow(None, sun) is None


def test_the_sun_can_be_too_low_to_draw() -> None:
    """Above the arctic circle in June it never sets; below it in the far south
    the reference moment can still put the sun on the floor. Either way the
    shadow is left out rather than stretched to the horizon."""
    far_south = Location(latitude=-65.0, longitude=0.0)
    assert drawing_shadow(10.0, drawing_sun(far_south)) is None


def test_only_the_kinds_that_cast_one_get_one() -> None:
    """The model already says which kinds stand up (doc 08); the drawing does
    not get a second opinion."""
    from ninanatur.garden.objects import casts_shadow

    assert casts_shadow(ObjectKind.HOUSE)
    assert not casts_shadow(ObjectKind.LAWN)
