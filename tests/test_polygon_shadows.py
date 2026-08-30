"""A house rarely casts a round shadow.

The shadow of a footprint is that footprint swept along the anti-solar direction
by `height / tan(altitude)` — for a convex outline, the hull of the original and
the swept copy. The circle it replaces was not a simplification of the geometry
so much as a claim about it.
"""
import math

import pytest

from ninanatur.garden.footprint import Shape, footprint_of
from ninanatur.solar.shading import Obstacle, Point, SunPosition, is_shaded, shadow_polygon

# Sun in the south at 30°, so shadows run north.
SOUTH_30 = SunPosition(altitude=30.0, azimuth=180.0)


def _house(width: float = 10.0, depth: float = 4.0, rotation: float = 0.0) -> Obstacle:
    return Obstacle(
        footprint=footprint_of(shape=Shape.RECT, x=0.0, y=0.0, width=width,
                               depth=depth, rotation=rotation, points=None),
        height=6.0,
    )


def test_a_long_house_casts_a_long_shadow_not_a_round_one() -> None:
    """The sentence this whole feature exists for."""
    shadow = shadow_polygon(_house(width=10.0, depth=4.0), SOUTH_30)
    xs = [p[0] for p in shadow]
    ys = [p[1] for p in shadow]
    assert max(xs) - min(xs) == pytest.approx(10.0), "as wide as the house"
    # 6 m at 30° reaches 10.39 m, plus the house's own 4 m depth.
    assert max(ys) - min(ys) == pytest.approx(4.0 + 6 / math.tan(math.radians(30)), rel=0.01)


def test_the_shadow_runs_away_from_the_sun() -> None:
    # Sun in the south, shadow to the north. Getting this backwards mirrors
    # every garden.
    shadow = shadow_polygon(_house(), SOUTH_30)
    assert max(p[1] for p in shadow) > 2.0


def test_a_shadow_from_the_east_runs_west() -> None:
    east = SunPosition(altitude=30.0, azimuth=90.0)
    shadow = shadow_polygon(_house(width=4.0, depth=4.0), east)
    assert min(p[0] for p in shadow) < -2.0


def test_rotating_the_house_rotates_its_shadow() -> None:
    straight = shadow_polygon(_house(width=10.0, depth=2.0), SOUTH_30)
    turned = shadow_polygon(_house(width=10.0, depth=2.0, rotation=90.0), SOUTH_30)
    width = lambda poly: max(p[0] for p in poly) - min(p[0] for p in poly)  # noqa: E731
    assert width(straight) > width(turned)


def test_a_point_in_the_shadow_is_shaded() -> None:
    house = _house()
    assert is_shaded(Point(x=0.0, y=6.0), house, SOUTH_30) is True


def test_a_point_beside_the_shadow_is_not() -> None:
    # The corner of a house is a real edge, and the old circle rounded it off.
    house = _house(width=4.0, depth=4.0)
    assert is_shaded(Point(x=6.0, y=6.0), house, SOUTH_30) is False


def test_a_point_beyond_the_shadow_s_reach_is_not() -> None:
    house = _house()
    assert is_shaded(Point(x=0.0, y=40.0), house, SOUTH_30) is False


def test_the_ground_under_the_house_is_shaded() -> None:
    # Regression from Wave 7: the cast-shadow test starts at the footprint and
    # runs away from the sun, so the ground beneath used to score as full sun.
    assert is_shaded(Point(x=0.0, y=0.0), _house(), SOUTH_30) is True


def test_a_raised_bed_stands_above_a_low_wall() -> None:
    wall = Obstacle(
        footprint=footprint_of(shape=Shape.RECT, x=0.0, y=-1.0, width=6.0,
                               depth=0.3, rotation=0.0, points=None),
        height=1.2,
    )
    here = Point(x=0.0, y=0.0)
    assert is_shaded(here, wall, SOUTH_30, height_above_ground=0.0) is True
    assert is_shaded(here, wall, SOUTH_30, height_above_ground=1.3) is False


def test_no_usable_sun_counts_as_shaded() -> None:
    night = SunPosition(altitude=2.0, azimuth=180.0)
    assert is_shaded(Point(x=0.0, y=5.0), _house(), night) is True


def test_a_circle_still_behaves_like_a_circle() -> None:
    """A crown is the one thing a circle actually fits, and it must not have got
    worse in the move to polygons."""
    tree = Obstacle(
        footprint=footprint_of(shape=Shape.CIRCLE, x=0.0, y=-4.0, width=6.0,
                               depth=None, rotation=0.0, points=None),
        height=8.0,
    )
    assert is_shaded(Point(x=0.0, y=2.0), tree, SOUTH_30) is True
    assert is_shaded(Point(x=12.0, y=2.0), tree, SOUTH_30) is False


def test_the_two_occlusion_models_answer_the_same_question() -> None:
    """The data-flow analysis found occlusion computed twice, agreeing only
    because both assumed a cylinder. They share one implementation now, and this
    is the test that says so.
    """
    from ninanatur.garden.sightlines import Blocker, Target, Viewpoint, visibility

    house = _house(width=8.0, depth=3.0)
    # A viewer standing where the sun is, looking at a point behind the house.
    eye = Viewpoint(x=0.0, y=-20.0, eye_height_m=6.0)
    behind = Target(x=0.0, y=6.0, base_m=0.0, height_m=0.2)
    beside = Target(x=14.0, y=6.0, base_m=0.0, height_m=0.2)
    blocker = Blocker(id=1, footprint=house.footprint, height_m=house.height)

    assert visibility(eye, behind, [blocker]).visible is False
    assert visibility(eye, beside, [blocker]).visible is True
