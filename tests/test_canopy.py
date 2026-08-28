"""Room needed and shade cast — both estimated from height, and marked as such."""
import pytest

from ninanatur.garden.canopy import (
    MIN_SHADING_HEIGHT_M,
    canopy_of,
    crown_radius,
    polygon_area,
    shades,
)


def test_a_tree_is_narrower_than_it_is_tall() -> None:
    # A 24 m oak spreads about 8 m from its trunk, not 24.
    assert crown_radius(24.0, "tree") == pytest.approx(8.0)


def test_a_shrub_is_proportionally_broader_than_a_tree() -> None:
    assert crown_radius(4.0, "shrub") > crown_radius(4.0, "tree")


def test_an_unrecorded_growth_form_still_gets_a_size() -> None:
    # Growth form is missing for half the catalogue. Refusing a size there would
    # make the room check depend on a second gap rather than on the height.
    assert crown_radius(3.0, None) > 0


def test_no_height_means_no_size_rather_than_a_default() -> None:
    """Inventing a size for the 56% without a recorded height would put a
    confident number where there is no data."""
    assert canopy_of(None, "tree") is None


def test_a_canopy_says_it_is_an_estimate() -> None:
    # The catalogue holds no crown widths; every number here is derived.
    canopy = canopy_of(6.0, "shrub")
    assert canopy is not None
    assert canopy.estimated is True


def test_area_grows_with_the_square_of_the_radius() -> None:
    small = canopy_of(2.0, "tree")
    large = canopy_of(4.0, "tree")
    assert small is not None and large is not None
    assert large.area_m2 == pytest.approx(small.area_m2 * 4, rel=0.01)


def test_a_perennial_does_not_shade_its_neighbours() -> None:
    # Its shadow falls inside its own footprint at any usable sun altitude.
    assert shades(canopy_of(0.6, "forb")) is False


def test_a_shrub_above_the_threshold_shades() -> None:
    assert shades(canopy_of(MIN_SHADING_HEIGHT_M + 0.1, "shrub")) is True


def test_a_plant_with_no_recorded_height_does_not_shade() -> None:
    assert shades(None) is False


def test_bed_area_from_its_polygon() -> None:
    assert polygon_area([[0, 0], [4, 0], [4, 4], [0, 4]]) == pytest.approx(16.0)


def test_winding_direction_does_not_change_the_area() -> None:
    """The drawing tool will not guarantee which way a polygon is wound."""
    clockwise = [[0, 0], [0, 4], [4, 4], [4, 0]]
    assert polygon_area(clockwise) == pytest.approx(16.0)


def test_a_degenerate_polygon_has_no_area() -> None:
    assert polygon_area([[0, 0], [1, 1]]) == 0.0
