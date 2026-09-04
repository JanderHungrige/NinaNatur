"""The colour endpoint, through the API.

What a hand-entered colour *is* now lives in `test_manual_colours.py`: a `trait`
row marked `manual`, in the shared catalogue, beaten by any published source.
This file is what a client can see of it.
"""
from __future__ import annotations

import sqlite3

import pytest

from ninanatur.bloom.palette import garden_palette
from ninanatur.garden.elements import insert_element
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.observations import record_colour
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


def test_a_hand_entry_reaches_the_plan(conn: sqlite3.Connection) -> None:
    """The point of the feature. Colour is recorded for 590 of 8,939 species,
    so for most of the catalogue this is the only answer there is."""
    garden_id, _bed = _garden_with(conn, 1)
    record_colour(conn, taxon_id=1, colour="violet")

    palette = garden_palette(conn, garden_id)
    june = next(m for m in palette["beds"][0]["months"] if m["month"] == 6)

    assert june["colours"] == ["violet"]
    assert june["unknown"] == 0


def test_it_reaches_every_plan(conn: sqlite3.Connection) -> None:
    """The consequence of the change, stated as a test rather than left to be
    discovered. One person's entry answers for every garden on this server —
    that is what "general database" means, and it is the cost of it."""
    mine, _a = _garden_with(conn, 1)
    yours, _b = _garden_with(conn, 1)
    record_colour(conn, taxon_id=1, colour="violet")

    for garden_id in (mine, yours):
        june = next(
            m for m in garden_palette(conn, garden_id)["beds"][0]["months"]
            if m["month"] == 6
        )
        assert june["colours"] == ["violet"]


def test_a_second_answer_replaces_the_first(conn: sqlite3.Connection) -> None:
    record_colour(conn, taxon_id=1, colour="violet")
    record_colour(conn, taxon_id=1, colour="white")

    from ninanatur.garden.observations import manual_colours

    assert manual_colours(conn) == {1: "white"}


def test_a_colour_nobody_can_draw_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValueError, match="colour"):
        record_colour(conn, taxon_id=1, colour="knallbunt")


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
