"""Recording what already grows in a garden, including what we cannot name.

The catalogue holds 8,939 German species and no cultivars, so a name it does not
know is an ordinary answer rather than a mistake. Discarding it would tell
someone their garden is wrong because our data is incomplete.
"""
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.data.names import normalise
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    conn.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (1, 'Primula veris', 1)"
    )
    conn.execute(
        "INSERT INTO vernacular_name (taxon_id, name, normalised, is_preferred, source)"
        " VALUES (1, 'Echte Schlüsselblume', ?, 1, 'GBIF')",
        (normalise("Echte Schlüsselblume"),),
    )
    upsert_trait(conn, 1, "ellenberg_l", value_num=6.0, source="EIVE-1.0", license="CC-BY-4.0")
    conn.commit()
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _bed(client: TestClient) -> tuple[str, int]:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    bed = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "B", "polygon": SQUARE, "soil_type": "loam", "moisture": "fresh"},
    ).json()["beds"][0]
    return token, int(bed["bed_id"])


def _add(client: TestClient, token: str, bed_id: int, **body: object) -> dict:
    response = client.post(f"/api/v1/gardens/{token}/beds/{bed_id}/plantings", json=body)
    assert response.status_code in (200, 201), response.text
    result: dict = response.json()
    return result


def test_a_german_name_resolves_to_its_species(client: TestClient) -> None:
    token, bed_id = _bed(client)
    body = _add(client, token, bed_id, raw_name="Echte Schlüsselblume")
    planting = body["beds"][0]["plantings"][0]
    assert planting["taxon_id"] == 1
    assert planting["canonical_name"] == "Primula veris"


def test_the_words_the_user_typed_are_kept_alongside_the_match(client: TestClient) -> None:
    """Not sentiment: it is how someone recognises their own entry, and how a
    later catalogue improvement can re-resolve it."""
    token, bed_id = _bed(client)
    body = _add(client, token, bed_id, raw_name="Echte Schlüsselblume")
    assert body["beds"][0]["plantings"][0]["raw_name"] == "Echte Schlüsselblume"


def test_a_name_the_catalogue_does_not_know_is_kept(client: TestClient) -> None:
    token, bed_id = _bed(client)
    body = _add(client, token, bed_id, raw_name="Bauernhortensie", quantity=3)
    planting = body["beds"][0]["plantings"][0]
    assert planting["taxon_id"] is None
    assert planting["raw_name"] == "Bauernhortensie"
    assert planting["quantity"] == 3


def test_two_unidentified_plants_can_share_a_bed(client: TestClient) -> None:
    # Two unknown roses are two plants. NULLs are distinct in SQLite, which is
    # exactly the behaviour wanted here.
    token, bed_id = _bed(client)
    _add(client, token, bed_id, raw_name="Rose vom Vorbesitzer")
    body = _add(client, token, bed_id, raw_name="Andere Rose")
    assert len(body["beds"][0]["plantings"]) == 2


def test_the_garden_reports_what_it_could_not_identify(client: TestClient) -> None:
    """A score computed over 4 of 7 plantings must say so."""
    token, bed_id = _bed(client)
    _add(client, token, bed_id, raw_name="Echte Schlüsselblume")
    _add(client, token, bed_id, raw_name="Bauernhortensie")
    body = client.get(f"/api/v1/gardens/{token}").json()
    assert body["unidentified_plantings"] == 1


def test_an_unidentified_planting_scores_nothing_rather_than_zero(
    client: TestClient,
) -> None:
    # Not zero: "we have no data" and "this plant is worth nothing" are
    # different facts, and the score's own report is where that shows.
    token, bed_id = _bed(client)
    _add(client, token, bed_id, raw_name="Bauernhortensie")
    score = client.get(f"/api/v1/gardens/{token}/score").json()
    assert score["by_species"] == []


def test_a_taxon_id_still_works_for_the_suggestion_path(client: TestClient) -> None:
    # Wave 4's "Pflanzen" button sends an id, and must keep working.
    token, bed_id = _bed(client)
    body = _add(client, token, bed_id, taxon_id=1, quantity=2)
    planting = body["beds"][0]["plantings"][0]
    assert planting["taxon_id"] == 1
    assert planting["quantity"] == 2


def test_a_planting_needs_either_a_name_or_an_id(client: TestClient) -> None:
    token, bed_id = _bed(client)
    response = client.post(f"/api/v1/gardens/{token}/beds/{bed_id}/plantings", json={})
    assert response.status_code == 422


def test_a_blank_name_is_not_a_plant(client: TestClient) -> None:
    token, bed_id = _bed(client)
    response = client.post(
        f"/api/v1/gardens/{token}/beds/{bed_id}/plantings", json={"raw_name": "   "}
    )
    assert response.status_code == 422


def test_a_scientific_name_resolves_too(client: TestClient) -> None:
    token, bed_id = _bed(client)
    body = _add(client, token, bed_id, raw_name="Primula veris")
    assert body["beds"][0]["plantings"][0]["taxon_id"] == 1
