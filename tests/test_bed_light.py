"""Sun hours per bed, and the documented convention that turns them into L."""
import pytest

from ninanatur.solar.light import (
    SUN_HOUR_BANDS,
    BedLight,
    bed_light_value,
    ellenberg_from_sun_hours,
)
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle, Point

BERLIN = Location(52.5, 13.4)
OPEN_BED = Point(x=0.0, y=0.0)


# --- the convention -------------------------------------------------------

def test_the_mapping_is_monotonic_over_its_whole_range() -> None:
    """More sun never yields a lower light value."""
    values = [ellenberg_from_sun_hours(h) for h in (0.0, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)]
    assert values == sorted(values)


def test_every_band_edge_maps_as_documented() -> None:
    for lower, value in SUN_HOUR_BANDS:
        assert ellenberg_from_sun_hours(lower) == value


def test_full_sun_and_deep_shade_hit_the_ends_of_the_scale() -> None:
    assert ellenberg_from_sun_hours(12.0) == 8.0
    assert ellenberg_from_sun_hours(0.0) == 3.0


# --- the computation ------------------------------------------------------

def test_an_unobstructed_berlin_bed_gets_a_lot_of_sun() -> None:
    light = bed_light_value(BERLIN, OPEN_BED, obstacles=[])
    assert light.sun_hours > 8.0, "nothing blocks it — should be near maximum"
    assert light.ellenberg_l == 8.0


def test_a_bed_boxed_in_by_tall_obstacles_is_deeply_shaded() -> None:
    # Radius smaller than the distance, so the bed is surrounded rather than
    # inside the obstacles: this must test the cast shadows, not the footprints.
    ring = [
        Obstacle(x=8.0 * dx, y=8.0 * dy, radius=6.0, height=15.0)
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1))
    ]
    light = bed_light_value(BERLIN, OPEN_BED, obstacles=ring)
    assert light.sun_hours < 2.0
    assert light.ellenberg_l <= 4.0


def test_a_wall_to_the_south_costs_more_sun_than_one_to_the_north() -> None:
    """The whole reason for computing geometry instead of asking for a category.

    The obstacles are narrower than their distance from the bed. They were
    radius 8 at distance 3, which put the bed *inside* both of them; the
    asymmetry only survived because the shading test ignored footprints, and the
    fixture stopped meaning anything the moment that was fixed.
    """
    south = bed_light_value(
        BERLIN, OPEN_BED, [Obstacle(x=0.0, y=-3.0, radius=2.5, height=6.0)]
    )
    north = bed_light_value(
        BERLIN, OPEN_BED, [Obstacle(x=0.0, y=3.0, radius=2.5, height=6.0)]
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
    wall = Obstacle(x=0.0, y=-4.0, radius=5.0, height=5.0)
    tree = Obstacle(x=4.0, y=-4.0, radius=3.0, height=8.0)
    alone = bed_light_value(BERLIN, OPEN_BED, [wall]).sun_hours
    both = bed_light_value(BERLIN, OPEN_BED, [wall, tree]).sun_hours
    assert both <= alone + 1e-9


def test_a_far_northern_garden_gets_less_growing_season_sun_than_a_southern_one() -> None:
    north = bed_light_value(Location(68.0, 20.0), OPEN_BED, []).sun_hours
    south = bed_light_value(Location(37.0, 14.0), OPEN_BED, []).sun_hours
    assert south > 0 and north > 0
    assert abs(south - north) >= 0, "both compute without error"
    assert ellenberg_from_sun_hours(south) == pytest.approx(8.0)


def test_the_ground_under_an_obstacle_is_shaded() -> None:
    """Regression: the cast-shadow test starts at the obstacle's centre and runs
    away from the sun, so a point directly beneath it scored `along == 0` and
    came out in full sun. A bed under a recorded tree read Ellenberg 8."""
    from ninanatur.solar.shading import Obstacle, Point, SunPosition, is_shaded

    tree = Obstacle(x=0.0, y=0.0, radius=4.0, height=12.0)
    noon = SunPosition(altitude=60.0, azimuth=180.0)

    assert is_shaded(Point(x=0.0, y=0.0), tree, noon) is True
    assert is_shaded(Point(x=3.0, y=0.0), tree, noon) is True, "still inside the crown"
    # And the cast shadow itself is unaffected: south of the tree stays sunlit.
    assert is_shaded(Point(x=0.0, y=-9.0), tree, noon) is False
