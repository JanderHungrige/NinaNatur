"""A shape the plan cannot draw is refused before it is stored (owner's check #3).

The server used to store an element first and build its footprint only when
the garden was read. One freehand press that stayed within one centimetre
stored a line of one point twice, and from then on every request on that
garden answered 422 "a band needs at least two points", whatever it asked.
Each "failed" add was committed anyway.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.garden.elements import insert_element
from ninanatur.garden.store import create_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.repairs import UNBUILDABLE_KEY, mend_unbuildable_elements
from ninanatur.web.app import app

PATH = {"kind": "path", "x": 2.0, "y": 2.0, "shape": "line", "width": 1.0,
        "points": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0]]}


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    yield connection


@pytest.fixture()
def client(conn: sqlite3.Connection) -> Iterator[TestClient]:
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _token(client: TestClient) -> str:
    return str(client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"])


def _count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM element").fetchone()[0])


@pytest.mark.parametrize(
    "shape",
    [
        {"shape": "line", "width": 1.0, "points": [[0.0, 0.0], [0.0, 0.0]]},
        {"shape": "line", "width": 1.0},
        {"shape": "polygon", "points": [[0.0, 0.0], [1.0, 0.0]]},
        {"shape": "polygon", "points": [[0.0, 0.0], [1.0, 0.0], [1.0, 0.0]]},
    ],
)
def test_a_shape_with_no_footprint_is_refused_and_nothing_is_stored(
    client: TestClient, conn: sqlite3.Connection, shape: dict[str, object]
) -> None:
    token = _token(client)
    refused = client.post(
        f"/api/v1/gardens/{token}/obstacles", json={"kind": "path", "x": 1, "y": 1, **shape}
    )
    assert refused.status_code == 422
    assert _count(conn) == 0
    # The garden still opens, and the next add works.
    assert client.get(f"/api/v1/gardens/{token}").status_code == 200
    added = client.post(f"/api/v1/gardens/{token}/obstacles", json={"kind": "shed", "x": 0, "y": 0})
    assert added.status_code == 201


def test_reshaping_a_path_keeps_its_width(client: TestClient) -> None:
    """A vertex drag sends points, a resize sends points and a position, and
    neither sends the band. Both used to clear it."""
    token = _token(client)
    path = client.post(f"/api/v1/gardens/{token}/obstacles", json=PATH).json()["obstacles"][0]
    url = f"/api/v1/gardens/{token}/obstacles/{path['obstacle_id']}"

    dragged = client.patch(url, json={"points": [[0, 0], [5, 0], [5, 3]], "constraint_hint": None})
    assert dragged.status_code == 200, dragged.text
    assert dragged.json()["obstacles"][0]["width"] == 1.0

    resized = client.patch(url, json={"x": 3.0, "y": 2.5, "points": [[0, 0], [6, 0], [6, 4]]})
    assert resized.status_code == 200, resized.text
    assert resized.json()["obstacles"][0]["width"] == 1.0


def test_an_edit_that_collapses_a_line_is_refused_and_changes_nothing(
    client: TestClient,
) -> None:
    token = _token(client)
    path = client.post(f"/api/v1/gardens/{token}/obstacles", json=PATH).json()["obstacles"][0]
    url = f"/api/v1/gardens/{token}/obstacles/{path['obstacle_id']}"

    refused = client.patch(url, json={"points": [[1, 1], [1, 1]]})
    assert refused.status_code == 422
    opened = client.get(f"/api/v1/gardens/{token}")
    assert opened.status_code == 200
    assert opened.json()["obstacles"][0]["points"] == PATH["points"]


def test_a_width_only_change_to_a_line_is_judged_on_its_stored_points(
    client: TestClient,
) -> None:
    token = _token(client)
    path = client.post(f"/api/v1/gardens/{token}/obstacles", json=PATH).json()["obstacles"][0]
    widened = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{path['obstacle_id']}", json={"width": 1.5}
    )
    assert widened.status_code == 200, widened.text
    assert widened.json()["obstacles"][0]["width"] == 1.5


def _stored(conn: sqlite3.Connection, garden_id: int, **fields: object) -> int:
    fields.setdefault("kind", "path")
    return insert_element(conn, garden_id, x=0.0, y=0.0, **fields)


def test_the_repair_gives_a_path_its_width_back_and_removes_what_cannot_be_drawn(
    conn: sqlite3.Connection,
) -> None:
    """The gardens broken before the check open again."""
    conn.execute("DELETE FROM catalogue_meta WHERE key = ?", (UNBUILDABLE_KEY,))
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    reshaped = _stored(conn, garden_id, shape="line", width=None,
                       points=[[0.0, 0.0], [3.0, 0.0]])
    dot = _stored(conn, garden_id, shape="line", width=1.0,
                  points=[[0.0, 0.0], [0.0, 0.0]])
    fine = _stored(conn, garden_id, shape="line", width=0.6,
                   points=[[0.0, 0.0], [2.0, 0.0]])
    house = _stored(conn, garden_id, kind="house", shape="polygon", height=8.0,
                    points=[[0.0, 0.0], [8.0, 0.0], [8.0, 6.0]])
    conn.commit()

    said = mend_unbuildable_elements(conn)

    assert said is not None and "1 path" in said and "removed 1" in said
    widths = dict(conn.execute("SELECT element_id, width FROM element").fetchall())
    assert set(widths) == {reshaped, fine, house}
    assert dot not in widths
    assert widths[reshaped] is not None and widths[reshaped] > 0
    assert widths[fine] == 0.6


def test_the_repair_runs_once(conn: sqlite3.Connection) -> None:
    """A fresh database is marked, so the repair never fires later."""
    marked = conn.execute(
        "SELECT value FROM catalogue_meta WHERE key = ?", (UNBUILDABLE_KEY,)
    ).fetchone()
    assert marked is not None
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    _stored(conn, garden_id, shape="line", width=None, points=[[0.0, 0.0], [3.0, 0.0]])
    conn.commit()
    assert mend_unbuildable_elements(conn) is None


def test_a_street_that_collapses_to_a_point_costs_that_street_not_the_garden(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """A way whose nodes sit inside one centimetre is no line once rounded. It
    used to fail the whole import, after the garden was already committed."""
    from ninanatur.api import geo as geo_routes
    from ninanatur.geo.osm_streets import OsmStreet
    from ninanatur.geo.projection import LatLon

    def street(osm_id: int, name: str, end: LatLon) -> OsmStreet:
        return OsmStreet(osm_id=osm_id, name=name, width_m=6.0,
                         centreline=[LatLon(lat=52.4998, lon=13.3998), end])

    monkeypatch.setattr(geo_routes, "buildings_in", lambda *a, **k: [])
    monkeypatch.setattr(geo_routes, "streets_in", lambda *a, **k: [
        street(1, "Punkt", LatLon(lat=52.49980001, lon=13.39980001)),
        street(2, "Gartenweg", LatLon(lat=52.5006, lon=13.4008)),
    ])
    made = client.post("/api/v1/gardens/from-map", json={
        "name": "Mit Straße",
        "outline": [{"lat": 52.5, "lon": 13.4}, {"lat": 52.5004, "lon": 13.4},
                    {"lat": 52.5004, "lon": 13.4006}],
    })
    assert made.status_code == 201, made.json()
    streets = [o["label"] for o in made.json()["garden"]["obstacles"] if o["kind"] == "street"]
    assert streets == ["Gartenweg"]
