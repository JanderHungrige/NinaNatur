"""A flower colour the gardener recorded themselves.

Colour is recorded for 590 of 8,939 species. Now that the info panel shows a
photograph, somebody looking at their own bed can often say what the catalogue
cannot — and the plan should be able to use that.

Where it must *not* go is the catalogue. That ships inside the image and is
re-synced at startup whenever the build stamps differ, so a user's row would be
overwritten by the next deployment — and until it was, it would change the
suggestions of every other garden on the server. CLAUDE.md's rule: the
catalogue and user data do not share a source of truth.
"""
from __future__ import annotations

import sqlite3

import pytest

from ninanatur.bloom.palette import garden_palette
from ninanatur.garden.elements import insert_element
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.observations import observed_colours, record_colour
from ninanatur.garden.plantings import add_planting
from ninanatur.garden.store import create_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    connection.execute(
        "INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Salvia pratensis')"
    )
    connection.execute(
        "INSERT INTO taxon (taxon_id, canonical_name) VALUES (2, 'Achillea millefolium')"
    )
    for taxon in (1, 2):
        for key, value in (("flowering_start_month", 6.0), ("flowering_end_month", 8.0)):
            upsert_trait(
                connection, taxon, key, source="test", license="CC0", value_num=value
            )
    connection.commit()
    return connection


def _garden_with(conn: sqlite3.Connection, taxon_id: int) -> tuple[int, int]:
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    bed_id = insert_element(
        conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
        name="Beet", points=[[0, 0], [4, 0], [4, 3], [0, 3]],
    )
    conn.commit()
    add_planting(conn, bed_id, taxon_id=taxon_id, quantity=1)
    return garden_id, bed_id


def test_an_observation_fills_a_colour_the_catalogue_lacks(
    conn: sqlite3.Connection,
) -> None:
    garden_id, _bed = _garden_with(conn, 1)
    before = garden_palette(conn, garden_id)["beds"][0]["months"][5]
    assert before["colours"] == []
    assert before["unknown"] == 1

    record_colour(conn, garden_id, taxon_id=1, colour="violet")
    after = garden_palette(conn, garden_id)["beds"][0]["months"][5]
    assert after["colours"] == ["violet"]
    assert after["unknown"] == 0


def test_it_stays_in_the_garden_that_recorded_it(conn: sqlite3.Connection) -> None:
    """The catalogue is shared by every garden on the server. One gardener's
    observation must not become everybody's."""
    mine, _bed = _garden_with(conn, 1)
    theirs, _other = _garden_with(conn, 1)
    record_colour(conn, mine, taxon_id=1, colour="violet")

    assert garden_palette(conn, mine)["beds"][0]["months"][5]["colours"] == ["violet"]
    assert garden_palette(conn, theirs)["beds"][0]["months"][5]["colours"] == []


def test_nothing_is_written_to_the_catalogue(conn: sqlite3.Connection) -> None:
    """The catalogue ships in the image and is re-synced at startup. A row
    written here would be overwritten by the next deployment."""
    garden_id, _bed = _garden_with(conn, 1)
    before = conn.execute("SELECT count(*) FROM trait").fetchone()[0]
    record_colour(conn, garden_id, taxon_id=1, colour="violet")
    assert conn.execute("SELECT count(*) FROM trait").fetchone()[0] == before


def test_a_second_answer_replaces_the_first(conn: sqlite3.Connection) -> None:
    garden_id, _bed = _garden_with(conn, 1)
    record_colour(conn, garden_id, taxon_id=1, colour="violet")
    record_colour(conn, garden_id, taxon_id=1, colour="blue")
    assert observed_colours(conn, garden_id) == {1: "blue"}


def test_it_can_be_taken_back(conn: sqlite3.Connection) -> None:
    """Somebody who guessed wrong should be able to say so, and get the
    catalogue's silence back rather than a wrong colour."""
    garden_id, _bed = _garden_with(conn, 1)
    record_colour(conn, garden_id, taxon_id=1, colour="violet")
    record_colour(conn, garden_id, taxon_id=1, colour=None)
    assert observed_colours(conn, garden_id) == {}
    assert garden_palette(conn, garden_id)["beds"][0]["months"][5]["unknown"] == 1


def test_an_observation_overrides_what_the_catalogue_says(
    conn: sqlite3.Connection,
) -> None:
    """Cultivars exist. Somebody standing in front of a white yarrow is a better
    witness for their own garden than a continental average."""
    upsert_trait(
        conn, 2, "flower_colour", source="test", license="CC0", value_text="pink"
    )
    conn.commit()
    garden_id, _bed = _garden_with(conn, 2)
    assert garden_palette(conn, garden_id)["beds"][0]["months"][5]["colours"] == ["pink"]

    record_colour(conn, garden_id, taxon_id=2, colour="white")
    assert garden_palette(conn, garden_id)["beds"][0]["months"][5]["colours"] == ["white"]


def test_a_colour_nobody_can_draw_is_refused(conn: sqlite3.Connection) -> None:
    """The palette maps a fixed vocabulary to swatches. A free string would
    reach the canvas as a dot with no colour."""
    garden_id, _bed = _garden_with(conn, 1)
    with pytest.raises(ValueError, match="colour"):
        record_colour(conn, garden_id, taxon_id=1, colour="knallbunt")


def test_the_endpoint_is_where_the_client_looks(conn: sqlite3.Connection) -> None:
    """The store tests all passed while the route was mounted at
    `/api/v1/gardens/gardens/...` — the router already carries the prefix and it
    was written a second time. Nothing testing the store could see that; only
    something going through the API could.
    """
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
            noted = client.put(
                f"/api/v1/gardens/{token}/colours/1", json={"colour": "violet"}
            )
            assert noted.status_code == 200, noted.json()
            assert noted.json()["observed_colours"] == {"1": "violet"}

            cleared = client.put(
                f"/api/v1/gardens/{token}/colours/1", json={"colour": None}
            )
            assert cleared.json()["observed_colours"] == {}

            refused = client.put(
                f"/api/v1/gardens/{token}/colours/1", json={"colour": "knallbunt"}
            )
            assert refused.status_code == 422
    finally:
        app.dependency_overrides.clear()
