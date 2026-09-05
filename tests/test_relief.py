"""Relief shading: a grid of metres turned into something an eye can read."""
from __future__ import annotations

import pytest

from ninanatur.garden.relief import EXAGGERATION, LIGHT_AZIMUTH_DEG, relief_of
from ninanatur.geo.terrain import TerrainWindow


def _window(heights: list[float], size: int) -> TerrainWindow:
    return TerrainWindow(
        min_x=0.0, min_y=0.0, cell_m=1.0, cols=size, rows=size, heights=heights,
        source="Test", licence="—", attribution="—", vertical_step_m=0.01,
    )


def _plane(rise_north: float = 0.0, rise_east: float = 0.0, size: int = 20) -> TerrainWindow:
    return _window(
        [
            100.0 + row * rise_north + col * rise_east
            for row in range(size)
            for col in range(size)
        ],
        size,
    )


def test_flat_ground_is_uniformly_lit() -> None:
    lit = relief_of(_plane())
    assert max(lit) - min(lit) == pytest.approx(0.0, abs=0.001)


def test_a_slope_facing_the_lamp_is_brighter_than_one_facing_away() -> None:
    """The lamp stands in the north-west, which is the cartographic convention.
    Lighting relief from the south-east makes valleys read as ridges."""
    towards = relief_of(_plane(rise_north=0.2))   # climbs north, faces south
    away = relief_of(_plane(rise_north=-0.2))     # climbs south, faces north

    assert LIGHT_AZIMUTH_DEG == 315.0
    assert sum(away) / len(away) > sum(towards) / len(towards)


def test_a_steeper_slope_reads_as_more_relief() -> None:
    gentle = relief_of(_plane(rise_east=0.02))
    steep = relief_of(_plane(rise_east=0.40))

    assert abs(steep[0] - 0.5) > abs(gentle[0] - 0.5)


def test_unsurveyed_ground_reads_as_level_rather_than_as_a_hole() -> None:
    """A gap in a picture is something somebody has to explain, and it must not
    look like anything. The value has to be the one level ground gets — a fixed
    0.5 would draw a dark ring around every gap, which is the one shape a viewer
    would be certain meant something."""
    size = 10
    heights = [100.0] * (size * size)
    heights[55] = float("nan")
    lit = relief_of(_window(heights, size))

    assert all(0.0 <= v <= 1.0 for v in lit)
    flat = relief_of(_window([100.0] * (size * size), size))
    assert lit[55] == pytest.approx(flat[55], abs=0.001), (
        "a gap must light exactly like level ground, or it draws a ring"
    )
    assert lit[45] == pytest.approx(flat[45], abs=0.001), "and so must its neighbours"


def test_every_value_is_something_an_opacity_can_use() -> None:
    lit = relief_of(_plane(rise_north=0.5, rise_east=-0.3))
    assert all(0.0 <= v <= 1.0 for v in lit)
    assert len(lit) == 400


def test_the_exaggeration_is_stated_rather_than_hidden() -> None:
    """A garden's ground falls a couple of metres across a couple of hundred,
    which is invisible at true scale — so the picture is not to scale, and the
    number that makes it so has a name."""
    assert EXAGGERATION > 1.0


# --- what actually gets drawn ----------------------------------------------

def test_the_relief_is_cropped_to_what_the_plan_shows() -> None:
    """The window reaches 100 m out because the shading needs the neighbours.
    The drawing is the garden. Sending the whole window meant 39,999 rectangles
    for a picture of about nine hundred, in a canvas that redraws on every pan."""
    from ninanatur.garden.relief import crop_to

    window = _plane(rise_north=0.1, size=200)
    cropped = crop_to(window, (0.0, 0.0, 20.0, 15.0), margin_m=10.0)

    assert cropped.cols * cropped.rows < window.cols * window.rows / 10
    assert cropped.cell_m == window.cell_m
    assert cropped.attribution == window.attribution


def test_cropping_keeps_the_ground_where_it_was() -> None:
    """A crop that shifted the heights by a cell would put every bank a metre
    from where it is, and look entirely plausible."""
    from ninanatur.garden.relief import crop_to

    window = _plane(rise_north=0.1, size=200)
    cropped = crop_to(window, (50.0, 60.0, 70.0, 75.0), margin_m=5.0)

    for row in range(cropped.rows):
        for col in range(cropped.cols):
            x = cropped.min_x + (col + 0.5) * cropped.cell_m
            y = cropped.min_y + (row + 0.5) * cropped.cell_m
            assert cropped.at(x, y) == pytest.approx(window.at(x, y))


def test_a_garden_larger_than_its_window_keeps_the_whole_window() -> None:
    from ninanatur.garden.relief import crop_to

    window = _plane(size=20)
    assert crop_to(window, (-500.0, -500.0, 500.0, 500.0)).cols == window.cols
