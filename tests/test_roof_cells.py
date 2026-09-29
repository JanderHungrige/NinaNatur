"""Where a roof's own cells stand — doc 120, rule 1, where it is applied.

A cell on a house is answered on its roof, at the roof's height there: the
lower envelope of the planes the house's shadow is cast from. Rule 1 was
tested on the planes and on the shadow, but not where the cells take their
height (`lightcells.surface_at`): standing every roof cell at the ridge passed
the whole suite (review of feature 5, 2026-09-28). On a lone house it changes
no hour — its own roof is left out of its shadow — and under a neighbour's
shadow it changes every one.
"""
from __future__ import annotations

import pytest

from ninanatur.garden.casting import casting
from ninanatur.garden.lightcells import roofs_of, surface_at
from ninanatur.garden.models import Element, Garden
from ninanatur.geo.terrain import TerrainWindow


def _rising() -> TerrainWindow:
    """Ground rising 5 % northwards, 100 m up."""
    return TerrainWindow(min_x=-50.0, min_y=-50.0, cell_m=1.0, cols=100, rows=100,
                         heights=[100.0 + (row - 50) * 0.05 for row in range(100)
                                  for _ in range(100)],
                         source="Test", licence="-", attribution="-", vertical_step_m=0.01)


def _house(roof: str, fall: float | None) -> Element:
    """12 m east–west, 8 m deep, its ridge 9 m and its eaves 5 m, off the origin."""
    return Element(element_id=7, kind="house", shape="polygon", x=3.0, y=-2.0,
                   points=[[-6.0, -4.0], [6.0, -4.0], [6.0, 4.0], [-6.0, 4.0]], height=9.0,
                   roof=roof, eaves_m=5.0, roof_fall_deg=fall)


@pytest.mark.parametrize("ground", [None, _rising()], ids=["level", "rising"])
@pytest.mark.parametrize(("roof", "fall"), [("gable", None), ("hip", None), ("pent", 0.0),
                                            ("pent", 180.0)])
def test_a_roofs_cells_stand_on_the_planes_its_shadow_is_cast_from(
    roof: str, fall: float | None, ground: TerrainWindow | None,
) -> None:
    house = _house(roof, fall)
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="G", latitude=51.25,
                    longitude=7.15, created_at="", updated_at="", elements=[house])
    solid = casting(house).roof
    assert solid is not None, "a shape the model places casts its planes"
    roofs = roofs_of(garden, ground)
    base = roofs[0].base
    heights = []
    for x in (-2.5, 0.0, 3.0, 5.5, 8.5):
        for y in (-5.5, -3.0, -2.0, 0.5, 1.5):
            cell = surface_at((x, y), ground, None, 0.0, roofs)
            assert cell.on_a_roof and cell.owner == 7
            assert cell.z == pytest.approx(base + solid.height_at(x, y), abs=1e-9), (x, y)
            heights.append(cell.z - base)
    assert min(heights) < 6.0 < 8.0 < max(heights), "from near the eaves to near the top"
