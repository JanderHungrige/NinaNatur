"""Wave 20, feature 2: every number has an edge.

Each test here drives the app's own client the way somebody without an account
could, and was red before its fix. None of them reaches the network: the map
import's two outbound calls are replaced by functions that fail the test if
they are ever reached, because a request that should be refused must be refused
*before* it costs anybody anything.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def token(client: TestClient) -> str:
    body = client.post("/api/v1/gardens",
                       json={"name": "G", "latitude": 51.2564, "longitude": 7.1501})
    return str(body.json()["share_token"])


def _raw(client: TestClient, url: str, text: str) -> int:
    """Send JSON text as written, because NaN and Infinity cannot be spelled in
    a Python dict that `json=` would serialise honestly."""
    return client.post(url, content=text,
                       headers={"content-type": "application/json"}).status_code


# --- non-finite numbers: a 422, never a 500, and never stored ---------------

@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_a_non_finite_coordinate_is_refused(client: TestClient, token: str, value: str) -> None:
    status = _raw(client, f"/api/v1/gardens/{token}/obstacles",
                  f'{{"kind": "tree", "x": {value}, "y": 0, "height": 5}}')
    assert status == 422


def test_an_infinite_coordinate_is_never_stored(client: TestClient, token: str) -> None:
    """Stored, it poisons the signature, the extent and every shadow after it."""
    _raw(client, f"/api/v1/gardens/{token}/obstacles",
         '{"kind": "tree", "x": Infinity, "y": 0, "height": 5}')
    assert client.get(f"/api/v1/gardens/{token}").json()["obstacles"] == []


def test_a_non_finite_polygon_point_is_refused(client: TestClient, token: str) -> None:
    status = _raw(client, f"/api/v1/gardens/{token}/beds",
                  '{"name": "B", "polygon": [[0,0],[4,0],[4,NaN],[0,4]]}')
    assert status == 422


# --- distances: a garden is not ten kilometres across -----------------------

def test_a_coordinate_far_outside_any_garden_is_refused(client: TestClient, token: str) -> None:
    """At x = 1e9 the light grid spans a billion metres, and `POST /light`
    stopped answering: one request, no account."""
    r = client.post(f"/api/v1/gardens/{token}/obstacles",
                    json={"kind": "tree", "x": 1e9, "y": 0, "height": 5})
    assert r.status_code == 422


def test_a_far_polygon_point_is_refused(client: TestClient, token: str) -> None:
    r = client.post(f"/api/v1/gardens/{token}/beds",
                    json={"name": "B", "polygon": [[0, 0], [4, 0], [1e9, 4], [0, 4]]})
    assert r.status_code == 422


def test_a_placement_far_outside_the_bed_is_refused(client: TestClient, token: str) -> None:
    from ninanatur.api.schemas import PlantingPlacement
    with pytest.raises(ValueError):
        PlantingPlacement(x=1e9, y=0)


# --- lengths ------------------------------------------------------------------

def test_a_bed_with_ten_thousand_corners_is_refused(client: TestClient, token: str) -> None:
    polygon = [[float(i % 100), float(i // 100)] for i in range(10_000)]
    r = client.post(f"/api/v1/gardens/{token}/beds", json={"name": "B", "polygon": polygon})
    assert r.status_code == 422


# --- the map import: refused before it asks anybody -------------------------

@pytest.fixture()
def no_outbound(monkeypatch: pytest.MonkeyPatch) -> None:
    from ninanatur.api import geo

    def refuse(*_a: object, **_k: object) -> object:
        raise AssertionError("an oversized outline reached Overpass")

    monkeypatch.setattr(geo, "buildings_in", refuse)
    monkeypatch.setattr(geo, "streets_in", refuse)


def test_an_outline_across_half_of_germany_is_refused(
    client: TestClient, no_outbound: None
) -> None:
    """Reproduced: a three-point outline across the country sent Overpass a
    bounding box over half the republic and held the server for 41 seconds."""
    outline = [{"lat": 48.0, "lon": 7.0}, {"lat": 54.0, "lon": 7.0}, {"lat": 51.0, "lon": 14.0}]
    r = client.post("/api/v1/gardens/from-map", json={"name": "G", "outline": outline})
    assert r.status_code == 422


def test_an_outline_with_thousands_of_points_is_refused(
    client: TestClient, no_outbound: None
) -> None:
    outline = [{"lat": 51.25 + i * 1e-6, "lon": 7.15} for i in range(5_000)]
    r = client.post("/api/v1/gardens/from-map", json={"name": "G", "outline": outline})
    assert r.status_code == 422


# --- the one computation that scales with the drawing -----------------------

def test_the_light_grid_refuses_a_garden_too_large_to_compute() -> None:
    """Bounds on the inputs are the first line; this is the second. Whatever
    reaches `compute_grid`, it answers "too large" rather than running."""
    from ninanatur.garden.lightgrid import GardenTooLarge, check_extent
    with pytest.raises(GardenTooLarge):
        check_extent(0.0, 0.0, 20_000.0, 20_000.0)


def test_the_largest_legitimate_garden_still_fits() -> None:
    from ninanatur.garden.lightgrid import check_extent
    check_extent(-600.0, -600.0, 600.0, 600.0)


# --- the body itself ----------------------------------------------------------

def test_an_oversized_body_is_refused_before_it_is_read(client: TestClient, token: str) -> None:
    """A 2.8 MB bed polygon used to be parsed in full before anything checked it."""
    padding = " " * 1_100_000
    status = _raw(client, f"/api/v1/gardens/{token}/beds",
                  '{"name": "B", "polygon": [[0,0],[4,0],[4,4]]' + padding + "}")
    assert status == 413
