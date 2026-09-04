"""Light across the whole garden, and knowing when it has gone stale."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.lightgrid import (
    MAX_CELLS,
    cell_size_for,
    compute_grid,
    extent_of,
    load_grid,
    save_grid,
    signature_of,
)
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.plantings import add_planting, place_planting
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.shading import Obstacle

SQUARE = [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    connection.execute(
        "INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Salvia pratensis')"
    )
    connection.commit()
    yield connection


def _garden(conn: sqlite3.Connection) -> int:
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    insert_element(
        conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
        name="Beet", points=SQUARE,
    )
    conn.commit()
    return garden_id


# --- how fine the grid is --------------------------------------------------

def test_a_small_garden_gets_the_finest_cell() -> None:
    assert cell_size_for(10.0, 8.0) == 0.5


def test_a_large_plot_gets_a_coarser_one_rather_than_a_long_wait() -> None:
    """A 40 x 60 m plot at 1 m is 2,400 cells and 2.7 seconds. Nobody waits that
    long after nudging a shed."""
    cell = cell_size_for(40.0, 60.0)

    assert (40.0 / cell) * (60.0 / cell) <= MAX_CELLS
    assert cell > 1.0


def test_even_a_field_stays_bounded() -> None:
    cell = cell_size_for(300.0, 300.0)
    assert cell == 5.0, "the ladder ends; it does not grow without limit"


# --- what it covers --------------------------------------------------------

def test_the_grid_covers_everything_drawn_not_only_the_beds(
    conn: sqlite3.Connection,
) -> None:
    """The ground between beds is where somebody decides to put the next one."""
    garden_id = _garden(conn)
    insert_element(
        conn, garden_id, kind="shed", shape="polygon", x=0, y=0,
        points=[[20.0, 20.0], [24.0, 20.0], [24.0, 23.0], [20.0, 23.0]], height=2.4,
    )
    conn.commit()

    box = extent_of(load_garden(conn, garden_id))

    assert box is not None
    assert box[2] >= 24.0 and box[3] >= 23.0


def test_an_empty_garden_has_no_grid(conn: sqlite3.Connection) -> None:
    garden_id = create_garden(conn, name="leer", latitude=52.5, longitude=13.4)
    assert compute_grid(load_garden(conn, garden_id), []) is None


# --- the answer ------------------------------------------------------------

def test_a_wall_darkens_the_cells_behind_it_and_not_the_others(
    conn: sqlite3.Connection,
) -> None:
    """The whole point of a grid. One number per bed could not say this."""
    garden_id = _garden(conn)
    # A 6 m wall along the southern edge: the sun is in the south here.
    wall = Obstacle(footprint=[(0.0, -1.0), (10.0, -1.0), (10.0, -0.5), (0.0, -0.5)],
                    height=6.0)

    grid = compute_grid(load_garden(conn, garden_id), [wall])

    assert grid is not None
    near = grid.at(5.0, 0.5)
    far = grid.at(5.0, 7.5)
    assert near is not None and far is not None
    assert near < far, "the strip against the wall gets less sun than the far end"
    assert far > 4.0, "and the far end is not dark"


def test_a_bed_takes_the_mean_of_its_cells(conn: sqlite3.Connection) -> None:
    garden_id = _garden(conn)
    wall = Obstacle(footprint=[(0.0, -1.0), (10.0, -1.0), (10.0, -0.5), (0.0, -0.5)],
                    height=6.0)
    grid = compute_grid(load_garden(conn, garden_id), [wall])

    assert grid is not None
    mean = grid.mean_over(SQUARE)
    assert mean is not None
    assert grid.at(5.0, 0.5) < mean < grid.at(5.0, 7.5)  # type: ignore[operator]


def test_a_bed_too_narrow_for_a_cell_says_so_rather_than_zero() -> None:
    """Zero is a number this model uses for real darkness. A bed that no cell
    centre falls inside is a different thing and must not borrow it."""
    from ninanatur.garden.lightgrid import LightGrid

    grid = LightGrid(min_x=0, min_y=0, cell_m=2.0, cols=3, rows=3, hours=[8.0] * 9)

    assert grid.mean_over([[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]) is None


# --- staleness -------------------------------------------------------------

def test_the_signature_moves_when_a_shadow_would(conn: sqlite3.Connection) -> None:
    garden_id = _garden(conn)
    before = signature_of(load_garden(conn, garden_id))

    insert_element(
        conn, garden_id, kind="shed", shape="polygon", x=0, y=0,
        points=[[2.0, 12.0], [5.0, 12.0], [5.0, 15.0], [2.0, 15.0]], height=2.4,
    )
    conn.commit()

    assert signature_of(load_garden(conn, garden_id)) != before


def test_the_signature_stays_put_when_nothing_would(conn: sqlite3.Connection) -> None:
    """The reason this is a signature and not a list of actions.

    Renaming a bed cannot move a shadow, and neither can a soil type. A list of
    invalidating operations has to be extended by hand for every new feature,
    and forgetting is silent — a stale map that looks right.
    """
    garden_id = _garden(conn)
    before = signature_of(load_garden(conn, garden_id))

    conn.execute(
        "UPDATE element SET name = 'Anderer Name', soil_type = 'sand',"
        " label = 'hinten links' WHERE garden_id = ?",
        (garden_id,),
    )
    conn.commit()

    assert signature_of(load_garden(conn, garden_id)) == before


def test_moving_a_planting_moves_the_signature(conn: sqlite3.Connection) -> None:
    """A cluster has coordinates since Wave 15, and a tree standing somewhere
    else shades somewhere else."""
    garden_id = _garden(conn)
    bed_id = load_garden(conn, garden_id).beds[0].bed_id
    planting_id = add_planting(conn, bed_id, taxon_id=1, quantity=1)
    before = signature_of(load_garden(conn, garden_id))

    place_planting(conn, planting_id, 2.0, 3.0)

    assert signature_of(load_garden(conn, garden_id)) != before


def test_a_grid_survives_being_stored(conn: sqlite3.Connection) -> None:
    garden_id = _garden(conn)
    grid = compute_grid(load_garden(conn, garden_id), [])
    assert grid is not None

    save_grid(conn, garden_id, grid, "abc123")
    read = load_grid(conn, garden_id)

    assert read is not None
    stored, signature, computed_at = read
    assert stored == grid
    assert signature == "abc123"
    assert computed_at


def test_storing_twice_replaces_rather_than_accumulates(
    conn: sqlite3.Connection,
) -> None:
    garden_id = _garden(conn)
    grid = compute_grid(load_garden(conn, garden_id), [])
    assert grid is not None

    save_grid(conn, garden_id, grid, "one")
    save_grid(conn, garden_id, grid, "two")

    rows = conn.execute("SELECT count(*) FROM light_grid").fetchone()[0]
    assert rows == 1
    read = load_grid(conn, garden_id)
    assert read is not None and read[1] == "two"
