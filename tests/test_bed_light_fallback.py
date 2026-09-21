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
