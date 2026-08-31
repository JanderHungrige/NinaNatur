"""Re-labelling an element, and what it costs.

Wave 11's whole point: an element is drawn first and named afterwards. Being a
planting site is a property, so changing it is an ordinary edit — except when
there are plants standing in it.
"""
from __future__ import annotations

import sqlite3

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.plantings import add_planting
from ninanatur.garden.store import create_garden, load_garden, update_obstacle
from ninanatur.ingest.db import connect, init_schema


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = connect(":memory:")
    init_schema(connection)
    connection.execute(
        "INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Salvia pratensis')"
    )
    connection.commit()
    return connection


def _bed_with_plants(connection: sqlite3.Connection) -> tuple[int, int]:
    garden_id = create_garden(connection, name="G", latitude=52.5, longitude=13.4)
    element_id = insert_element(
        connection, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
        name="Beet", points=[[0, 0], [4, 0], [4, 3], [0, 3]],
    )
    connection.commit()
    add_planting(connection, element_id, taxon_id=1, quantity=3)
    return garden_id, element_id


def test_a_bed_can_become_a_pool(conn: sqlite3.Connection) -> None:
    """The plain case, and the one that was impossible before the merge: it
    used to mean moving a row between two tables."""
    garden_id, element_id = _bed_with_plants(conn)
    update_obstacle(conn, element_id, kind="pond")
    element = next(e for e in load_garden(conn, garden_id).elements)
    assert element.kind == "pond"
    assert not element.is_planting_site


def test_the_plants_go_with_it(conn: sqlite3.Connection) -> None:
    """Decided with the user: warn, then delete. Keeping them would leave data
    that nothing displays; refusing would be a dead end mid-drawing."""
    garden_id, element_id = _bed_with_plants(conn)
    assert conn.execute("SELECT count(*) FROM planting").fetchone()[0] == 1
    update_obstacle(conn, element_id, kind="pond")
    assert conn.execute("SELECT count(*) FROM planting").fetchone()[0] == 0


def test_plants_survive_a_change_that_is_still_a_bed(conn: sqlite3.Connection) -> None:
    """Renaming or moving a bed is not the same as ceasing to be one."""
    _garden_id, element_id = _bed_with_plants(conn)
    update_obstacle(conn, element_id, label="Südbeet")
    assert conn.execute("SELECT count(*) FROM planting").fetchone()[0] == 1


def test_becoming_a_bed_costs_nothing(conn: sqlite3.Connection) -> None:
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    element_id = insert_element(
        conn, garden_id, kind="gravel", shape="polygon", x=0, y=0,
        points=[[0, 0], [4, 0], [4, 3], [0, 3]],
    )
    conn.commit()
    update_obstacle(conn, element_id, kind=PLANTING_KIND)
    element = next(e for e in load_garden(conn, garden_id).elements)
    assert element.is_planting_site
    assert element.plantings == []



# A `plantings_at_risk` helper stood here to answer "how many plants would this
# cost?" for the warning. It went: the browser already has the plantings in the
# garden it is displaying, so counting them again on the server is a second
# answer to a question that already has one.
