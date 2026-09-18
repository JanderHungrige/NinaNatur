"""Where a roof's numbers came from, and whose word wins (doc 93).

The survey, OpenStreetMap, the storey count and the gardener all write a roof.
The page has to say which one did, and a refresh must not overwrite what the
gardener said — value by value, not building by building.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import geo as geo_routes
from ninanatur.api.deps import get_connection
from ninanatur.garden.measured import apply, measure
from ninanatur.garden.roofs import Roof
from ninanatur.garden.store import garden_by_token
from ninanatur.geo.lod2 import Lod2Building
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

HOUSE = [[-4.0, -3.0], [4.0, -3.0], [4.0, 3.0], [-4.0, 3.0]]


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


def _imported_house(client: TestClient, conn: sqlite3.Connection) -> tuple[str, int]:
    """A house as the map import leaves it: its height from the storey count."""
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 51.0, "longitude": 6.0}
    ).json()["share_token"]
    body = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "house", "shape": "polygon", "x": 0, "y": 0, "points": HOUSE,
              "height": 9.0},
    ).json()
    house = int(body["obstacles"][-1]["obstacle_id"])
    conn.execute(
        "UPDATE element SET height_source = 'osm_levels', roof_source = 'osm'"
        " WHERE element_id = ?", (house,),
    )
    conn.commit()
    return token, house


def _survey(conn: sqlite3.Connection, token: str, *, eaves: float | None) -> None:
    """The state's survey, arriving on a recompute: a 10 m gable over the house."""
    garden = garden_by_token(conn, token)
    assert garden is not None
    building = Lod2Building(
        building_id="DE_X", roof=Roof.GABLE, height_m=10.0, eaves_m=eaves,
        outline=[(-4.0, -3.0), (4.0, -3.0), (4.0, 3.0), (-4.0, 3.0)],
    )
    apply(conn, measure(garden, [building], None))


def _house(client: TestClient, token: str, house: int) -> dict[str, Any]:
    garden = client.get(f"/api/v1/gardens/{token}").json()
    found: dict[str, Any] = next(o for o in garden["obstacles"] if o["obstacle_id"] == house)
    return found


def _patch(client: TestClient, token: str, house: int, **body: Any) -> dict[str, Any]:
    response = client.patch(f"/api/v1/gardens/{token}/obstacles/{house}", json=body)
    assert response.status_code == 200, response.text
    found: dict[str, Any] = next(
        o for o in response.json()["obstacles"] if o["obstacle_id"] == house
    )
    return found


