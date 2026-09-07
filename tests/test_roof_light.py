"""The sun on a roof, rather than the darkness under a building.

The ground under a house never sees the sun — all day, every day. Reporting that
is true and useless: what a plan shows at a house is the *roof*, and a roof at
51°N is a very different place on its north pitch than on its south.

`test_roofshape.py` covers the geometry on its own. This is the same thing
through the light model, where a pitch has to become fewer hours.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.lightgrid import LightGrid, compute_grid
from ninanatur.garden.lightview import shading_obstacles
from ninanatur.garden.models import PLANTING_KIND, Garden, ObstacleInput
from ninanatur.garden.store import add_obstacle, create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:")
    init_schema(connection)
    yield connection


def _house_garden(
    conn: sqlite3.Connection, roof: str, height: float = 9.0
) -> Garden:
    """A 12 x 8 m house, long axis east-west, with a bed to the south of it.

    The long axis is what the ridge is assumed to run along, so this house has
    one pitch facing north and one facing south — which at 51°N is the whole
    reason a roof needs more than one number.
    """
    garden_id = create_garden(conn, name="G", latitude=51.2564, longitude=7.1501)
    add_obstacle(conn, garden_id, ObstacleInput(
        kind="house", x=0, y=0, shape="rect", width=12, depth=8,
        height=height, roof=roof, eaves_m=6.0, label="Haus"))
    insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
                   name="Beet", points=[[-8.0, -14.0], [8.0, -14.0],
                                        [8.0, -8.0], [-8.0, -8.0]])
    conn.commit()
    return load_garden(conn, garden_id)


def _pitches(grid: LightGrid) -> tuple[float, float]:
    """The hours on the north pitch and on the south pitch."""
    north = south = None
    for index, hours in enumerate(grid.hours):
        if not grid.is_roof(index):
            continue
        x, y = grid.centre_of(index % grid.cols, index // grid.cols)
        if abs(x) < 2:
            if 2.0 < y < 3.5:
                north = hours
            if -3.5 < y < -2.0:
                south = hours
    assert north is not None and south is not None
    return north, south


def test_a_roof_is_not_the_darkness_underneath_it(conn: sqlite3.Connection) -> None:
    """The complaint this answers: a house read as full shade everywhere,
    because the ground under a building never sees the sun — which is true, and
    not what anyone looking down at a plan is asking about."""
    garden = _house_garden(conn, "gable")
    grid = compute_grid(garden, shading_obstacles(conn, garden))

    north, south = _pitches(grid)
    assert north > 5.0 and south > 5.0
    assert any(grid.is_roof(i) for i in range(len(grid.hours)))


def test_the_north_pitch_gets_less_sun_than_the_south_one(
    conn: sqlite3.Connection,
) -> None:
    """The roof type is in the calculation now, not only in the shadow the
    building throws. A ridge stands between the north pitch and the noon sun."""
    garden = _house_garden(conn, "gable")
    grid = compute_grid(garden, shading_obstacles(conn, garden))

    north, south = _pitches(grid)
    assert north < south


def test_a_steeper_pitch_costs_the_north_face_more(conn: sqlite3.Connection) -> None:
    """The mechanism, not a coincidence of one geometry: the pitch is folded
    into the sky exactly the way a hillside is, so a steeper roof stands higher
    in front of the southern sun."""
    shallow = _house_garden(conn, "gable", height=7.0)
    steep = _house_garden(conn, "gable", height=13.0)

    gentle, _ = _pitches(compute_grid(shallow, shading_obstacles(conn, shallow)))
    sharp, _ = _pitches(compute_grid(steep, shading_obstacles(conn, steep)))

    assert sharp < gentle


def test_a_flat_roof_has_no_darker_side(conn: sqlite3.Connection) -> None:
    garden = _house_garden(conn, "flat")
    grid = compute_grid(garden, shading_obstacles(conn, garden))

    north, south = _pitches(grid)
    assert north == pytest.approx(south)


def test_a_roof_never_reaches_the_bed_below_it(conn: sqlite3.Connection) -> None:
    """A roof's sun is a real answer to a different question. Averaging it into
    a bed would place a plant by a number taken nine metres above it."""
    garden = _house_garden(conn, "gable")
    grid = compute_grid(garden, shading_obstacles(conn, garden))

    # Straight through the house: every cell inside it is a roof cell.
    assert grid.mean_over([[-5.0, -3.0], [5.0, -3.0], [5.0, 3.0], [-5.0, 3.0]]) is None
