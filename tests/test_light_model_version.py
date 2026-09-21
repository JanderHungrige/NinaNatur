"""A new hours->L convention makes every stored map read stale once (2026-09-21).

A bed keeps the light value it was computed with until somebody presses the
button. When the convention moves — the staircase became lines on EIVE's scale —
every stored value is on the old one, so the map and the bed's suggestions must
both say so, and pressing the button must make them current again.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from extent_builders import PLOT, garden_with
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.garden import lightgrid
from ninanatur.garden.light_state import current_signature
from ninanatur.garden.lightgrid import signature_of
from ninanatur.garden.store import load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.light import LIGHT_MODEL, ellenberg_from_sun_hours
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    yield connection


@pytest.fixture()
def client(conn: sqlite3.Connection) -> Iterator[TestClient]:
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_the_signature_carries_the_light_model(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whoever next changes the convention raises one number, and every stored
    map says it is out of date — no list of maps to remember."""
    garden = load_garden(conn, garden_with(conn, PLOT))
    before = signature_of(garden)

    monkeypatch.setattr(lightgrid, "LIGHT_MODEL", LIGHT_MODEL + 1)

    assert signature_of(garden) != before


def _computed_under_the_staircase(
    client: TestClient, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> tuple[str, int]:
    """A garden whose map and beds were computed under convention 1."""
    token = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.5, "longitude": 13.4}).json()["share_token"]
    bed = client.post(f"/api/v1/gardens/{token}/beds", json={
        "name": "Beet", "polygon": SQUARE, "soil_type": "loam",
        "moisture": "fresh"}).json()["beds"][0]
    with monkeypatch.context() as old:
        old.setattr(lightgrid, "LIGHT_MODEL", 1)
        client.post(f"/api/v1/gardens/{token}/recompute")
    # And the value the staircase gave an open bed: its top rung, 8.
    conn.execute("UPDATE element SET ellenberg_l = 8.0 WHERE element_id = ?",
                 (bed["bed_id"],))
    conn.commit()
    return token, int(bed["bed_id"])


def test_a_map_from_the_old_convention_reads_stale_in_the_map_and_the_list(
    client: TestClient, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    token, bed_id = _computed_under_the_staircase(client, conn, monkeypatch)

    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is True
    suggestions = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions")
    assert suggestions.json()["light_state"] == "stale"


def test_one_press_makes_it_current_and_moves_the_bed_onto_the_new_scale(
    client: TestClient, conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stale once, not for ever — and the value the list ranks by afterwards is
    the one the new convention gives the bed's own hours."""
    token, bed_id = _computed_under_the_staircase(client, conn, monkeypatch)

    garden = client.post(f"/api/v1/gardens/{token}/recompute").json()

    bed = next(b for b in garden["beds"] if b["bed_id"] == bed_id)
    assert bed["ellenberg_l"] == ellenberg_from_sun_hours(bed["sun_hours"])
    assert bed["ellenberg_l"] != 8.0, "an open bed is 9.0 on EIVE's scale"
    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is False
    suggestions = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions")
    assert suggestions.json()["light_state"] == "current"
    stored = conn.execute("SELECT signature FROM light_grid").fetchone()[0]
    garden_id = int(conn.execute("SELECT garden_id FROM garden").fetchone()[0])
    assert stored == current_signature(conn, load_garden(conn, garden_id))
