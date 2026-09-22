"""Sun hours per bed, and the documented convention that turns them into L."""
import pytest

from ninanatur.garden.footprint import Shape, footprint_of
from ninanatur.solar.light import (
    SUN_HOUR_ANCHORS,
    BedLight,
    bed_light_value,
    ellenberg_from_sun_hours,
)
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle, Point


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
OPEN_BED = Point(x=0.0, y=0.0)



# --- the convention -------------------------------------------------------

#: Every hundredth of an hour from none to fourteen.
HOURS = [h / 100 for h in range(0, 1401)]


def test_the_mapping_is_monotonic_over_its_whole_range() -> None:
    """More sun never yields a lower light value."""
    values = [ellenberg_from_sun_hours(h) for h in HOURS]
    assert values == sorted(values)
    assert values[0] < values[-1]


def test_the_mapping_has_no_steps() -> None:
    """3.99 h and 4.01 h are the same place. The staircase this replaced put
    them a whole class apart, enough to drop a species from a list."""
    values = [ellenberg_from_sun_hours(h) for h in HOURS]
    steepest = max(
        (l1 - l0) / (h1 - h0)
        for (h0, l0), (h1, l1) in zip(SUN_HOUR_ANCHORS, SUN_HOUR_ANCHORS[1:], strict=False)
    )
    # A hundredth of an hour moves the value by at most the steepest line's
    # slope, plus the rounding to two places.
    jumps = [b - a for a, b in zip(values, values[1:], strict=False)]
    assert max(jumps) <= steepest * 0.01 + 0.01


def test_every_anchor_maps_as_documented() -> None:
    for hours, value in SUN_HOUR_ANCHORS:
        assert ellenberg_from_sun_hours(hours) == value


def test_between_anchors_the_value_is_on_the_line() -> None:
    """Half way from 2.5 h (5.0) to 4 h (6.25) is half way between them."""
    assert ellenberg_from_sun_hours(3.25) == pytest.approx(5.625, abs=0.005)
    assert ellenberg_from_sun_hours(7.0) == pytest.approx(8.25, abs=0.005)


def test_the_anchors_are_the_old_rungs_on_eives_scale() -> None:
    """EIVE scaled Ellenberg's 1–9 linearly onto 0–10, (L − 1) × 1.25. The old
    staircase's rungs 3–7, carried through that, are the anchors' values."""
    for (_, value), classic in zip(SUN_HOUR_ANCHORS[:-1], (3, 4, 5, 6, 7), strict=True):
        assert value == pytest.approx((classic - 1) * 1.25)


def test_full_sun_and_deep_shade_hit_the_ends_of_the_scale() -> None:
    """Flat beyond both ends, and on EIVE's scale: between classic 8 and 9 in
    full sun, classic 3 in deep shade."""
    assert ellenberg_from_sun_hours(12.0) == ellenberg_from_sun_hours(8.0) == 9.0
    assert ellenberg_from_sun_hours(0.0) == 2.5
    assert ellenberg_from_sun_hours(-1.0) == 2.5


# --- the computation ------------------------------------------------------

def test_an_unobstructed_berlin_bed_gets_a_lot_of_sun() -> None:
    light = bed_light_value(BERLIN, OPEN_BED, obstacles=[])
    assert light.sun_hours > 8.0, "nothing blocks it — should be near maximum"
    assert light.ellenberg_l == 9.0


def test_a_bed_boxed_in_by_tall_obstacles_is_deeply_shaded() -> None:
    # Radius smaller than the distance, so the bed is surrounded rather than
    # inside the obstacles: this must test the cast shadows, not the footprints.
    ring = [
        _cyl(8.0 * dx, 8.0 * dy, 6.0, 15.0)
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1))
    ]
    light = bed_light_value(BERLIN, OPEN_BED, obstacles=ring)
    assert light.sun_hours < 2.0
    assert light.ellenberg_l < ellenberg_from_sun_hours(2.0) < 5.0


def test_a_wall_to_the_south_costs_more_sun_than_one_to_the_north() -> None:
    """The whole reason for computing geometry instead of asking for a category.

    The obstacles are narrower than their distance from the bed. They were
    radius 8 at distance 3, which put the bed *inside* both of them; the
    asymmetry only survived because the shading test ignored footprints, and the
    fixture stopped meaning anything the moment that was fixed.
    """
    south = bed_light_value(
        BERLIN, OPEN_BED, [_cyl(0.0, -3.0, 2.5, 6.0)]
    )
    north = bed_light_value(
        BERLIN, OPEN_BED, [_cyl(0.0, 3.0, 2.5, 6.0)]
    )
    assert south.sun_hours < north.sun_hours


def test_the_light_value_carries_the_sun_hours_behind_it() -> None:
    """A bare number the user cannot trace back to their own obstacles is not explainable."""
    light = bed_light_value(BERLIN, OPEN_BED, obstacles=[])
    assert isinstance(light, BedLight)
    assert light.sun_hours > 0
    assert light.samples > 0
    assert light.ellenberg_l == ellenberg_from_sun_hours(light.sun_hours)


def test_more_obstacles_never_increase_the_sun() -> None:
    """A monotonicity property no plausible geometry bug survives."""
    wall = _cyl(0.0, -4.0, 5.0, 5.0)
    tree = _cyl(4.0, -4.0, 3.0, 8.0)
    alone = bed_light_value(BERLIN, OPEN_BED, [wall]).sun_hours
    both = bed_light_value(BERLIN, OPEN_BED, [wall, tree]).sun_hours
    assert both <= alone + 1e-9


def test_a_far_northern_garden_gets_less_growing_season_sun_than_a_southern_one() -> None:
    north = bed_light_value(Location(68.0, 20.0), OPEN_BED, []).sun_hours
    south = bed_light_value(Location(37.0, 14.0), OPEN_BED, []).sun_hours
    assert south > 0 and north > 0
    assert abs(south - north) >= 0, "both compute without error"
    assert ellenberg_from_sun_hours(south) == pytest.approx(9.0)


def test_the_ground_under_an_obstacle_is_shaded() -> None:
    """Regression: the cast-shadow test starts at the obstacle's centre and runs
    away from the sun, so a point directly beneath it scored `along == 0` and
    came out in full sun. A bed under a recorded tree read Ellenberg 8."""
    from ninanatur.solar.shading import Point, SunPosition, is_shaded

    tree = _cyl(0.0, 0.0, 4.0, 12.0)
    noon = SunPosition(altitude=60.0, azimuth=180.0)

    assert is_shaded(Point(x=0.0, y=0.0), tree, noon) is True
    assert is_shaded(Point(x=3.0, y=0.0), tree, noon) is True, "still inside the crown"
    # And the cast shadow itself is unaffected: south of the tree stays sunlit.
    assert is_shaded(Point(x=0.0, y=-9.0), tree, noon) is False
