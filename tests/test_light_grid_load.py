"""What a light grid pays for, counted before it is computed (docs 117, 120, 121).

The estimate chooses the cell, and what it multiplies is counted here
(`lightgrid_load`): how far the grid's cells stand apart in height, which
stretches every crown's box, and which neighbours off the grid stand near
enough to throw their shadows in at most moments. Each was keyed on the wrong
thing once — "terrain exists", "the roof is pitched", a neighbour's ground
under its own corners — and level surveyed ground paid for a slope while a
15 m house of no known shape paid nothing (review of 45eb56a).
"""
from __future__ import annotations

from ninanatur.garden.casting import casting
from ninanatur.garden.ground import standing_on
from ninanatur.garden.lightcells import roofs_of
from ninanatur.garden.lightgrid_cost import estimate_ms
from ninanatur.garden.lightgrid_load import load_of
from ninanatur.garden.models import Element, Garden
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.raster import parts_of

#: The grid's box: a 40 m plot and its 5 m margin.
BOX = (-25.0, -25.0, 25.0, 25.0)


def _window(rise_per_m: float, wobble: float = 0.0) -> TerrainWindow:
    """Ground 100 m up, rising northwards — and wobbling a little, row by row."""
    return TerrainWindow(min_x=-100.0, min_y=-100.0, cell_m=1.0, cols=200, rows=200,
                         heights=[100.0 + (row - 100) * rise_per_m + wobble * (row % 2)
                                  for row in range(200) for _ in range(200)],
                         source="Test", licence="-", attribution="-", vertical_step_m=0.01)


def _house(number: int, x: float, y: float, height: float, roof: str,
           measured: bool = False) -> Element:
    return Element(element_id=number, kind="house", shape="polygon", x=x, y=y,
                   points=[[-5.0, -4.0], [5.0, -4.0], [5.0, 4.0], [-5.0, 4.0]], height=height,
                   roof=roof, height_source="osm" if measured else "user",
                   roof_source="osm" if measured else "user")


def _load(elements: list[Element], ground: TerrainWindow | None = None) -> tuple[float, int]:
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="G", latitude=51.25,
                    longitude=7.15, created_at="", updated_at="", elements=elements)
    parts = parts_of(standing_on([casting(e) for e in elements], ground))
    load = load_of(parts, BOX, ground, roofs_of(garden, ground))
    return load.relief_m, load.reaching


def test_the_height_the_cells_span_is_the_ground_s_and_every_roof_s_on_the_grid() -> None:
    assert _load([], _window(0.0, wobble=0.1))[0] < 0.2, "level, however surveyed"
    assert _load([], _window(0.05))[0] > 2.4, "rising 5 % across 50 m"
    for roof in ("flat", "unknown", "gable"):
        assert _load([_house(1, 0.0, 0.0, 9.0, roof)])[0] == 9.0, roof
    # A roof off the grid raises no cell of it.
    assert _load([_house(1, 0.0, 60.0, 9.0, "flat", measured=True)])[0] == 0.0


def test_crowns_on_the_grid_cost_more_the_further_its_cells_stand_apart() -> None:
    flat = estimate_ms(40_000, 12, 12, near_crowns=12)
    assert estimate_ms(40_000, 12, 12, near_crowns=12, relief_m=9.0) > flat
    assert estimate_ms(40_000, 12, 12, near_crowns=12, relief_m=0.1) < flat * 1.05


def test_a_neighbour_reaches_in_by_its_height_above_the_grid_s_lowest_cell() -> None:
    """On ground 100 m up a neighbour's top is absolute: measured from zero it
    reached in from anywhere. From the grid's lowest cell, the house 5 m past
    the edge reaches in and the one 30 m out does not."""
    near = _house(2, 0.0, 34.0, 9.0, "flat", measured=True)
    far = _house(3, 0.0, 59.0, 9.0, "flat", measured=True)
    assert _load([near, far], _window(0.0))[1] == 1
    assert _load([near, far])[1] == 1
