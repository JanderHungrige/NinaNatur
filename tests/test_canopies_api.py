"""A tree suggestion's three fates, through the API."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.garden.canopies_found import remember
from ninanatur.geo.canopy import Canopy
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _garden(client: TestClient) -> tuple[str, sqlite3.Connection]:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 51.0, "longitude": 6.0}
    ).json()["share_token"]
    conn = app.dependency_overrides[get_connection]()
    garden_id = conn.execute(
        "SELECT garden_id FROM garden WHERE share_token = ?", (token,)
    ).fetchone()[0]
    remember(conn, garden_id, [
        Canopy(x=8.0, y=-6.0, radius_m=4.0, height_m=18.0),
        Canopy(x=-12.0, y=4.0, radius_m=2.5, height_m=9.0),
    ])
    return token, conn


def test_the_suggestions_come_back_tallest_first(client: TestClient) -> None:
    token, _ = _garden(client)

    body = client.get(f"/api/v1/gardens/{token}/canopies").json()

    assert [c["height_m"] for c in body] == [18.0, 9.0]


def test_accepting_one_puts_a_tree_on_the_plan(client: TestClient) -> None:
    token, _ = _garden(client)
    first = client.get(f"/api/v1/gardens/{token}/canopies").json()[0]

    garden = client.post(
        f"/api/v1/gardens/{token}/canopies/{first['suggestion_id']}"
    ).json()

    trees = [o for o in garden["obstacles"] if o["kind"] == "tree"]
    assert len(trees) == 1
    assert trees[0]["height"] == pytest.approx(18.0)
    assert trees[0]["height_source"] == "measured", "it is a measurement, and says so"


def test_an_accepted_suggestion_is_not_offered_again(client: TestClient) -> None:
    token, _ = _garden(client)
    first = client.get(f"/api/v1/gardens/{token}/canopies").json()[0]

    client.post(f"/api/v1/gardens/{token}/canopies/{first['suggestion_id']}")

    left = client.get(f"/api/v1/gardens/{token}/canopies").json()
    assert [c["height_m"] for c in left] == [9.0]


def test_a_dismissed_one_stays_dismissed(client: TestClient) -> None:
    """Remembered rather than deleted: the next recomputation finds the same
    tree again, and re-proposing something somebody rejected is how a suggestion
    becomes a nuisance."""
    token, conn = _garden(client)
    first = client.get(f"/api/v1/gardens/{token}/canopies").json()[0]

    assert client.delete(
        f"/api/v1/gardens/{token}/canopies/{first['suggestion_id']}"
    ).status_code == 204

    garden_id = conn.execute("SELECT garden_id FROM garden").fetchone()[0]
    remember(conn, garden_id, [Canopy(x=8.2, y=-6.1, radius_m=4.0, height_m=18.1)])

    left = client.get(f"/api/v1/gardens/{token}/canopies").json()
    assert [c["height_m"] for c in left] == [9.0], "it came back"


def test_a_suggestion_that_moved_a_little_is_the_same_tree(client: TestClient) -> None:
    """A crown's centroid moves when its edge cells change, and they change with
    the season the flight was made in. A fresh fetch will not reproduce it."""
    token, conn = _garden(client)
    garden_id = conn.execute("SELECT garden_id FROM garden").fetchone()[0]

    added = remember(conn, garden_id, [Canopy(x=9.5, y=-7.0, radius_m=4.1, height_m=18.2)])

    assert added == 0
    assert len(client.get(f"/api/v1/gardens/{token}/canopies").json()) == 2


def test_a_suggestion_that_is_not_there_is_a_404(client: TestClient) -> None:
    token, _ = _garden(client)

    assert client.post(f"/api/v1/gardens/{token}/canopies/9999").status_code == 404
    assert client.delete(f"/api/v1/gardens/{token}/canopies/9999").status_code == 404


def test_a_garden_that_was_never_measured_has_no_suggestions(client: TestClient) -> None:
    token = client.post(
        "/api/v1/gardens", json={"name": "leer", "latitude": 51.0, "longitude": 6.0}
    ).json()["share_token"]

    assert client.get(f"/api/v1/gardens/{token}/canopies").json() == []
