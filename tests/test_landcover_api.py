"""The land around a garden through the API (doc 114): fetched when a garden is
made from the map, read back without a request, and credited.

Overpass is stubbed where the fetch looks it up (`landcover_sync`); conftest
answers "nothing mapped" for every test that does not say otherwise.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import nullcontext
from typing import Any, get_args

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import geo as geo_routes
from ninanatur.api.deps import get_connection
from ninanatur.api.landcover import LandKind
from ninanatur.garden import landcover_sync
from ninanatur.geo.landcover_clip import LANDCOVER_MARGIN_M, LandArea
from ninanatur.geo.landcover_store import save_landcover
from ninanatur.geo.osm_landcover import LANDCOVER, OsmArea
from ninanatur.geo.projection import LatLon, Metres, centroid, to_latlon
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

# About 20 x 20 m near Kleinmachnow. Its centre rounds to four places 3 m east
# and 1 m south of where it is — which is what the exact anchor is for.
OUTLINE = [
    {"lat": 52.4055, "lon": 13.2100},
    {"lat": 52.4055, "lon": 13.21029},
    {"lat": 52.40568, "lon": 13.21029},
    {"lat": 52.40568, "lon": 13.2100},
]
EXACT = centroid([LatLon(p["lat"], p["lon"]) for p in OUTLINE])


def _square_at(x: float, y: float, anchor: LatLon, half: float = 5.0) -> list[LatLon]:
    """A square in degrees, centred `x, y` metres from `anchor`."""
    return [to_latlon(Metres(x + dx, y + dy), anchor)
            for dx, dy in ((-half, -half), (half, -half), (half, half), (-half, half))]


@pytest.fixture()
def conn(monkeypatch: pytest.MonkeyPatch) -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    monkeypatch.setattr(geo_routes, "buildings_in", lambda *_a, **_k: [])
    monkeypatch.setattr(geo_routes, "streets_in", lambda *_a, **_k: [])
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


def _from_map(client: TestClient) -> str:
    made = client.post("/api/v1/gardens/from-map", json={"name": "Umgebung", "outline": OUTLINE})
    assert made.status_code == 201, made.text
    return str(made.json()["garden"]["share_token"])


def test_an_unknown_garden_has_no_surroundings(conn: sqlite3.Connection) -> None:
    """404, never 403, like every read by token."""
    assert TestClient(app).get("/api/v1/gardens/gibtesnicht/landcover").status_code == 404


def test_a_garden_with_none_is_empty_and_still_names_the_map(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.5171, "longitude": 13.3889}).json()["share_token"]
    body = client.get(f"/api/v1/gardens/{token}/landcover").json()
    assert body == {"areas": [], "attribution": "© OpenStreetMap-Mitwirkende",
                    "licence": "ODbL-1.0"}


def test_a_garden_from_the_map_arrives_with_its_surroundings(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Placed from the exact centre of the outline — the anchor the streets and
    houses were placed by — not the rounded one the database keeps."""
    asked: list[dict[str, Any]] = []

    def landcover(*box: float, centre: LatLon, **_k: Any) -> list[OsmArea]:
        asked.append({"box": box, "centre": centre})
        return [OsmArea(osm_id=1, kind="wood", outers=[_square_at(40.0, 0.0, EXACT)], inners=[])]

    monkeypatch.setattr(landcover_sync, "landcover_in", landcover)
    # After the answer, on a connection of its own: here, the test's.
    monkeypatch.setattr(landcover_sync, "background_connection", lambda: nullcontext(conn))
    client = TestClient(app)
    token = _from_map(client)

    [call] = asked
    assert call["centre"] == EXACT
    south, _west, north, _east = call["box"]
    # The plot's 20 m and the margin on each side.
    assert (north - south) * 111_320 == pytest.approx(20 + 2 * LANDCOVER_MARGIN_M, abs=0.5)
    [area] = client.get(f"/api/v1/gardens/{token}/landcover").json()["areas"]
    assert area["kind"] == "wood"
    [ring] = area["rings"]
    xs = [p[0] for p in ring]
    assert (min(xs) + max(xs)) / 2 == pytest.approx(40.0, abs=0.15)
    assert conn.execute("SELECT placed_by FROM garden_landcover").fetchone()[0] == "map"


def test_a_refusal_costs_the_colours_not_the_garden(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def refuse(*_a: Any, **_k: Any) -> list[OsmArea]:
        calls["n"] += 1
        raise RuntimeError("Overpass sagt nein")

    monkeypatch.setattr(landcover_sync, "landcover_in", refuse)
    # After the answer, on a connection of its own: here, the test's. Without
    # it the refusal was never asked for, and this test passed on anything.
    monkeypatch.setattr(landcover_sync, "background_connection", lambda: nullcontext(conn))
    client = TestClient(app)
    token = _from_map(client)
    assert calls["n"] == 1, "the import asked, after its answer"
    assert client.get(f"/api/v1/gardens/{token}").status_code == 200
    assert client.get(f"/api/v1/gardens/{token}/landcover").json()["areas"] == []
    # Nothing is kept; the garden is left alone for a while before it is asked
    # for again, and the rebuild within that pause does not ask.
    assert conn.execute("SELECT count(*) FROM garden_landcover").fetchone()[0] == 0
    client.post(f"/api/v1/gardens/{token}/light")
    assert calls["n"] == 1


def test_reading_them_reaches_no_network(conn: sqlite3.Connection,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)
    token = _from_map(client)

    def refuse(*_a: Any, **_k: Any) -> list[OsmArea]:
        raise AssertionError("a page load asked Overpass")

    monkeypatch.setattr(landcover_sync, "landcover_in", refuse)
    assert client.get(f"/api/v1/gardens/{token}/landcover").status_code == 200


def _sources(client: TestClient, token: str) -> list[str]:
    return [c["name"] for c in client.get(f"/api/v1/gardens/{token}/sources").json()]


def test_openstreetmap_is_credited_where_its_land_is_drawn(conn: sqlite3.Connection) -> None:
    """A garden drawn by hand, whose rebuild brought it surroundings: ODbL asks
    for the credit wherever the map's data is shown (doc 106)."""
    client = TestClient(app)
    token = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.5171, "longitude": 13.3889}).json()["share_token"]
    garden_id = conn.execute("SELECT garden_id FROM garden").fetchone()[0]
    assert "OpenStreetMap" not in _sources(client, token)

    save_landcover(conn, garden_id, [], "anchor")
    assert "OpenStreetMap" not in _sources(client, token), "nothing drawn, nothing owed"

    save_landcover(conn, garden_id, [LandArea("field", [[(0, 0), (9, 0), (9, 9)]])], "anchor")
    assert "OpenStreetMap" in _sources(client, token)


def test_the_page_knows_every_class_the_server_draws() -> None:
    """The response's kinds are the page's type; the table is what writes them."""
    assert set(get_args(LandKind)) == set(LANDCOVER.values())
