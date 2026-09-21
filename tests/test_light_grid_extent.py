"""What the light grid covers: the garden, not the neighbourhood (owner #6).

A garden made from the map carries its neighbours' houses up to 50 m out and
every street at full length. The grid used to cover all of it, and the time
budget answered with 3 m cells over a 25 x 40 m plot. Staleness is in
tests/test_light_grid_stale.py.
"""
from __future__ import annotations

import random
import sqlite3
from collections.abc import Iterator

import pytest
from extent_builders import PLOT, PLOT_BOX, M, add, garden_with, neighbour, rect

from ninanatur.garden.footprint import covers
from ninanatur.garden.lightgrid import LightGrid, compute_grid
from ninanatur.garden.lightgrid_extent import GardenTooLarge, grid_extent_of
from ninanatur.garden.lightview import shading_obstacles
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    yield connection


def _box(conn: sqlite3.Connection, garden_id: int) -> tuple[float, ...] | None:
    return grid_extent_of(load_garden(conn, garden_id))


# --- what it covers -----------------------------------------------------------

def test_the_grid_covers_the_plot_and_a_margin_not_the_neighbours(
    conn: sqlite3.Connection,
) -> None:
    garden_id = garden_with(conn, PLOT)
    neighbour(conn, garden_id, rect(60.0, 10.0, 70.0, 20.0))
    neighbour(conn, garden_id, rect(-45.0, -30.0, -35.0, -22.0))

    assert _box(conn, garden_id) == PLOT_BOX


@pytest.mark.parametrize("plot", [PLOT, None], ids=["plot", "no-plot"])
def test_streets_do_not_widen_the_grid(
    conn: sqlite3.Connection, plot: list[list[float]] | None
) -> None:
    """A way arrives from OpenStreetMap at full length, to the next junction."""
    garden_id = garden_with(conn, plot)
    before = _box(conn, garden_id)
    add(conn, garden_id, "street", [[-300.0, -20.0], [300.0, -20.0]], None)

    assert _box(conn, garden_id) == before


def test_nothing_without_a_height_widens_the_grid(conn: sqlite3.Connection) -> None:
    garden_id = garden_with(conn, PLOT)
    add(conn, garden_id, "paving", rect(40.0, 0.0, 48.0, 6.0), None)

    assert _box(conn, garden_id) == PLOT_BOX


def test_a_bed_drawn_outside_the_plot_is_still_covered(conn: sqlite3.Connection) -> None:
    garden_id = garden_with(conn, PLOT)
    add(conn, garden_id, "bed", rect(40.0, 0.0, 44.0, 3.0), None)

    assert _box(conn, garden_id) == (-M, -M, 44.0 + M, 40.0 + M)


@pytest.mark.parametrize(
    ("height_source", "roof_source", "covered"),
    [
        ("user", "user", True),                # drawn with the tools
        ("osm_levels", "osm", False),          # brought by the import
        ("surveyed", "surveyed", False),       # measured by the state's survey
        ("measured", "osm", False),            # measured from the surface raster
        ("user", "osm", False),                # a neighbour's height corrected
        ("osm_height", "user", False),         # a neighbour's roof corrected
    ],
)
def test_what_the_gardener_drew_outside_the_plot_is_covered(
    conn: sqlite3.Connection, height_source: str, roof_source: str, covered: bool
) -> None:
    """Their own shed behind the fence is part of their garden; the neighbour's
    house is not, even after they corrected its height."""
    garden_id = garden_with(conn, PLOT)
    add(conn, garden_id, "shed", rect(50.0, 50.0, 53.0, 52.0), 2.4,
        height_source=height_source, roof_source=roof_source)

    expected = (-M, -M, 53.0 + M, 52.0 + M) if covered else PLOT_BOX
    assert _box(conn, garden_id) == expected


def test_a_garden_without_a_plot_falls_back_to_what_stands_on_it(
    conn: sqlite3.Connection,
) -> None:
    """Nothing tells its ground from the neighbours', so every standing thing
    counts, imported or not — and no margin, as before."""
    garden_id = garden_with(conn, None)
    neighbour(conn, garden_id, rect(20.0, 0.0, 30.0, 8.0))
    add(conn, garden_id, "street", [[-300.0, -20.0], [300.0, -20.0]], None)
    add(conn, garden_id, "lawn", rect(-20.0, 0.0, -10.0, 6.0), None)

    # The bed from (2, 2) and the neighbour's house to (30, 8); not the lawn.
    assert _box(conn, garden_id) == (2.0, 0.0, 30.0, 8.0)


def test_a_garden_of_surfaces_alone_is_covered_by_its_surfaces(
    conn: sqlite3.Connection,
) -> None:
    """No plot, no bed, nothing standing: a lawn and a path are the garden. It
    got no grid at all, and an old map then read stale for ever (review)."""
    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    add(conn, garden_id, "lawn", rect(0.0, 0.0, 10.0, 6.0), None)
    add(conn, garden_id, "street", [[-300.0, -20.0], [300.0, -20.0]], None)

    assert _box(conn, garden_id) == (0.0, 0.0, 10.0, 6.0)


