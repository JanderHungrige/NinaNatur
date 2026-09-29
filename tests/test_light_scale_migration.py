"""Stored bed light values move onto a new hours->L convention at once (2026-09-21).

A bed's light value is written together with its sun hours, so when the
convention moved — the staircase became lines on EIVE's scale — the new value
follows from what is stored. No garden has to run the slow rebuild for it, and
no map reads stale over it: no shadow moved.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.light_scale import LIGHT_SCALE_KEY, rescale_bed_light
from ninanatur.solar.light import ellenberg_from_sun_hours, light_value
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


def _computed_under_the_staircase(client: TestClient, conn: sqlite3.Connection) -> tuple[str, int]:
    """A garden whose bed was computed at 7.9 h and stored the staircase's rung, 7."""
    token = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.5, "longitude": 13.4}).json()["share_token"]
    bed = client.post(f"/api/v1/gardens/{token}/beds", json={
        "name": "Beet", "polygon": SQUARE, "soil_type": "loam",
        "moisture": "fresh"}).json()["beds"][0]
    client.post(f"/api/v1/gardens/{token}/recompute")
    conn.execute("UPDATE element SET ellenberg_l = 7.0, sun_hours = 7.9 WHERE element_id = ?",
                 (bed["bed_id"],))
    conn.execute("DELETE FROM catalogue_meta WHERE key = ?", (LIGHT_SCALE_KEY,))
    conn.commit()
    return token, int(bed["bed_id"])


def test_a_stored_bed_moves_onto_the_new_scale_from_its_own_hours(
    client: TestClient, conn: sqlite3.Connection,
) -> None:
    token, bed_id = _computed_under_the_staircase(client, conn)

    assert rescale_bed_light(conn) == "moved 1 bed light value(s) onto EIVE's scale"

    bed = next(b for b in client.get(f"/api/v1/gardens/{token}").json()["beds"]
               if b["bed_id"] == bed_id)
    assert bed["ellenberg_l"] == ellenberg_from_sun_hours(7.9) == 8.93
    assert bed["sun_hours"] == 7.9


def test_it_runs_once_and_leaves_a_later_value_alone(
    client: TestClient, conn: sqlite3.Connection,
) -> None:
    _token, bed_id = _computed_under_the_staircase(client, conn)
    rescale_bed_light(conn)
    conn.execute("UPDATE element SET ellenberg_l = 4.0 WHERE element_id = ?", (bed_id,))

    assert rescale_bed_light(conn) is None
    assert conn.execute("SELECT ellenberg_l FROM element WHERE element_id = ?",
                        (bed_id,)).fetchone()[0] == 4.0


def test_a_fresh_database_is_marked_with_nothing_to_move(conn: sqlite3.Connection) -> None:
    assert conn.execute("SELECT value FROM catalogue_meta WHERE key = ?",
                        (LIGHT_SCALE_KEY,)).fetchone()[0] == "0"


def test_the_map_and_the_list_stay_current_across_it(
    client: TestClient, conn: sqlite3.Connection,
) -> None:
    """The convention is no input of the map: no shadow moved, nothing to rebuild."""
    token, bed_id = _computed_under_the_staircase(client, conn)
    rescale_bed_light(conn)

    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is False
    suggestions = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions")
    assert suggestions.json()["light_state"] == "current"


def test_a_bed_stored_with_its_sky_moves_by_both(
    client: TestClient, conn: sqlite3.Connection,
) -> None:
    """Since the sky counts, a bed's value is its hours' floored by the sky it
    sees in leaf (doc 118). The recompute writes both; the rescale reads both."""
    _token, bed_id = _computed_under_the_staircase(client, conn)
    conn.execute("UPDATE element SET sky_view = 0.05 WHERE element_id = ?", (bed_id,))
    rescale_bed_light(conn)
    value = conn.execute("SELECT ellenberg_l FROM element WHERE element_id = ?",
                         (bed_id,)).fetchone()[0]
    assert value == light_value(7.9, 0.05) == 2.5
