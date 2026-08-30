"""Standing somewhere in the garden and asking what is visible."""
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.web.app import app

GIFT = {"source": "GIFT", "license": "CC-BY-4.0"}
BED = [[-2.0, 8.0], [2.0, 8.0], [2.0, 12.0], [-2.0, 12.0]]


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    # 3 m, not 2.4: a 2 m hedge 4 m from the eye hides everything under 2.6 m
    # at 10 m, which is correct geometry and made the first fixture meaningless.
    for tid, name, height in ((1, "Bodendecker", 0.2), (2, "Hochstaude", 3.0)):
        conn.execute(
            "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
            (tid, name),
        )
        upsert_trait(conn, tid, "height_max_m", value_num=height, **GIFT)
    conn.commit()
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _garden(client: TestClient) -> tuple[str, int]:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    bed = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "Beet", "polygon": BED, "soil_type": "loam", "moisture": "fresh"},
    ).json()["beds"][0]
    for taxon in (1, 2):
        client.post(
            f"/api/v1/gardens/{token}/beds/{bed['bed_id']}/plantings",
            json={"taxon_id": taxon},
        )
    return token, int(bed["bed_id"])


def _look(client: TestClient, token: str, **body: Any) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/gardens/{token}/sightlines",
        json={"x": 0.0, "y": 0.0, "eye_height_m": 1.6, **body},
    )
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


def _by_name(body: dict[str, Any], name: str) -> dict[str, Any]:
    return next(p for p in body["plantings"] if p["name"] == name)


def test_with_nothing_in_the_way_everything_is_visible(client: TestClient) -> None:
    token, _ = _garden(client)
    body = _look(client, token)
    assert all(p["visible"] for p in body["plantings"])


def test_a_hedge_hides_the_ground_cover_but_not_the_tall_one(client: TestClient) -> None:
    token, _ = _garden(client)
    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "hedge", "x": 0.0, "y": 4.0, "radius": 3.0, "height": 2.0},
    )
    body = _look(client, token)
    assert _by_name(body, "Bodendecker")["visible"] is False
    assert _by_name(body, "Hochstaude")["visible"] is True


def test_it_says_from_what_height_something_would_be_visible(client: TestClient) -> None:
    token, _ = _garden(client)
    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "hedge", "x": 0.0, "y": 4.0, "radius": 3.0, "height": 2.0},
    )
    hidden = _by_name(_look(client, token), "Bodendecker")
    assert hidden["visible_from_m"] > 0.2


def test_raising_the_bed_brings_it_back_into_view(client: TestClient) -> None:
    # Wave 7 stored height_above_ground for this as much as for the light.
    token, bed_id = _garden(client)
    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "hedge", "x": 0.0, "y": 4.0, "radius": 3.0, "height": 1.2},
    )
    assert _by_name(_look(client, token), "Bodendecker")["visible"] is False
    client.patch(f"/api/v1/gardens/{token}/beds/{bed_id}", json={"height_above_ground": 1.4})
    assert _by_name(_look(client, token), "Bodendecker")["visible"] is True


def test_an_answer_resting_on_a_guessed_height_says_so(client: TestClient) -> None:
    """The plan's requirement in one line: a sightline computed from an
    estimated building height must not be drawn as though it were surveyed."""
    token, _ = _garden(client)
    obstacle = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "building", "x": 0.0, "y": 4.0, "radius": 3.0, "height": 7.0},
    ).json()["obstacles"][0]
    client.patch(
        f"/api/v1/gardens/{token}/obstacles/{obstacle['obstacle_id']}",
        json={"height_source": "neighbourhood"},
    )
    hidden = _by_name(_look(client, token), "Bodendecker")
    assert hidden["visible"] is False
    assert hidden["estimated"] is True


def test_a_plant_with_no_recorded_height_is_reported_not_guessed(
    client: TestClient,
) -> None:
    # Height is recorded for 44% of the catalogue. Assuming one would put a
    # confident answer on top of nothing.
    conn = app.dependency_overrides[get_connection]()
    conn.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, occurs_de)"
        " VALUES (3, 'Namenlos', 1)"
    )
    conn.commit()
    token, bed_id = _garden(client)
    client.post(f"/api/v1/gardens/{token}/beds/{bed_id}/plantings", json={"taxon_id": 3})
    entry = _by_name(_look(client, token), "Namenlos")
    assert entry["height_m"] is None
    assert entry["visible"] is None


def test_the_viewpoint_must_be_inside_a_sensible_garden(client: TestClient) -> None:
    token, _ = _garden(client)
    response = client.post(
        f"/api/v1/gardens/{token}/sightlines", json={"x": 0.0, "y": 0.0, "eye_height_m": 40.0}
    )
    assert response.status_code == 422