def test_a_map_that_can_no_longer_be_computed_is_removed_not_left_stale(
    conn: sqlite3.Connection,
) -> None:
    from ninanatur.garden.lightgrid_store import load_grid
    from ninanatur.garden.lighting import recompute_light

    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    lawn = add(conn, garden_id, "lawn", rect(0.0, 0.0, 10.0, 6.0), None)
    recompute_light(conn, garden_id)
    assert load_grid(conn, garden_id) is not None
    conn.execute("DELETE FROM element WHERE element_id = ?", (lawn,))
    add(conn, garden_id, "street", [[-300.0, -20.0], [300.0, -20.0]], None)
    recompute_light(conn, garden_id)
    assert load_grid(conn, garden_id) is None


def test_a_garden_of_streets_alone_has_no_grid(conn: sqlite3.Connection) -> None:
    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    add(conn, garden_id, "street", [[-300.0, -20.0], [300.0, -20.0]], None)

    assert compute_grid(load_garden(conn, garden_id), []) is None


# --- the neighbours still cast their shadows ----------------------------------

def test_a_neighbour_house_outside_the_plot_still_shades_a_cell_inside_it(
    conn: sqlite3.Connection,
) -> None:
    """Only the cells over the neighbour's land go, not the neighbour."""
    garden_id = garden_with(conn, rect(0.0, 0.0, 10.0, 8.0))
    # Due south, past the margin, and tall.
    neighbour(conn, garden_id, rect(0.0, -14.0, 10.0, -6.0), height=12.0)
    garden = load_garden(conn, garden_id)

    shaded = compute_grid(garden, list(shading_obstacles(conn, garden)))
    open_sky = compute_grid(garden, [])

    assert shaded is not None and open_sky is not None
    assert shaded.min_y == -M, "the grid stops at the margin, short of the house"
    near_fence, open_near_fence = shaded.at(5.0, 0.5), open_sky.at(5.0, 0.5)
    assert near_fence is not None and open_near_fence is not None
    assert near_fence < open_near_fence - 1.0


# --- the refusal asks about the box it computes -------------------------------

def test_streets_across_the_whole_range_are_no_reason_to_refuse(
    conn: sqlite3.Connection,
) -> None:
    """They made the old box 3.9 km square, which `check_extent` refused."""
    garden_id = garden_with(conn, None)
    add(conn, garden_id, "street", [[-1950.0, -1950.0], [1950.0, -1950.0]], None)
    add(conn, garden_id, "street", [[-1950.0, 1950.0], [1950.0, 1950.0]], None)

    grid = compute_grid(load_garden(conn, garden_id), [])

    assert grid is not None and grid.cell_m == 0.5


def test_something_drawn_far_out_is_still_refused(conn: sqlite3.Connection) -> None:
    garden_id = garden_with(conn, PLOT)
    add(conn, garden_id, "shed", rect(-1990.0, -1990.0, -1987.0, -1988.0), 2.4)
    add(conn, garden_id, "shed", rect(1987.0, 1988.0, 1990.0, 1990.0), 2.4)

    with pytest.raises(GardenTooLarge):
        compute_grid(load_garden(conn, garden_id), [])


# --- a bed's mean reads only the cells near it --------------------------------

def _mean_over_every_cell(grid: LightGrid, polygon: list[list[float]]) -> float | None:
    """`mean_over` as it was: every cell of the grid asked about every bed."""
    ring = [(float(p[0]), float(p[1])) for p in polygon]
    inside = [
        hours
        for row in range(grid.rows)
        for col in range(grid.cols)
        if covers(ring, grid.centre_of(col, row))
        and not grid.is_roof(row * grid.cols + col)
        and (hours := grid.hours[row * grid.cols + col]) is not None
    ]
    return sum(inside) / len(inside) if inside else None


def _random_bed(rng: random.Random, grid: LightGrid) -> list[list[float]]:
    """Three to six corners anywhere near the grid, off it included. Half the
    time they sit on cell centres, where `covers` counts the edge as inside."""
    snap = rng.random() < 0.5
    corners = []
    for _ in range(rng.randint(3, 6)):
        x = grid.min_x + rng.uniform(-5.0, grid.cols * grid.cell_m + 5.0)
        y = grid.min_y + rng.uniform(-5.0, grid.rows * grid.cell_m + 5.0)
        if snap:
            x = grid.min_x + (round((x - grid.min_x) / grid.cell_m - 0.5) + 0.5) * grid.cell_m
            y = grid.min_y + (round((y - grid.min_y) / grid.cell_m - 0.5) + 0.5) * grid.cell_m
        corners.append([x, y])
    return corners


def test_a_bed_mean_is_what_it_was_when_every_cell_was_asked() -> None:
    """Limited to the cells around the bed for speed; the answer must not move,
    to the last bit — edges, roofs, gaps and beds hanging off the grid included."""
    rng = random.Random(21)
    for _ in range(400):
        cols, rows = rng.randint(1, 30), rng.randint(1, 30)
        n = cols * rows
        grid = LightGrid(
            min_x=rng.uniform(-5, 5), min_y=rng.uniform(-5, 5),
            cell_m=rng.choice((0.5, 1.0, 2.0)), cols=cols, rows=rows,
            hours=[None if rng.random() < 0.1 else rng.uniform(0, 12) for _ in range(n)],
            roof=[rng.random() < 0.1 for _ in range(n)] if rng.random() < 0.5 else [],
        )
        bed = _random_bed(rng, grid)

        assert grid.mean_over(bed) == _mean_over_every_cell(grid, bed)