def test_a_chosen_roof_is_the_gardeners_and_survives_the_survey(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    token, house = _imported_house(client, conn)
    assert _patch(client, token, house, roof="hip")["roof_source"] == "user"

    _survey(conn, token, eaves=6.0)

    after = _house(client, token, house)
    assert after["roof"] == "hip"
    assert after["roof_source"] == "user"
    # The height was left to the survey, and the survey answered it.
    assert after["height"] == 10.0
    assert after["height_source"] == "surveyed"


def test_a_typed_eaves_height_survives_the_survey(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    token, house = _imported_house(client, conn)
    assert _patch(client, token, house, eaves_m=5.0)["eaves_source"] == "user"

    _survey(conn, token, eaves=6.3)

    after = _house(client, token, house)
    assert after["eaves_m"] == 5.0
    assert after["eaves_source"] == "user"


def test_the_survey_fills_the_eaves_and_says_so(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    token, house = _imported_house(client, conn)
    before = _house(client, token, house)
    assert before["eaves_m"] is None
    assert before["eaves_source"] is None

    _survey(conn, token, eaves=6.3)

    after = _house(client, token, house)
    assert after["eaves_m"] == 6.3
    assert after["eaves_source"] == "surveyed"
    assert after["roof"] == "gable"
    assert after["roof_source"] == "surveyed"


def test_a_survey_without_eaves_keeps_the_ones_from_the_storeys(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    token, house = _imported_house(client, conn)
    conn.execute(
        "UPDATE element SET eaves_m = 6.0, eaves_source = 'osm_levels' WHERE element_id = ?",
        (house,),
    )
    conn.commit()

    _survey(conn, token, eaves=None)

    after = _house(client, token, house)
    assert after["eaves_m"] == 6.0
    assert after["eaves_source"] == "osm_levels"


def test_weiss_nicht_is_nobodys_answer_and_the_survey_may_give_one(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    token, house = _imported_house(client, conn)
    said = _patch(client, token, house, roof="unknown")
    assert said["roof"] == "unknown"
    assert said["roof_source"] == "user"

    _survey(conn, token, eaves=6.0)

    after = _house(client, token, house)
    assert after["roof"] == "gable"
    assert after["roof_source"] == "surveyed"


def test_emptying_the_eaves_hands_them_back_to_the_survey(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    token, house = _imported_house(client, conn)
    _patch(client, token, house, eaves_m=5.0)
    cleared = _patch(client, token, house, eaves_m=None)
    assert cleared["eaves_m"] is None
    assert cleared["eaves_source"] is None

    _survey(conn, token, eaves=6.3)

    after = _house(client, token, house)
    assert after["eaves_m"] == 6.3
    assert after["eaves_source"] == "surveyed"


def test_a_rename_is_not_a_statement_about_the_roof(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    token, house = _imported_house(client, conn)
    _survey(conn, token, eaves=6.3)

    renamed = _patch(client, token, house, label="Nachbarhaus")

    assert renamed["label"] == "Nachbarhaus"
    assert renamed["height_source"] == "surveyed"
    assert renamed["roof_source"] == "surveyed"
    assert renamed["eaves_source"] == "surveyed"


def test_a_client_cannot_name_the_source_of_its_own_number(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    token, house = _imported_house(client, conn)

    typed = _patch(client, token, house, height=11.0, height_source="surveyed",
                   roof="gable", roof_source="surveyed", eaves_m=7.0,
                   eaves_source="surveyed")

    assert typed["height_source"] == "user"
    assert typed["roof_source"] == "user"
    assert typed["eaves_source"] == "user"


# --- the map import ---------------------------------------------------------

OUTLINE = [
    {"lat": 52.4055, "lon": 13.2100},
    {"lat": 52.4055, "lon": 13.21029},
    {"lat": 52.40568, "lon": 13.21029},
    {"lat": 52.40568, "lon": 13.2100},
]


@pytest.fixture()
def imported(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> list[dict[str, Any]]:
    """The houses a map selection brings with it: one tagged, one bare."""
    from ninanatur.geo.projection import LatLon
    from ninanatur.geo.surroundings import OsmBuilding

    tagged = {"building": "house", "height": "9", "roof:shape": "gabled",
              "building:levels": "2"}
    bare = {"building": "house", "height": "9"}
    monkeypatch.setattr(geo_routes, "buildings_in", lambda *_a, **_k: [
        OsmBuilding(1, LatLon(52.40530, 13.21015), [], tagged),
        OsmBuilding(2, LatLon(52.40530, 13.21035), [], bare),
    ])
    monkeypatch.setattr(geo_routes, "streets_in", lambda *_a, **_k: [])
    response = client.post(
        "/api/v1/gardens/from-map", json={"name": "Kartengarten", "outline": OUTLINE}
    )
    assert response.status_code in (200, 201), response.text
    houses: list[dict[str, Any]] = [
        o for o in response.json()["garden"]["obstacles"] if o["kind"] == "house"
    ]
    return houses


def test_an_imported_roof_says_it_came_from_openstreetmap(
    imported: list[dict[str, Any]]
) -> None:
    tagged = next(h for h in imported if h["roof"] == "gable")
    assert tagged["roof_source"] == "osm"
    assert tagged["eaves_m"] == 6.0
    assert tagged["eaves_source"] == "osm_levels"


def test_an_import_without_storeys_leaves_the_eaves_unsaid(
    imported: list[dict[str, Any]]
) -> None:
    bare = next(h for h in imported if h["roof"] == "unknown")
    assert bare["eaves_m"] is None
    assert bare["eaves_source"] is None
    assert bare["roof_source"] == "osm"
