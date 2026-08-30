"""Editing what an object is, after it has been drawn."""
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _garden(client: TestClient) -> tuple[str, int]:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    bed = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "B", "polygon": SQUARE, "soil_type": "loam", "moisture": "fresh"},
    ).json()["beds"][0]
    return token, int(bed["bed_id"])


def test_a_bed_can_be_raised_and_says_so(client: TestClient) -> None:
    token, bed_id = _garden(client)
    response = client.patch(
        f"/api/v1/gardens/{token}/beds/{bed_id}",
        json={"height_above_ground": 0.8, "label": "Hochbeet an der Mauer"},
    )
    assert response.status_code == 200, response.text
    bed = response.json()["beds"][0]
    assert bed["height_above_ground"] == 0.8
    assert bed["label"] == "Hochbeet an der Mauer"


def test_raising_a_bed_recomputes_its_light(client: TestClient) -> None:
    """Otherwise the number on screen describes a bed that no longer exists."""
    token, bed_id = _garden(client)
    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "fence", "x": 0.0, "y": -1.0, "radius": 0.3, "height": 1.4},
    )
    before = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["sun_hours"]

    client.patch(
        f"/api/v1/gardens/{token}/beds/{bed_id}", json={"height_above_ground": 1.6}
    )
    after = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["sun_hours"]
    assert after > before


def test_an_obstacle_gets_a_kind_from_the_vocabulary(client: TestClient) -> None:
    token, _ = _garden(client)
    created = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "tree", "x": 2.0, "y": -5.0, "radius": 3.0, "height": 8.0},
    )
    assert created.status_code in (200, 201), created.text
    obstacle = created.json()["obstacles"][0]

    response = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{obstacle['obstacle_id']}",
        json={"kind": "hedge", "height": 2.5, "label": "Liguster zum Nachbarn"},
    )
    assert response.status_code == 200, response.text
    edited = response.json()["obstacles"][0]
    assert edited["kind"] == "hedge"
    assert edited["height"] == 2.5
    assert edited["label"] == "Liguster zum Nachbarn"


def test_an_invented_kind_is_refused(client: TestClient) -> None:
    """A free string means the shading table silently misses a value."""
    token, _ = _garden(client)
    response = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "hedgehog", "x": 0.0, "y": 0.0, "radius": 1.0, "height": 1.0},
    )
    assert response.status_code == 422


def test_editing_an_obstacle_recomputes_the_light(client: TestClient) -> None:
    token, _ = _garden(client)
    created = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "fence", "x": 0.0, "y": -1.0, "radius": 0.3, "height": 1.2},
    ).json()["obstacles"][0]
    before = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["sun_hours"]

    client.patch(
        f"/api/v1/gardens/{token}/obstacles/{created['obstacle_id']}",
        json={"height": 6.0},
    )
    after = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["sun_hours"]
    assert after < before, "a 6 m wall casts more shade than a 1.2 m fence"


def test_a_label_is_stored_as_text_not_interpreted(client: TestClient) -> None:
    token, bed_id = _garden(client)
    nasty = "<script>alert(1)</script>"
    body = client.patch(
        f"/api/v1/gardens/{token}/beds/{bed_id}", json={"label": nasty}
    ).json()
    assert body["beds"][0]["label"] == nasty


def test_editing_a_bed_of_another_garden_is_404(client: TestClient) -> None:
    _, bed_id = _garden(client)
    other = client.post(
        "/api/v1/gardens", json={"name": "H", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    response = client.patch(
        f"/api/v1/gardens/{other}/beds/{bed_id}", json={"height_above_ground": 1.0}
    )
    assert response.status_code == 404


def test_a_negative_height_is_refused(client: TestClient) -> None:
    token, bed_id = _garden(client)
    response = client.patch(
        f"/api/v1/gardens/{token}/beds/{bed_id}", json={"height_above_ground": -1.0}
    )
    assert response.status_code == 422


def test_an_edited_height_becomes_the_users_word_on_it(client: TestClient) -> None:
    """Wave 8 places buildings with assumed heights. Correcting one has to make
    it authoritative, or the sightline keeps marking it as a guess."""
    token, _ = _garden(client)
    created = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "building", "x": 0.0, "y": -6.0, "radius": 4.0, "height": 7.0},
    ).json()["obstacles"][0]
    assert created["height_source"] == "user"

    edited = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{created['obstacle_id']}",
        json={"height": 11.0, "height_source": "user"},
    ).json()["obstacles"][0]
    assert edited["height"] == 11.0
    assert edited["height_source"] == "user"
