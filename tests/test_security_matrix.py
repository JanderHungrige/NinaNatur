"""Whose garden is it — every route, against every garden but its own.

Wave 20, feature 0: the authorization matrix, and a CI gate.

The share token is the whole of a garden's access control, and every id below
it — a bed, an element, a planting, a tree suggestion — is a capability only
together with it. Each check existed and was tested where it was written, one
route family at a time. What no test held is the whole: that *every* route
taking such an id refuses one from another garden and leaves both gardens as
they were, that every route taking a token refuses one that names no garden —
and that the next route to be added does too. The tables are checked against
the app's own route list, walked the way the API document walks it.

The answer is always 404, never 403: telling a caller that an id exists but
belongs to somebody else is the one thing a capability URL must not do.
"""
from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from route_walk import api_routes, path_ids, takes_token

from ninanatur.api.deps import get_connection
from ninanatur.garden.canopies_found import remember
from ninanatur.geo.canopy import Canopy
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

pytestmark = pytest.mark.gate

G = "/api/v1/gardens/{token}"
Body = dict[str, Any] | None

#: Every route that takes the id of something inside a garden, with a body it
#: would accept from that garden.
OWNED: dict[tuple[str, str], Body] = {
    ("PATCH", f"{G}/beds/{{bed_id}}"): {"name": "Umbenannt"},
    ("POST", f"{G}/beds/{{bed_id}}/plantings"): {"taxon_id": 1, "quantity": 1},
    ("GET", f"{G}/beds/{{bed_id}}/suggestions"): None,
    ("POST", f"{G}/canopies/{{suggestion_id}}"): None,
    ("DELETE", f"{G}/canopies/{{suggestion_id}}"): None,
    ("PATCH", f"{G}/obstacles/{{obstacle_id}}"): {"label": "Umbenannt"},
    ("DELETE", f"{G}/obstacles/{{obstacle_id}}"): None,
    ("PATCH", f"{G}/plantings/{{planting_id}}"): {"x": 0.5, "y": 0.5},
    ("DELETE", f"{G}/plantings/{{planting_id}}"): None,
}

#: Ids that are nobody's property: species in the catalogue. `/plants/{taxon_id}`
#: *is* the catalogue, and a hand-entered colour is a shared catalogue entry by
#: design — the one cross-garden write, named in the report rather than refused.
PUBLIC_IDS = frozenset({
    ("GET", "/api/v1/plants/{taxon_id}"),
    ("GET", "/api/v1/plants/{taxon_id}/info"),
    ("PUT", f"{G}/colours/{{taxon_id}}"),
})

#: Every other route that takes a token, with a body it would accept.
BY_TOKEN: dict[tuple[str, str], Body] = {
    ("GET", G): None,
    ("DELETE", G): None,
    ("POST", f"{G}/beds"): {"name": "Beet", "polygon": [[0, 0], [2, 0], [2, 2]]},
    ("GET", f"{G}/bloom"): None,
    ("GET", f"{G}/canopies"): None,
    ("POST", f"{G}/claim"): None,
    ("PUT", f"{G}/colours/{{taxon_id}}"): {"colour": "blue"},
    ("GET", f"{G}/improvements"): None,
    ("GET", f"{G}/light"): None,
    ("POST", f"{G}/light"): None,
    ("POST", f"{G}/obstacles"): {"kind": "shed", "x": 1.0, "y": 1.0},
    ("POST", f"{G}/recompute"): None,
    ("GET", f"{G}/score"): None,
    ("GET", f"{G}/shadows"): None,
    ("POST", f"{G}/sightlines"): {"x": 0.0, "y": 0.0},
    ("PATCH", f"{G}/soil"): {"soil_type": "loam", "moisture": "fresh"},
    ("GET", f"{G}/terrain"): None,
    ("GET", f"{G}/timeline"): None,
}
EVERY_TOKEN_ROUTE = {**BY_TOKEN, **OWNED}
ACCOUNT = {"username": "gaertnerin", "password": "ein langes Passwort"}


@dataclass(frozen=True)
class Planted:
    """One garden with one of everything an id can name."""

    token: str
    ids: dict[str, int]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    made.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de)"
                 " VALUES (1, 'Salvia pratensis', 1)")
    made.commit()
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


