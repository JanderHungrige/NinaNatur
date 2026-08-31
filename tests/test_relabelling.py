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
    connection = connect(":memory:", same_thread=False)
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


def test_a_bed_can_still_be_reached_after_it_becomes_one(conn: sqlite3.Connection) -> None:
    """The endpoint used to look in `garden.obstacles`, which since the merge is
    a *view* that excludes planting sites. An element that had just been made a
    bed was then unreachable through the only endpoint that edits a kind — so
    a bed could be created and never changed back."""
    from fastapi.testclient import TestClient

    from ninanatur.api.deps import get_connection
    from ninanatur.web.app import app

    app.dependency_overrides[get_connection] = lambda: conn
    try:
        with TestClient(app) as client:
            token = client.post(
                "/api/v1/gardens",
                json={"name": "G", "latitude": 52.5, "longitude": 13.4},
            ).json()["share_token"]
            made = client.post(
                f"/api/v1/gardens/{token}/obstacles",
                json={"kind": "other", "x": 0, "y": 0, "shape": "polygon",
                      "points": [[-3, -2], [3, -2], [3, 2], [-3, 2]]},
            ).json()["obstacles"][0]

            as_bed = client.patch(
                f"/api/v1/gardens/{token}/obstacles/{made['obstacle_id']}",
                json={"kind": "bed"},
            )
            assert as_bed.status_code == 200

            # And back again, which is the half that was impossible.
            back = client.patch(
                f"/api/v1/gardens/{token}/obstacles/{made['obstacle_id']}",
                json={"kind": "pond"},
            )
            assert back.status_code == 200, back.json()
            assert back.json()["obstacles"][0]["kind"] == "pond"
    finally:
        app.dependency_overrides.clear()


def test_a_bed_can_be_told_its_own_soil(conn: sqlite3.Connection) -> None:
    """A raised bed with bought soil. The store allowed it; the API model did
    not carry the fields, so it never arrived."""
    from fastapi.testclient import TestClient

    from ninanatur.api.deps import get_connection
    from ninanatur.web.app import app

    app.dependency_overrides[get_connection] = lambda: conn
    try:
        with TestClient(app) as client:
            token = client.post(
                "/api/v1/gardens",
                json={"name": "G", "latitude": 52.5, "longitude": 13.4},
            ).json()["share_token"]
            client.patch(
                f"/api/v1/gardens/{token}/soil",
                json={"soil_type": "clay", "moisture": "moist"},
            )
            made = client.post(
                f"/api/v1/gardens/{token}/obstacles",
                json={"kind": "bed", "x": 0, "y": 0, "shape": "polygon",
                      "points": [[-3, -2], [3, -2], [3, 2], [-3, 2]]},
            ).json()
            bed_id = made["beds"][0]["bed_id"]
            changed = client.patch(
                f"/api/v1/gardens/{token}/obstacles/{bed_id}",
                json={"soil_type": "humus", "moisture": "dry"},
            ).json()
            bed = changed["beds"][0]
            assert bed["soil_type"] == "humus"
            assert bed["moisture"] == "dry"
    finally:
        app.dependency_overrides.clear()
