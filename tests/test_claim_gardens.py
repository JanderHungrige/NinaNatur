"""Claiming a garden made before there was an account to put it under.

Wave 3 put a nullable `owner_id` on `garden` in the very first migration so this
would cost one column rather than a migration of live plans. This is where that
pays off.
"""
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

ANNA = {"username": "anna", "password": "ein langes Passwort"}
BEN = {"username": "ben", "password": "ein anderes langes Passwort"}


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    from ninanatur.api import accounts

    accounts.ATTEMPTS.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


def _garden(client: TestClient, name: str = "Garten") -> str:
    token: str = client.post(
        "/api/v1/gardens", json={"name": name, "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    return token


def _login(client: TestClient, who: dict[str, str]) -> None:
    client.post("/api/v1/accounts", json=who)
    client.post("/api/v1/sessions", json=who)


def test_a_logged_in_user_can_claim_a_garden_from_its_link(client: TestClient) -> None:
    token = _garden(client)
    _login(client, ANNA)
    assert client.post(f"/api/v1/gardens/{token}/claim").status_code == 200


def test_claiming_needs_a_session(client: TestClient) -> None:
    token = _garden(client)
    assert client.post(f"/api/v1/gardens/{token}/claim").status_code == 401


def test_a_claimed_garden_appears_in_the_account(client: TestClient) -> None:
    token = _garden(client, "Mein Beet")
    _login(client, ANNA)
    client.post(f"/api/v1/gardens/{token}/claim")
    mine = client.get("/api/v1/accounts/me/gardens").json()["gardens"]
    assert [g["name"] for g in mine] == ["Mein Beet"]


def test_a_garden_somebody_else_owns_cannot_be_taken(client: TestClient) -> None:
    """Holding the link is enough to edit a garden — that was Wave 3's bargain —
    but not to take it away from the person who claimed it."""
    token = _garden(client)
    _login(client, ANNA)
    client.post(f"/api/v1/gardens/{token}/claim")
    client.delete("/api/v1/sessions")

    _login(client, BEN)
    assert client.post(f"/api/v1/gardens/{token}/claim").status_code == 409


def test_the_share_link_keeps_working_after_a_claim(client: TestClient) -> None:
    """Removing share links to push registration would be a downgrade dressed
    as a feature."""
    token = _garden(client)
    _login(client, ANNA)
    client.post(f"/api/v1/gardens/{token}/claim")
    client.delete("/api/v1/sessions")
    assert client.get(f"/api/v1/gardens/{token}").status_code == 200


def test_a_stranger_with_the_link_can_still_edit(client: TestClient) -> None:
    token = _garden(client)
    _login(client, ANNA)
    client.post(f"/api/v1/gardens/{token}/claim")
    client.delete("/api/v1/sessions")
    response = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "B", "polygon": [[0, 0], [2, 0], [2, 2], [0, 2]],
              "soil_type": "loam", "moisture": "fresh"},
    )
    assert response.status_code in (200, 201)


def test_deleting_from_the_share_link_stays_possible(client: TestClient) -> None:
    """Optional email means account loss is expected, not exceptional. A garden
    that can only be deleted by an account nobody can reach is a garden nobody
    can delete."""
    token = _garden(client)
    _login(client, ANNA)
    client.post(f"/api/v1/gardens/{token}/claim")
    client.delete("/api/v1/sessions")
    assert client.delete(f"/api/v1/gardens/{token}").status_code == 204


def test_claiming_a_garden_twice_is_not_an_error(client: TestClient) -> None:
    token = _garden(client)
    _login(client, ANNA)
    client.post(f"/api/v1/gardens/{token}/claim")
    assert client.post(f"/api/v1/gardens/{token}/claim").status_code == 200


def test_an_account_with_no_gardens_gets_an_empty_list(client: TestClient) -> None:
    _login(client, ANNA)
    assert client.get("/api/v1/accounts/me/gardens").json()["gardens"] == []


def test_the_garden_list_needs_a_session(client: TestClient) -> None:
    assert client.get("/api/v1/accounts/me/gardens").status_code == 401


def test_the_list_carries_the_share_token_so_it_can_be_opened(
    client: TestClient,
) -> None:
    token = _garden(client)
    _login(client, ANNA)
    client.post(f"/api/v1/gardens/{token}/claim")
    mine = client.get("/api/v1/accounts/me/gardens").json()["gardens"]
    assert mine[0]["share_token"] == token


def test_one_account_does_not_see_another_account_s_gardens(
    client: TestClient,
) -> None:
    token = _garden(client)
    _login(client, ANNA)
    client.post(f"/api/v1/gardens/{token}/claim")
    client.delete("/api/v1/sessions")
    _login(client, BEN)
    assert client.get("/api/v1/accounts/me/gardens").json()["gardens"] == []
