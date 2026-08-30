"""Shadow casting — geometry that must be right in the direction, not just the length."""
import pytest

from ninanatur.garden.footprint import Shape, footprint_of
from ninanatur.solar.position import SunPosition
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle, Point, is_shaded, shadow_length


def _cyl(x: float, y: float, radius: float, height: float) -> Obstacle:
    """A cylinder, built the way everything else builds one since Wave 10.

    These tests were written when an obstacle *was* a radius. The shape they
    describe is still a cylinder; only the way it is stated changed.
    """
    return Obstacle(
        footprint=footprint_of(shape=Shape.CIRCLE, x=x, y=y, width=radius * 2,
                               depth=None, rotation=0.0, points=None),
        height=height,
    )

def test_shadow_is_longer_when_the_sun_is_lower() -> None:
    low = shadow_length(height=4.0, altitude=15.0)
    high = shadow_length(height=4.0, altitude=60.0)
    assert low > high > 0


# A 4 m wall a few metres north of the origin.
NORTH_WALL = _cyl(0.0, 5.0, 3.0, 4.0)
ORIGIN = Point(x=0.0, y=0.0)

def test_shadow_length_matches_the_trigonometry() -> None:
    """At 45° the shadow is exactly as long as the obstacle is tall."""
    assert shadow_length(height=4.0, altitude=45.0) == pytest.approx(4.0, abs=0.01)


def test_a_point_north_of_an_obstacle_is_shaded_by_a_southern_sun() -> None:
    """The everyday case: a wall to the south shades the bed behind it."""
    south_wall = _cyl(0.0, -5.0, 3.0, 4.0)
    midday = SunPosition(altitude=30.0, azimuth=180.0)
    assert is_shaded(ORIGIN, south_wall, midday)


def test_the_same_point_is_lit_when_the_sun_comes_from_the_other_side() -> None:
    """Direction matters — a length-only check would call this shaded too."""
    south_wall = _cyl(0.0, -5.0, 3.0, 4.0)
    northern_sun = SunPosition(altitude=30.0, azimuth=0.0)
    assert not is_shaded(ORIGIN, south_wall, northern_sun)


def test_a_point_beyond_the_shadow_tip_is_lit() -> None:
    far = Point(x=0.0, y=-40.0)
    steep_sun = SunPosition(altitude=60.0, azimuth=0.0)  # short shadow to the south
    assert not is_shaded(far, NORTH_WALL, steep_sun)


def test_a_point_off_to_the_side_of_the_shadow_is_lit() -> None:
    """Perpendicular distance is what the obstacle's width limits."""
    aside = Point(x=20.0, y=0.0)
    sun = SunPosition(altitude=30.0, azimuth=0.0)
    assert not is_shaded(aside, NORTH_WALL, sun)


def test_a_sun_below_the_minimum_altitude_casts_no_usable_light(
) -> None:
    """Without a floor, 1/tan(altitude) produces shadows kilometres long."""
    grazing = SunPosition(altitude=MIN_ALTITUDE - 0.1, azimuth=180.0)
    south_wall = _cyl(0.0, -5.0, 3.0, 4.0)
    assert is_shaded(ORIGIN, south_wall, grazing), "below the floor counts as no sun"


def test_the_sun_below_the_horizon_means_shaded_not_an_error() -> None:
    night = SunPosition(altitude=-10.0, azimuth=180.0)
    assert is_shaded(ORIGIN, NORTH_WALL, night)


def test_a_taller_obstacle_shades_further() -> None:
    sun = SunPosition(altitude=45.0, azimuth=180.0)
    point = Point(x=0.0, y=0.0)
    # Centred at -9 with a 3 m radius, so its near edge is 6 m away. Since
    # Wave 10 a shadow starts at the wall rather than at the wall's centre,
    # which is what the old radius quietly assumed.
    short = _cyl(0.0, -9.0, 3.0, 4.0)
    tall = _cyl(0.0, -9.0, 3.0, 10.0)
    assert not is_shaded(point, short, sun), "4 m casts a 4 m shadow — 6 m away is lit"
    assert is_shaded(point, tall, sun), "10 m casts a 10 m shadow — 6 m away is shaded"
