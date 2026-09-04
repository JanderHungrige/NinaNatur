"""Where a cluster sits, and what colour it is.

Wave 15, feature 6. A planting *is* a cluster — `UNIQUE (element_id, taxon_id)`
means one row per species per bed — so a cluster's position is a column on the
planting, and copying a species into a bed it is already in raises the count
rather than starting a second patch of it.
"""
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    connection.execute(
        "INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Salvia pratensis')"
    )
    connection.execute(
        "INSERT INTO taxon (taxon_id, canonical_name) VALUES (2, 'Achillea millefolium')"
    )
    connection.commit()
    yield connection


@pytest.fixture()
def client(conn: sqlite3.Connection) -> Iterator[TestClient]:
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _garden(client: TestClient) -> tuple[str, int]:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    bed = client.post(
        f"/api/v1/gardens/{token}/beds", json={"name": "Beet A", "polygon": SQUARE}
    ).json()["beds"][0]
    return token, int(bed["bed_id"])


def _plant(client: TestClient, token: str, bed_id: int, taxon_id: int, n: int = 1) -> int:
    body = client.post(
        f"/api/v1/gardens/{token}/beds/{bed_id}/plantings",
        json={"taxon_id": taxon_id, "quantity": n},
    ).json()
    bed = next(b for b in body["beds"] if b["bed_id"] == bed_id)
    return int(next(p for p in bed["plantings"] if p["taxon_id"] == taxon_id)["planting_id"])


# --- a cluster has a place -------------------------------------------------

def test_a_new_planting_has_no_position_of_its_own(client: TestClient) -> None:
    """Null, not 0,0. Defaulting to the origin would stack every planting in one
    corner of the bed; null means "nobody has moved this", and the plan derives
    somewhere sensible from the id."""
    token, bed_id = _garden(client)
    _plant(client, token, bed_id, 1)

    bed = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    assert bed["plantings"][0]["x"] is None
    assert bed["plantings"][0]["y"] is None


def test_a_cluster_can_be_put_somewhere_and_stays(client: TestClient) -> None:
    token, bed_id = _garden(client)
    planting_id = _plant(client, token, bed_id, 1)

    response = client.patch(
        f"/api/v1/gardens/{token}/plantings/{planting_id}", json={"x": 1.5, "y": 2.25}
    )

    assert response.status_code == 200
    bed = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    assert (bed["plantings"][0]["x"], bed["plantings"][0]["y"]) == (1.5, 2.25)


def test_a_planting_in_another_garden_cannot_be_moved(client: TestClient) -> None:
    """The token is the whole of a garden's access control, and a bare planting
    id is enumerable. Reached through its garden or not at all."""
    token, bed_id = _garden(client)
    planting_id = _plant(client, token, bed_id, 1)
    other, _ = _garden(client)

    response = client.patch(
        f"/api/v1/gardens/{other}/plantings/{planting_id}", json={"x": 1.0, "y": 1.0}
    )

    assert response.status_code == 404


def test_a_position_outside_the_bed_is_accepted(client: TestClient) -> None:
    """Deliberately. The plan clamps a drag to the outline, but a bed can be
    reshaped afterwards, and a stored position that was inside can end up
    outside. Refusing it here would mean a bed could not be made smaller
    without first moving everything in it."""
    token, bed_id = _garden(client)
    planting_id = _plant(client, token, bed_id, 1)

    response = client.patch(
        f"/api/v1/gardens/{token}/plantings/{planting_id}", json={"x": 99.0, "y": 99.0}
    )

    assert response.status_code == 200


# --- copying ---------------------------------------------------------------

def test_copying_into_another_bed_makes_a_second_cluster(client: TestClient) -> None:
    token, first = _garden(client)
    second = int(
        client.post(
            f"/api/v1/gardens/{token}/beds",
            json={"name": "Beet B", "polygon": [[10, 0], [16, 0], [16, 4], [10, 4]]},
        ).json()["beds"][-1]["bed_id"]
    )
    _plant(client, token, first, 1, 3)

    _plant(client, token, second, 1, 3)

    beds = {b["bed_id"]: b for b in client.get(f"/api/v1/gardens/{token}").json()["beds"]}
    assert len(beds[first]["plantings"]) == 1
    assert len(beds[second]["plantings"]) == 1
    assert beds[first]["plantings"][0]["planting_id"] != (
        beds[second]["plantings"][0]["planting_id"]
    )


def test_copying_into_the_same_bed_grows_the_cluster(client: TestClient) -> None:
    """Not a second patch of the same species a metre away. The table says one
    row per species per bed, and that is what a gardener means by planting more
    of something: the patch gets bigger."""
    token, bed_id = _garden(client)
    _plant(client, token, bed_id, 1, 3)

    _plant(client, token, bed_id, 1, 2)

    bed = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    assert len(bed["plantings"]) == 1
    assert bed["plantings"][0]["quantity"] == 5


# --- colour, per cluster ---------------------------------------------------

def test_the_palette_says_which_cluster_is_which_colour(client: TestClient) -> None:
    """The old palette answered per bed — a set of colours and a count of
    unknowns — which is all a colour band needed. A dot per cluster needs to
    know which cluster."""
    token, bed_id = _garden(client)
    first = _plant(client, token, bed_id, 1)
    second = _plant(client, token, bed_id, 2)

    palette = client.get(f"/api/v1/gardens/{token}/bloom").json()
    bed = next(b for b in palette["beds"] if b["bed_id"] == bed_id)

    listed = {p["planting_id"] for p in bed["plantings"]}
    assert listed == {first, second}


def test_a_cluster_carries_the_months_it_flowers_in(client: TestClient) -> None:
    token, bed_id = _garden(client)
    planting_id = _plant(client, token, bed_id, 1)

    palette = client.get(f"/api/v1/gardens/{token}/bloom").json()
    entry = next(
        p for p in palette["beds"][0]["plantings"] if p["planting_id"] == planting_id
    )

    assert "colour" in entry, "null is an answer: the catalogue often has none"
    assert isinstance(entry["months"], list)
    assert "space_m2" in entry, "a cluster is sized from this"


def test_the_room_a_cluster_claims_is_null_when_nothing_is_known(
    client: TestClient,
) -> None:
    """The catalogue records no spread at all and knows a height for 44% of
    species, so this is null more often than not. The plan must draw a cluster
    either way — and never print the number, because it is estimated from
    height and would read as measured."""
    token, bed_id = _garden(client)
    _plant(client, token, bed_id, 1)

    entry = client.get(f"/api/v1/gardens/{token}/bloom").json()["beds"][0]["plantings"][0]

    assert entry["space_m2"] is None, "the fixture taxon carries no height"
