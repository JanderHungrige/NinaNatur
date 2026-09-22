"""A bed with no cells of its own is measured at one point, and not under a house.

`lighting.recompute_light` averages the cells whose centres fall in a bed; a
raised bed, or one narrower than a cell, is sampled at a point instead. That
point was its middle, wherever it lay.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.lightgrid_store import load_grid
from ninanatur.garden.lighting import recompute_light
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema

HOUSE = [[0, 0], [10, 0], [10, 8], [0, 8]]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    yield made


def _border(conn: sqlite3.Connection, outline: list[list[float]]) -> float | None:
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    insert_element(conn, garden_id, kind="house", shape="polygon", x=0, y=0,
                   points=HOUSE, height=7.0, roof="flat")
    insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
                   name="Rabatte", points=outline, soil_type="loam", moisture="fresh")
    conn.commit()
    recompute_light(conn, garden_id)
    bed = load_garden(conn, garden_id).beds[0]
    stored = load_grid(conn, garden_id)
    assert stored is not None and stored[0].mean_over(bed.polygon) is None, "sampled"
    return bed.sun_hours


def test_a_border_drawn_over_a_houses_wall_is_not_measured_under_the_house(
    conn: sqlite3.Connection,
) -> None:
    """Its middle lay inside the house, where the sun never reaches, and a south
    border in full sun was stored as deep shade (review, 2026-09-21)."""
    hours = _border(conn, [[1, -0.1], [9, -0.1], [9, 0.3], [1, 0.3]])
    assert hours is not None and hours > 6.0


def test_a_border_clear_of_the_house_is_still_measured_at_its_middle(
    conn: sqlite3.Connection,
) -> None:
    """Nothing changes for a bed whose middle is in the open: north of the house,
    in its shadow, it stays in the shade it is in."""
    hours = _border(conn, [[1, 8.3], [9, 8.3], [9, 8.6], [1, 8.6]])
    assert hours is not None and hours < 4.0


def test_a_bed_measured_at_a_point_sees_what_the_cell_there_sees(
    conn: sqlite3.Connection,
) -> None:
    """On sloping ground under a ring of hills the point stood on flat ground
    under an open sky, and a narrow bed saw a sky, a light and a sunshine its
    neighbouring cells did not (review, 2026-09-22). Asked at a cell's centre,
    the point answers what the cell does."""
    from ninanatur.garden.lightgrid import compute_grid
    from ninanatur.garden.lighting import _PointLight
    from ninanatur.garden.lightview import shading_obstacles
    from ninanatur.geo.terrain import TerrainWindow
    from ninanatur.solar.position import Location

    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    insert_element(conn, garden_id, kind="house", shape="polygon", x=0, y=0,
                   points=HOUSE, height=7.0, roof="flat")
    insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
                   name="Beet", points=[[0, -12], [10, -12], [10, -2], [0, -2]],
                   soil_type="loam", moisture="fresh")
    conn.commit()
    garden = load_garden(conn, garden_id)
    size = 120
    ground = TerrainWindow(  # falling away to the north, 15 cm a metre
        min_x=-55.0, min_y=-55.0, cell_m=1.0, cols=size, rows=size,
        heights=[150.0 - (row - size / 2) * 0.15 for row in range(size) for _ in range(size)],
        source="Test", licence="—", attribution="—", vertical_step_m=0.01)
    horizon = [14.0 if 90 <= d <= 270 else 3.0 for d in range(360)]
    obstacles = shading_obstacles(conn, garden)
    grid = compute_grid(garden, obstacles, ground=ground, horizon=horizon)
    assert grid is not None
    point = _PointLight(obstacles, Location(51.25, 7.15), ground, horizon)
    checked = 0
    for col in range(0, grid.cols, 5):
        for row in range(0, grid.rows, 5):
            index = row * grid.cols + col
            if grid.is_roof(index) or grid.hours[index] is None:
                continue
            hours, sky, relative, expected = point.at(*grid.centre_of(col, row), 0.0)
            assert hours == pytest.approx(grid.hours[index], abs=0.006)
            assert sky == pytest.approx(grid.sky[index], abs=6e-4)
            assert relative == pytest.approx(grid.relative[index], abs=6e-4)
            assert expected == pytest.approx(grid.expected[index], abs=0.006)
            checked += 1
    assert checked >= 10