def _plant(client: TestClient, conn: sqlite3.Connection, name: str) -> Planted:
    token = client.post("/api/v1/gardens", json={
        "name": name, "latitude": 51.0, "longitude": 7.0}).json()["share_token"]
    base = f"/api/v1/gardens/{token}"
    garden = client.post(f"{base}/beds", json={
        "name": "Beet", "polygon": [[0, 0], [3, 0], [3, 2], [0, 2]],
        "soil_type": "loam", "moisture": "fresh"}).json()
    bed = garden["beds"][-1]["bed_id"]
    garden = client.post(f"{base}/beds/{bed}/plantings",
                         json={"taxon_id": 1, "quantity": 2}).json()
    planting = garden["beds"][-1]["plantings"][-1]["planting_id"]
    garden = client.post(f"{base}/obstacles", json={"kind": "shed", "x": 6.0, "y": 6.0}).json()
    obstacle = garden["obstacles"][-1]["obstacle_id"]
    garden_id = conn.execute("SELECT garden_id FROM garden WHERE share_token = ?",
                             (token,)).fetchone()[0]
    remember(conn, garden_id, [Canopy(x=12.0, y=12.0, radius_m=3.0, height_m=14.0)])
    suggestion = client.get(f"{base}/canopies").json()[0]["suggestion_id"]
    return Planted(token, {"bed_id": bed, "planting_id": planting, "obstacle_id": obstacle,
                           "suggestion_id": suggestion, "taxon_id": 1})


@pytest.fixture()
def gardens(conn: sqlite3.Connection) -> tuple[TestClient, Planted, Planted]:
    client = TestClient(app)
    return client, _plant(client, conn, "Mein Garten"), _plant(client, conn, "Fremder Garten")


def _status(client: TestClient, method: str, path: str, body: Body) -> int:
    return client.request(method, path, **({} if body is None else {"json": body})).status_code


def _url(path: str, token: str, ids: dict[str, int]) -> str:
    return path.format(token=token, **ids)


def _state(client: TestClient, garden: Planted) -> Any:
    base = f"/api/v1/gardens/{garden.token}"
    return client.get(base).json(), client.get(f"{base}/canopies").json()


def _ids(table: dict[tuple[str, str], Body]) -> list[str]:
    return [f"{method} {path}" for method, path in sorted(table)]


def test_the_tables_name_every_route_the_app_has() -> None:
    """A route added next year is in none of these tables, and fails here until
    somebody has decided what kind of id it takes."""
    routes = api_routes(app)
    with_ids = {(m, r.path) for r in routes if path_ids(r) for m in r.methods}
    with_token = {(m, r.path) for r in routes if takes_token(r) for m in r.methods}

    assert with_ids == set(OWNED) | PUBLIC_IDS
    assert with_token == set(EVERY_TOKEN_ROUTE)


@pytest.mark.parametrize(("method", "path"), sorted(OWNED), ids=_ids(OWNED))
def test_an_id_from_another_garden_is_a_404_and_changes_nothing(
    gardens: tuple[TestClient, Planted, Planted], method: str, path: str,
) -> None:
    client, mine, theirs = gardens
    before = (_state(client, mine), _state(client, theirs))

    status = _status(client, method, _url(path, mine.token, theirs.ids), OWNED[(method, path)])

    assert status == 404
    assert (_state(client, mine), _state(client, theirs)) == before


@pytest.mark.parametrize(("method", "path"), sorted(OWNED), ids=_ids(OWNED))
def test_the_same_call_with_the_garden_s_own_id_is_answered(
    gardens: tuple[TestClient, Planted, Planted], method: str, path: str,
) -> None:
    """So the 404 above is about whose id it is — not a request that could
    never have worked."""
    client, _mine, theirs = gardens
    status = _status(client, method, _url(path, theirs.token, theirs.ids), OWNED[(method, path)])

    assert 200 <= status < 300


@pytest.mark.parametrize(("method", "path"), sorted(EVERY_TOKEN_ROUTE),
                         ids=_ids(EVERY_TOKEN_ROUTE))
def test_a_token_that_names_no_garden_is_a_404(
    gardens: tuple[TestClient, Planted, Planted], method: str, path: str,
) -> None:
    """Never a 403, which would say the garden exists, and never an answer."""
    client, _mine, theirs = gardens
    if path.endswith("/claim"):
        # Claiming asks who is asking first; a stranger is a 401 before any
        # token is looked at. Logged in, the token is what is left to refuse.
        client.post("/api/v1/accounts", json=ACCOUNT)
        client.post("/api/v1/sessions", json=ACCOUNT)
    unknown = secrets.token_urlsafe(32)

    status = _status(client, method, _url(path, unknown, theirs.ids),
                     EVERY_TOKEN_ROUTE[(method, path)])

    assert status == 404
