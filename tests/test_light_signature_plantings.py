"""Only a planting that casts a shadow can make the shade out of date.

The map's signature hashed every planting, although only a plant tall enough to
shade (`canopy.shades`) becomes a crown in the light model. So planting a
perennial from the suggestions marked the sun map and the list "stale" when the
shade could not have changed, and the gardener was sent to recompute for
nothing (owner's check #9, 2026-09-21).
"""
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
GIFT = {"source": "GIFT", "license": "CC-BY-4.0"}
PERENNIAL, SHRUB, UNMEASURED = 1, 2, 3


def _species(conn: sqlite3.Connection, tid: int, name: str, height: float | None,
             form: str) -> None:
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
                 (tid, name))
    if height is not None:
        upsert_trait(conn, tid, "height_max_m", value_num=height, **GIFT)
    upsert_trait(conn, tid, "growth_form", value_text=form, **GIFT)


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    _species(conn, PERENNIAL, "Salvia pratensis", 0.6, "forb")
    _species(conn, SHRUB, "Corylus avellana", 5.0, "shrub")
    _species(conn, UNMEASURED, "Ohne Höhe", None, "shrub")
    conn.commit()
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _computed_bed(client: TestClient) -> tuple[str, int]:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    bed = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "Beet", "polygon": SQUARE, "soil_type": "loam", "moisture": "fresh"},
    ).json()["beds"][0]
    client.post(f"/api/v1/gardens/{token}/recompute")
    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is False
    return token, int(bed["bed_id"])


def _plant(client: TestClient, token: str, bed_id: int, **payload: object) -> None:
    response = client.post(f"/api/v1/gardens/{token}/beds/{bed_id}/plantings", json=payload)
    assert response.status_code == 201, response.text


def _stale(client: TestClient, token: str, bed_id: int) -> tuple[bool, str]:
    """The map's flag and the list's word on it, which must agree."""
    stale = client.get(f"/api/v1/gardens/{token}/light").json()["stale"]
    state = client.get(f"/api/v1/gardens/{token}/beds/{bed_id}/suggestions").json()["light_state"]
    return stale, state


def test_planting_a_perennial_leaves_the_shade_current(client: TestClient) -> None:
    token, bed_id = _computed_bed(client)
    _plant(client, token, bed_id, taxon_id=PERENNIAL, quantity=5)
    assert _stale(client, token, bed_id) == (False, "current")


def test_a_name_the_catalogue_does_not_know_casts_no_shadow_either(client: TestClient) -> None:
    token, bed_id = _computed_bed(client)
    _plant(client, token, bed_id, raw_name="Rose 'Gloria Dei'")
    _plant(client, token, bed_id, taxon_id=UNMEASURED)
    assert _stale(client, token, bed_id) == (False, "current")


def test_planting_a_shrub_makes_the_shade_stale(client: TestClient) -> None:
    token, bed_id = _computed_bed(client)
    _plant(client, token, bed_id, taxon_id=SHRUB)
    assert _stale(client, token, bed_id) == (True, "stale")


def test_moving_the_shrub_makes_it_stale_again_after_a_recompute(client: TestClient) -> None:
    token, bed_id = _computed_bed(client)
    _plant(client, token, bed_id, taxon_id=SHRUB)
    client.post(f"/api/v1/gardens/{token}/recompute")
    assert _stale(client, token, bed_id) == (False, "current")
    garden = client.get(f"/api/v1/gardens/{token}").json()
    planting = garden["beds"][0]["plantings"][0]["planting_id"]
    moved = client.patch(f"/api/v1/gardens/{token}/plantings/{planting}", json={"x": 3.0, "y": 3.0})
    assert moved.status_code == 200, moved.text
    assert _stale(client, token, bed_id) == (True, "stale")
