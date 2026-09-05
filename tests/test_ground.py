"""Buildings on ground, and a garden that stands at its own height.

The flat world these tests contrast with is not hypothetical: every shadow in
this project was computed on a plane at zero until Wave 17, and every garden
made before it still is one.
"""
from __future__ import annotations

import pytest

from ninanatur.garden.ground import height_at, lowest_ground, standing_on
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.shading import Obstacle


def _slope(rise_per_m: float = 0.05, size: int = 200) -> TerrainWindow:
    """Ground rising towards the north at a given gradient."""
    heights = [
        100.0 + (row - size / 2) * rise_per_m for row in range(size) for _ in range(size)
    ]
    return TerrainWindow(
        min_x=-size / 2, min_y=-size / 2, cell_m=1.0, cols=size, rows=size,
        heights=heights, source="Test", licence="—", attribution="—",
        vertical_step_m=0.01,
    )


SHED = Obstacle(footprint=[(-2.0, 8.0), (2.0, 8.0), (2.0, 12.0), (-2.0, 12.0)], height=3.0)


def test_a_building_stands_on_the_ground_beneath_it() -> None:
    """Ten metres north on a 5 % slope is half a metre up, so a 3 m shed there
    has a top at 100.5 + 3."""
    placed = standing_on([SHED], _slope())

    assert placed[0].base == pytest.approx(100.5, abs=0.05)
    assert placed[0].top == pytest.approx(103.5, abs=0.05)


def test_without_terrain_nothing_moves() -> None:
    """The flat world, untouched. `base` stays zero and `top` stays the height,
    which is what every garden made before Wave 17 relies on."""
    placed = standing_on([SHED], None)

    assert placed[0].base == 0.0
    assert placed[0].top == 3.0
    assert placed is not None


def test_a_building_keeps_what_it_lets_through() -> None:
    """Standing a tree on a slope must not quietly make it a wall."""
    crown = Obstacle(
        footprint=SHED.footprint, height=6.0, transmission=0.2, bare_transmission=0.75
    )
    placed = standing_on([crown], _slope())

    assert placed[0].transmission == 0.2
    assert placed[0].bare_transmission == 0.75


def test_the_floor_is_the_lowest_ground_the_garden_stands_on() -> None:
    """Every shadow polygon is swept onto it, so it has to be a lower bound —
    a floor above any real cell would clip a shadow that genuinely arrives."""
    ground = _slope()
    floor = lowest_ground(ground, min_x=-10.0, min_y=-10.0, cell=1.0, cols=20, rows=20)

    for row in range(20):
        for col in range(20):
            here = ground.at(-10.0 + col + 0.5, -10.0 + row + 0.5)
            assert here is not None
            assert floor <= here + 1e-9


def test_unsurveyed_ground_falls_back_to_the_floor_not_to_zero() -> None:
    """Zero would put a cell hundreds of metres below its own garden and let it
    see nothing. The floor is the cautious answer: the height that sees least."""
    ground = _slope()
    outside = height_at(ground, 5000.0, 5000.0, floor=97.0)

    assert outside == pytest.approx(97.0)


def test_without_terrain_every_point_is_at_zero() -> None:
    assert height_at(None, 3.0, 4.0, floor=99.0) == 0.0
    assert lowest_ground(None, min_x=0.0, min_y=0.0, cell=1.0, cols=5, rows=5) == 0.0


# --- through the light grid ------------------------------------------------

def test_a_house_uphill_shades_more_than_the_same_house_on_the_level() -> None:
    """The sentence the wave's demo-state promises, as two numbers.

    The same shed, the same distance due south, on flat ground and on ground
    that rises towards it. Standing above the garden it reaches further.
    """
    import sqlite3

    from ninanatur.garden.elements import insert_element
    from ninanatur.garden.lightgrid import compute_grid
    from ninanatur.garden.models import PLANTING_KIND
    from ninanatur.garden.store import create_garden, load_garden
    from ninanatur.ingest.db import connect, init_schema

    conn: sqlite3.Connection = connect(":memory:")
    init_schema(conn)
    garden_id = create_garden(conn, name="G", latitude=52.0, longitude=10.0)
    insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
                   name="Beet", points=[[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]])
    conn.commit()
    garden = load_garden(conn, garden_id)

    # Due south of the bed, and tall enough to matter.
    shed = Obstacle(
        footprint=[(2.0, -8.0), (8.0, -8.0), (8.0, -5.0), (2.0, -5.0)], height=5.0
    )
    # Ground falling away to the north: the shed's end is 1 m above the bed's.
    size = 120
    heights = [
        100.0 - (row - size / 2) * 0.1 for row in range(size) for _ in range(size)
    ]
    rising_south = TerrainWindow(
        min_x=-55.0, min_y=-55.0, cell_m=1.0, cols=size, rows=size, heights=heights,
        source="Test", licence="—", attribution="—", vertical_step_m=0.01,
    )

    flat = compute_grid(garden, [shed])
    sloped = compute_grid(garden, [shed], ground=rising_south)

    assert flat is not None and sloped is not None
    flat_hours = sum(flat.hours) / len(flat.hours)
    sloped_hours = sum(sloped.hours) / len(sloped.hours)
    assert sloped_hours < flat_hours, (
        f"a shed uphill should shade more: {sloped_hours:.2f} h against {flat_hours:.2f} h"
    )
