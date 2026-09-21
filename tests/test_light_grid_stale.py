"""A map laid over the old box says it is out of date (owner #6).

The grid stopped covering the neighbours' land on 2026-09-21. A map stored
before that is a 3 m grid over the whole neighbourhood, and it has to say so —
otherwise the owner never sees "neu berechnen" and never gets the finer one.
"""
from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator

import pytest
from extent_builders import PLOT, garden_with, neighbour, rect
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.garden import lightgrid_extent
from ninanatur.garden.lightgrid import signature_of
from ninanatur.garden.models import Garden
from ninanatur.garden.store import load_garden
from ninanatur.garden.terrain_sync import ground_for, horizon_for
from ninanatur.geo.projection import LatLon
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app


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


def _signature_before_2026_09_21(
    garden: Garden, ground: object, horizon: object
) -> str:
    """`signature_of` as it was when every stored map was computed."""
    parts = [f"{garden.latitude:.5f},{garden.longitude:.5f}"]
    parts.append(f"ground|{getattr(ground, 'source', None)}"
                 f"|{getattr(ground, 'vertical_step_m', None)}")
    ring = list(horizon) if isinstance(horizon, list) else []
    parts.append("horizon|" + ",".join(f"{angle:.2f}" for angle in ring))
    for e in sorted(garden.elements, key=lambda e: e.element_id):
        outline = ";".join(f"{x:.2f},{y:.2f}" for x, y in e.footprint)
        parts.append(f"{e.element_id}|{e.kind}|{e.height}|{e.roof}|{e.eaves_m}"
                     f"|{e.roof_fall_deg}|{e.height_above_ground}|{outline}")
        parts.extend(f"p{p.planting_id}|{p.taxon_id}|{p.quantity}|{p.x}|{p.y}"
                     for p in e.plantings)
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def test_a_map_stored_before_the_change_reads_stale(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    token = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.5171, "longitude": 13.3889}).json()["share_token"]
    client.post(f"/api/v1/gardens/{token}/beds",
                json={"name": "Beet", "polygon": rect(0.0, 0.0, 6.0, 4.0)})
    client.post(f"/api/v1/gardens/{token}/light")
    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is False

    garden_id = int(conn.execute("SELECT garden_id FROM garden").fetchone()[0])
    garden = load_garden(conn, garden_id)
    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    old = _signature_before_2026_09_21(
        garden, ground_for(conn, anchor), horizon_for(conn, anchor))
    conn.execute("UPDATE light_grid SET signature = ?", (old,))
    conn.commit()

    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is True


@pytest.mark.parametrize(
    ("name", "value"),
    [("EXTENT_RULE", 99), ("GRID_MARGIN_M", 2.0), ("GRID_BUDGET_S", 10.0),
     ("CELL_LADDER_M", (1.0, 2.0))],
)
def test_a_change_to_the_grid_rule_stales_every_map(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, name: str, value: object
) -> None:
    """Whoever next changes what the grid covers or how fine it is does not have
    to remember that stored maps exist."""
    garden = load_garden(conn, garden_with(conn, PLOT))
    before = signature_of(garden)

    monkeypatch.setattr(lightgrid_extent, name, value)

    assert signature_of(garden) != before


def test_making_a_neighbours_house_your_own_stales_the_map(
    conn: sqlite3.Connection,
) -> None:
    """Same outline, same height: only where it came from changed, and with it
    the box the grid covers."""
    garden_id = garden_with(conn, PLOT)
    house = neighbour(conn, garden_id, rect(60.0, 10.0, 70.0, 20.0))
    before = signature_of(load_garden(conn, garden_id))

    conn.execute("UPDATE element SET height_source = 'user', roof_source = 'user'"
                 " WHERE element_id = ?", (house,))
    conn.commit()

    assert signature_of(load_garden(conn, garden_id)) != before


def test_a_neighbours_provenance_alone_does_not_stale_the_map(
    conn: sqlite3.Connection,
) -> None:
    """A survey writing `surveyed` over `osm` leaves it a neighbour's house,
    outside the box — nothing the grid covers moved."""
    garden_id = garden_with(conn, PLOT)
    house = neighbour(conn, garden_id, rect(60.0, 10.0, 70.0, 20.0))
    before = signature_of(load_garden(conn, garden_id))

    conn.execute("UPDATE element SET height_source = 'surveyed',"
                 " roof_source = 'surveyed' WHERE element_id = ?", (house,))
    conn.commit()

    assert signature_of(load_garden(conn, garden_id)) == before
