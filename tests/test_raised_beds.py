"""A raised bed stands above the low things around it.

The shading model measures a shadow against a point on the ground, so it used to
shade a raised bed exactly as hard as a border — wrong in the direction that
matters, because it makes the sunniest beds in a small garden look shaded.
"""
import pytest

from ninanatur.garden.footprint import Shape, footprint_of
from ninanatur.solar.light import bed_light_value
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle, Point, SunPosition, is_shaded


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

BERLIN = Location(52.5, 13.4)
BED = Point(x=0.0, y=0.0)
NOON = SunPosition(altitude=40.0, azimuth=180.0)



def test_a_low_fence_does_not_shade_a_bed_that_stands_above_it() -> None:
    # 1.2 m at 40° reaches 1.43 m, so the bed has to be closer than that.
    fence = _cyl(0.0, -1.0, 0.3, 1.2)
    assert is_shaded(BED, fence, NOON, height_above_ground=0.0) is True
    assert is_shaded(BED, fence, NOON, height_above_ground=1.3) is False


def test_a_tree_still_shades_a_raised_bed() -> None:
    # Raising a bed 80 cm does not put it above an 8 m tree.
    tree = _cyl(0.0, -4.0, 2.0, 8.0)
    assert is_shaded(BED, tree, NOON, height_above_ground=0.8) is True


def test_the_shadow_shortens_rather_than_vanishing() -> None:
    """An obstacle taller than the bed still shades — just less far."""
    # 4 m reaches 4.77 m; raised 2 m it reaches 2.38 m and falls short.
    wall = _cyl(0.0, -3.0, 0.3, 4.0)
    ground = is_shaded(Point(x=0.0, y=0.0), wall, NOON, height_above_ground=0.0)
    raised = is_shaded(Point(x=0.0, y=0.0), wall, NOON, height_above_ground=2.0)
    assert ground is True
    assert raised is False, "half the wall's height should not reach half as far"


def test_a_bed_on_the_ground_behaves_exactly_as_before() -> None:
    # The migration defaults every existing bed to 0, so no stored light value
    # may change meaning.
    wall = _cyl(0.0, -3.0, 1.0, 5.0)
    assert is_shaded(BED, wall, NOON) is is_shaded(BED, wall, NOON, height_above_ground=0.0)


def test_light_over_the_year_improves_when_a_bed_is_raised() -> None:
    fence = _cyl(0.0, -1.5, 0.3, 1.4)
    on_ground = bed_light_value(BERLIN, BED, [fence], height_above_ground=0.0)
    raised = bed_light_value(BERLIN, BED, [fence], height_above_ground=1.5)
    assert raised.sun_hours > on_ground.sun_hours


def test_raising_a_bed_above_nothing_changes_nothing() -> None:
    open_ground = bed_light_value(BERLIN, BED, [], height_above_ground=0.0)
    raised = bed_light_value(BERLIN, BED, [], height_above_ground=1.0)
    assert raised.sun_hours == pytest.approx(open_ground.sun_hours)
