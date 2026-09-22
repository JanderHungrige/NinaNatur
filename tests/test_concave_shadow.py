"""A concave building shades only what it shades (review, 2026-09-22).

The shadow model swept a footprint and took the convex hull of it and its
swept copy. For a concave outline — an L-shaped house, a house with a garage
built on, both common in OpenStreetMap — that hull covers the open ground in
the inner corner at every sun position, so the sun map showed it at 0 h all day
and a bed there was offered deep-shade plants.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.lightgrid import _exact, compute_grid
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.light import bed_light_value
from ninanatur.solar.position import Location, SunPosition
from ninanatur.solar.reach import is_convex, near_edge
from ninanatur.solar.shading import Obstacle, Point, is_shaded

#: 10 × 10 m with the north-east 6 × 6 open: the inner corner is at (4, 4).
ELL = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (4.0, 4.0), (4.0, 10.0), (0.0, 10.0)]
BOX = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]


def test_the_reach_is_to_the_next_part_of_the_outline_towards_the_sun() -> None:
    """In the frame where the sun lies towards +y: a C open to the east, and a
    point between its arms. It is 1 m from the upper arm, not under the house."""
    c_shape = ((0.0, 0.0), (10.0, 0.0), (10.0, 2.0), (4.0, 2.0),
               (4.0, 4.0), (10.0, 4.0), (10.0, 6.0), (0.0, 6.0))
    assert near_edge(c_shape, 7.0, 3.0) == pytest.approx(1.0)
    assert near_edge(c_shape, 7.0, 1.0) == 0.0, "under an arm"
    assert near_edge(c_shape, 7.0, 7.0) is None, "sunward of it all"


def test_convexity_ignores_a_node_on_a_straight_wall() -> None:
    assert is_convex(BOX)
    assert is_convex([(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])
    assert not is_convex(ELL)


def test_the_inner_corner_of_an_l_is_in_the_sun_when_the_sun_is_behind_it() -> None:
    corner = Point(7.0, 7.0)
    house = Obstacle(footprint=ELL, height=7.0)
    # From the north-east, over open ground: the hull said shaded.
    assert not is_shaded(corner, house, SunPosition(altitude=30.0, azimuth=45.0))
    # From the south-west, across the house: shaded, as it should be.
    assert is_shaded(corner, house, SunPosition(altitude=30.0, azimuth=225.0))


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    yield made


#: A house round a courtyard open to the north, 4 m high.
COURT = [(0.0, 0.0), (12.0, 0.0), (12.0, 12.0), (9.0, 12.0), (9.0, 3.0), (3.0, 3.0),
         (3.0, 12.0), (0.0, 12.0)]


def test_the_sun_map_gives_a_courtyard_its_sun(conn: sqlite3.Connection) -> None:
    """With a wing on either side of it along the sun's line, the courtyard was
    read as under the house: 0 h, all season, in the map and the bed's sample."""
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
                   name="Beet", points=[[4, 6], [8, 6], [8, 11], [4, 11]])
    conn.commit()
    court = [Obstacle(footprint=COURT, height=4.0)]
    grid = compute_grid(load_garden(conn, garden_id), court)
    assert grid is not None
    cell = grid.at(6.0, 9.0)
    sampled = bed_light_value(Location(52.5, 13.4), Point(6.0, 9.0), court).sun_hours
    assert cell is not None and cell > 2.0
    assert sampled == pytest.approx(cell, abs=0.5), "the map and a bed's sample agree"


def test_a_map_of_a_garden_with_a_concave_house_reads_stale_once() -> None:
    """Only there: a garden of rectangles keeps its map."""
    assert _exact(SimpleNamespace(footprint=ELL, height=7.0)) == "|exact"
    assert _exact(SimpleNamespace(footprint=BOX, height=7.0)) == ""
    assert _exact(SimpleNamespace(footprint=ELL, height=None)) == "", "a bed casts nothing"
