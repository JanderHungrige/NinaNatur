"""What a garden made from the map brings with it, and how it is credited.

From the integration review of the owner's check (2026-09-21): a building whose
corners merge once rounded failed the whole import after the garden was stored;
a plot like that did the same; and OpenStreetMap's credit was inferred from a
house's height and roof, so a map house the gardener corrected lost it.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import geo as geo_routes
from ninanatur.api.deps import get_connection
from ninanatur.garden.elements import insert_element
from ninanatur.garden.store import create_garden
from ninanatur.geo.projection import LatLon
from ninanatur.geo.surroundings import OsmBuilding
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.outline_provenance import OUTLINE_SOURCE_KEY, mark_map_outlines
from ninanatur.web.app import app

PLOT = [{"lat": 52.5, "lon": 13.4}, {"lat": 52.5004, "lon": 13.4},
        {"lat": 52.5004, "lon": 13.4006}]
#: Just south of the plot and tall enough to reach it.
NEAR = LatLon(lat=52.49985, lon=13.40020)


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    yield connection


@pytest.fixture()
def client(conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(geo_routes, "streets_in", lambda *a, **k: [])
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _import(client: TestClient, monkeypatch: pytest.MonkeyPatch, buildings: list[OsmBuilding],
            outline: list[dict[str, float]] = PLOT) -> Any:
    monkeypatch.setattr(geo_routes, "buildings_in", lambda *a, **k: buildings)
    return client.post("/api/v1/gardens/from-map", json={"name": "Karte", "outline": outline})


def _houses(made: Any) -> list[dict[str, Any]]:
    return [o for o in made.json()["garden"]["obstacles"] if o["kind"] == "house"]


def test_a_building_whose_corners_merge_arrives_as_its_square(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """[A, B, A] covers no ground. It used to fail the import after the garden,
    its plot and its streets were committed; the reach filter had already judged
    the building by its equal-area square, so that is what it becomes."""
    flat = OsmBuilding(1, NEAR, [NEAR, LatLon(lat=52.49985, lon=13.40030), NEAR],
                       {"building": "house", "height": "12"})
    made = _import(client, monkeypatch, [flat])
    assert made.status_code == 201, made.text
    [house] = _houses(made)
    assert house["constraint_hint"] == "rect"
    assert house["outline_source"] == "osm"


def test_a_plot_whose_corners_merge_is_refused_before_anything_is_stored(
    client: TestClient, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    same = {"lat": 52.5, "lon": 13.4}
    made = _import(client, monkeypatch, [], outline=[same, same, {"lat": 52.5004, "lon": 13.4}])
    assert made.status_code == 422
    assert conn.execute("SELECT COUNT(*) FROM garden").fetchone()[0] == 0


def test_every_outline_the_import_brings_is_marked_as_the_maps(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    corners = [LatLon(lat=52.49980, lon=13.40010), LatLon(lat=52.49980, lon=13.40030),
               LatLon(lat=52.49990, lon=13.40030), LatLon(lat=52.49990, lon=13.40010)]
    made = _import(client, monkeypatch, [OsmBuilding(2, NEAR, corners, {"building": "house"})])
    assert made.status_code == 201, made.text
    [house] = _houses(made)
    assert house["outline_source"] == "osm"
    plot = [o for o in made.json()["garden"]["obstacles"] if o["kind"] == "garden"]
    assert plot[0]["outline_source"] is None, "the gardener drew the plot on the map"


def test_a_corrected_map_house_keeps_openstreetmaps_credit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gardener types the height and picks the roof. The outline the plan
    draws is still OpenStreetMap's, and so is the credit under it."""
    corners = [LatLon(lat=52.49980, lon=13.40010), LatLon(lat=52.49980, lon=13.40030),
               LatLon(lat=52.49990, lon=13.40030), LatLon(lat=52.49990, lon=13.40010)]
    made = _import(client, monkeypatch, [OsmBuilding(3, NEAR, corners, {"building": "house"})])
    token = made.json()["garden"]["share_token"]
    [house] = _houses(made)
    edited = client.patch(f"/api/v1/gardens/{token}/obstacles/{house['obstacle_id']}",
                          json={"height": 7.0, "roof": "gable"})
    assert edited.status_code == 200, edited.text
    assert [c["about"] for c in client.get(f"/api/v1/gardens/{token}/sources").json()] == ["map"]


def test_the_backfill_marks_what_the_import_left_and_nothing_drawn(
    conn: sqlite3.Connection,
) -> None:
    conn.execute("DELETE FROM catalogue_meta WHERE key = ?", (OUTLINE_SOURCE_KEY,))
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    box = [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]
    imported = insert_element(conn, garden_id, kind="house", shape="polygon", x=0.0, y=0.0,
                              points=box, height=7.0, height_source="assumed", roof_source="osm")
    street = insert_element(conn, garden_id, kind="street", shape="line", x=0.0, y=-9.0,
                            points=[[0.0, 0.0], [20.0, 0.0]], width=6.0)
    drawn = insert_element(conn, garden_id, kind="house", shape="polygon", x=20.0, y=0.0,
                           points=box, height=8.0, height_source="user")
    conn.commit()

    assert mark_map_outlines(conn) == "marked 2 outline(s) as OpenStreetMap's"
    sources = dict(conn.execute("SELECT element_id, outline_source FROM element").fetchall())
    assert sources == {imported: "osm", street: "osm", drawn: None}
    assert mark_map_outlines(conn) is None, "once"
