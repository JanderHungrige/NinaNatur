"""The garden API — addressed by capability, not by id."""
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
BERLIN = {"name": "Testgarten", "latitude": 52.52, "longitude": 13.40}


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _new_garden(client: TestClient) -> str:
    response = client.post("/api/v1/gardens", json=BERLIN)
    assert response.status_code == 201
    return response.json()["share_token"]


# --- addressing -----------------------------------------------------------

def test_a_garden_is_addressed_by_token_never_by_id(client: TestClient) -> None:
    """An id is enumerable; the token is the capability."""
    body = client.post("/api/v1/gardens", json=BERLIN).json()
    assert "share_token" in body
    assert "garden_id" not in body


def test_an_unknown_token_is_404_not_403(client: TestClient) -> None:
    """403 would confirm the token exists — the one thing it must hide.

    A real token is fetched in the same test, so this cannot pass merely because
    the route is missing.
    """
    real = _new_garden(client)
    assert client.get(f"/api/v1/gardens/{real}").status_code == 200
    assert client.get("/api/v1/gardens/not-a-real-token").status_code == 404


def test_two_gardens_do_not_share_a_token(client: TestClient) -> None:
    assert _new_garden(client) != _new_garden(client)


# --- creation and validation ----------------------------------------------

def test_the_stored_location_is_rounded(client: TestClient) -> None:
    token = client.post(
        "/api/v1/gardens",
        json={"name": "Präzise", "latitude": 52.5170365, "longitude": 13.3888599},
    ).json()["share_token"]
    body = client.get(f"/api/v1/gardens/{token}").json()
    assert (body["latitude"], body["longitude"]) == (52.5, 13.4)


def test_an_impossible_latitude_is_422(client: TestClient) -> None:
    """The solar code would happily compute a sun path for latitude 500."""
    bad = client.post("/api/v1/gardens", json={**BERLIN, "latitude": 500})
    assert bad.status_code == 422


def test_a_degenerate_polygon_is_422_with_its_reason(client: TestClient) -> None:
    token = _new_garden(client)
    response = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "Linie", "polygon": [[0, 0], [1, 1]]},
    )
    assert response.status_code == 422
    assert "at least" in response.json()["detail"]


def test_an_unknown_soil_type_is_422_not_silently_defaulted(client: TestClient) -> None:
    token = _new_garden(client)
    response = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "Beet", "polygon": SQUARE, "soil_type": "concrete", "moisture": "fresh"},
    )
    assert response.status_code == 422


# --- the wave's actual point ----------------------------------------------

def test_adding_an_obstacle_recomputes_light_without_a_second_call(
    client: TestClient,
) -> None:
    """Otherwise a plan shows values that no longer match its own obstacles."""
    token = _new_garden(client)
    client.post(f"/api/v1/gardens/{token}/beds", json={"name": "Beet", "polygon": SQUARE})
    client.post(f"/api/v1/gardens/{token}/recompute")
    before = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["sun_hours"]

    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "building", "x": 2, "y": -4, "radius": 10, "height": 12},
    )
    after = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    assert after["sun_hours"] < before
    assert after["light_computed_at"] is not None


def test_a_bed_without_computed_light_reports_null_not_zero(client: TestClient) -> None:
    token = _new_garden(client)
    client.post(f"/api/v1/gardens/{token}/beds", json={"name": "Neu", "polygon": SQUARE})
    bed = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    assert "ellenberg_l" in bed
    assert bed["ellenberg_l"] is None


def test_soil_becomes_site_axes_the_user_never_typed(client: TestClient) -> None:
    token = _new_garden(client)
    client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "Beet", "polygon": SQUARE, "soil_type": "sand", "moisture": "dry"},
    )
    bed = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    assert bed["ellenberg_m"] == 2.5
    assert bed["ellenberg_r"] == 4.0


def test_deleting_a_garden_makes_its_token_stop_working(client: TestClient) -> None:
    token = _new_garden(client)
    assert client.delete(f"/api/v1/gardens/{token}").status_code == 204
    assert client.get(f"/api/v1/gardens/{token}").status_code == 404


def test_healthz_is_unaffected_by_any_of_this(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200
