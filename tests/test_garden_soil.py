"""The soil is asked once for the garden, and a bed may differ.

The same shape Wave 8 settled on for building heights: one question per garden
rather than one per object, because asking per bed is a wall in front of
somebody who has just arrived.
"""
from __future__ import annotations

import sqlite3

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.store import create_garden, load_garden, set_garden_soil, update_obstacle
from ninanatur.ingest.db import connect, init_schema


@pytest.fixture()
def conn() -> sqlite3.Connection:
    # `same_thread=False` because one test drives the API, whose sync
    # endpoints run in FastAPI's threadpool.
    connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    return connection


def test_a_new_garden_has_no_soil_yet(conn: sqlite3.Connection) -> None:
    """Unknown, not guessed. A default here would be a claim about a place
    nobody has described."""
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    garden = load_garden(conn, garden_id)
    assert garden.soil_type is None
    assert garden.moisture is None


def test_the_answer_is_stored_on_the_garden(conn: sqlite3.Connection) -> None:
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    set_garden_soil(conn, garden_id, soil_type="loam", moisture="fresh")
    garden = load_garden(conn, garden_id)
    assert garden.soil_type == "loam"
    assert garden.moisture == "fresh"


def test_a_bed_drawn_afterwards_starts_from_it(conn: sqlite3.Connection) -> None:
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    set_garden_soil(conn, garden_id, soil_type="clay", moisture="moist")
    element_id = insert_element(
        conn, garden_id, kind="other", shape="polygon", x=0, y=0,
        points=[[0, 0], [4, 0], [4, 3], [0, 3]],
    )
    conn.commit()
    update_obstacle(conn, element_id, kind=PLANTING_KIND)
    bed = load_garden(conn, garden_id).beds[0]
    assert bed.soil_type == "clay"
    assert bed.moisture == "moist"
    # And the axes that the suggestions rank on come with it.
    assert bed.ellenberg_m is not None
    assert bed.ellenberg_r is not None


def test_a_bed_that_says_otherwise_keeps_its_own(conn: sqlite3.Connection) -> None:
    """A raised bed with bought soil, or a corner that gets watered."""
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    set_garden_soil(conn, garden_id, soil_type="clay", moisture="moist")
    element_id = insert_element(
        conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
        soil_type="humus", moisture="dry",
        points=[[0, 0], [4, 0], [4, 3], [0, 3]],
    )
    conn.commit()
    update_obstacle(conn, element_id, label="Hochbeet")
    bed = load_garden(conn, garden_id).beds[0]
    assert bed.soil_type == "humus"
    assert bed.moisture == "dry"


def test_changing_the_garden_leaves_beds_that_already_answered(
    conn: sqlite3.Connection,
) -> None:
    """The garden value is a starting point, not a broadcast. Overwriting a bed
    somebody set by hand is the kind of helpfulness nobody asks for twice."""
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    set_garden_soil(conn, garden_id, soil_type="loam", moisture="fresh")
    insert_element(
        conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
        soil_type="sand", moisture="dry",
        points=[[0, 0], [4, 0], [4, 3], [0, 3]],
    )
    conn.commit()
    set_garden_soil(conn, garden_id, soil_type="clay", moisture="wet")
    assert load_garden(conn, garden_id).beds[0].soil_type == "sand"


def test_an_unknown_soil_is_refused(conn: sqlite3.Connection) -> None:
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    with pytest.raises(ValueError, match="soil"):
        set_garden_soil(conn, garden_id, soil_type="beton", moisture="fresh")


def test_the_endpoint_refuses_a_soil_nobody_can_map(
    conn: sqlite3.Connection,
) -> None:
    """422 rather than a stored value the axes cannot read. An unknown soil
    would otherwise sit there until a bed inherited it and the mapping raised."""
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
            bad = client.patch(
                f"/api/v1/gardens/{token}/soil",
                json={"soil_type": "beton", "moisture": "fresh"},
            )
            assert bad.status_code == 422
            good = client.patch(
                f"/api/v1/gardens/{token}/soil",
                json={"soil_type": "loam", "moisture": "fresh"},
            )
            assert good.json()["soil_type"] == "loam"
    finally:
        app.dependency_overrides.clear()
