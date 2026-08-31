"""Registration, login, and the promises made at the point of choosing.

This is the first feature here that stores a secret, so the tests are about the
properties rather than the happy path.
"""
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

GOOD = {"username": "gaertnerin", "password": "ein langes Passwort"}


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    from ninanatur.api import accounts

    accounts.ATTEMPTS.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- registration ----------------------------------------------------------

def test_an_account_can_be_made_without_an_email(client: TestClient) -> None:
    """The whole point of the feature as asked for."""
    response = client.post("/api/v1/accounts", json=GOOD)
    assert response.status_code == 201, response.text
    assert response.json()["email"] is None


def test_the_answer_says_what_no_email_costs(client: TestClient) -> None:
    """A limit discovered later is a support burden and a broken promise."""
    body = client.post("/api/v1/accounts", json=GOOD).json()
    assert "zurückgesetzt" in body["recovery_note"]


def test_with_an_email_the_note_is_different(client: TestClient) -> None:
    body = client.post(
        "/api/v1/accounts", json={**GOOD, "email": "jemand@example.org"}
    ).json()
    assert "zurückgesetzt" not in body["recovery_note"]


def test_the_password_never_comes_back(client: TestClient) -> None:
    body = client.post("/api/v1/accounts", json=GOOD).json()
    assert "password" not in str(body).lower()


def test_a_short_password_is_refused(client: TestClient) -> None:
    response = client.post("/api/v1/accounts", json={**GOOD, "password": "kurz"})
    assert response.status_code == 422


def test_a_password_that_is_the_username_is_refused(client: TestClient) -> None:
    # No composition rules — length and the obvious mistake, per NIST.
    response = client.post(
        "/api/v1/accounts", json={"username": "gaertnerin", "password": "gaertnerin"}
    )
    assert response.status_code == 422


def test_a_taken_username_is_refused(client: TestClient) -> None:
    client.post("/api/v1/accounts", json=GOOD)
    assert client.post("/api/v1/accounts", json=GOOD).status_code == 409


def test_the_stored_hash_is_not_the_password(client: TestClient) -> None:
    client.post("/api/v1/accounts", json=GOOD)
    conn = app.dependency_overrides[get_connection]()
    stored = conn.execute("SELECT password_hash FROM account").fetchone()["password_hash"]
    assert GOOD["password"] not in stored
    assert stored.startswith("scrypt$")


# --- login -----------------------------------------------------------------

def test_logging_in_sets_a_protected_cookie(client: TestClient) -> None:
    client.post("/api/v1/accounts", json=GOOD)
    response = client.post("/api/v1/sessions", json=GOOD)
    assert response.status_code == 200, response.text
    raw = response.headers["set-cookie"].lower()
    # Lower-cased on purpose: SameSite's value is case-insensitive per RFC 6265bis,
    # so asserting the capitalisation would test the framework's formatting
    # rather than the protection.
    assert "httponly" in raw
    assert "samesite=lax" in raw


def test_the_session_token_is_not_stored_as_given(client: TestClient) -> None:
    """A stolen database must not be a drawer full of usable sessions."""
    client.post("/api/v1/accounts", json=GOOD)
    client.post("/api/v1/sessions", json=GOOD)
    conn = app.dependency_overrides[get_connection]()
    row = conn.execute("SELECT token_hash FROM session").fetchone()
    cookie = client.cookies.get("ninanatur_session")
    assert cookie is not None
    assert row["token_hash"] != cookie


def test_a_wrong_password_is_refused(client: TestClient) -> None:
    client.post("/api/v1/accounts", json=GOOD)
    response = client.post("/api/v1/sessions", json={**GOOD, "password": "falsch aber lang"})
    assert response.status_code == 401


def test_an_unknown_user_and_a_wrong_password_answer_the_same(client: TestClient) -> None:
    """Otherwise the login form is a username oracle."""
    client.post("/api/v1/accounts", json=GOOD)
    wrong = client.post("/api/v1/sessions", json={**GOOD, "password": "falsch aber lang"})
    missing = client.post(
        "/api/v1/sessions", json={"username": "gibtesnicht", "password": "falsch aber lang"}
    )
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


def test_who_am_i_needs_a_session(client: TestClient) -> None:
    assert client.get("/api/v1/accounts/me").status_code == 401


def test_who_am_i_answers_when_logged_in(client: TestClient) -> None:
    client.post("/api/v1/accounts", json=GOOD)
    client.post("/api/v1/sessions", json=GOOD)
    assert client.get("/api/v1/accounts/me").json()["username"] == "gaertnerin"


def test_logging_out_ends_the_session(client: TestClient) -> None:
    client.post("/api/v1/accounts", json=GOOD)
    client.post("/api/v1/sessions", json=GOOD)
    client.delete("/api/v1/sessions")
    assert client.get("/api/v1/accounts/me").status_code == 401


def test_a_forged_cookie_is_not_a_session(client: TestClient) -> None:
    client.cookies.set("ninanatur_session", "a" * 43)
    assert client.get("/api/v1/accounts/me").status_code == 401


# --- rate limiting ---------------------------------------------------------

def test_repeated_failures_are_slowed_down(client: TestClient) -> None:
    """The API has had no rate limit since Wave 3, which stops being acceptable
    the moment credentials exist."""
    client.post("/api/v1/accounts", json=GOOD)
    codes = [
        client.post("/api/v1/sessions", json={**GOOD, "password": "falsch aber lang"}).status_code
        for _ in range(12)
    ]
    assert 429 in codes


def test_the_limit_does_not_lock_out_a_correct_login_immediately(
    client: TestClient,
) -> None:
    client.post("/api/v1/accounts", json=GOOD)
    for _ in range(3):
        client.post("/api/v1/sessions", json={**GOOD, "password": "falsch aber lang"})
    assert client.post("/api/v1/sessions", json=GOOD).status_code == 200


def test_registration_is_limited_too(client: TestClient) -> None:
    codes = [
        client.post(
            "/api/v1/accounts", json={"username": f"nutzer{i}", "password": "ein langes Passwort"}
        ).status_code
        for i in range(12)
    ]
    assert 429 in codes


def test_the_cookie_is_marked_secure_behind_an_https_proxy(client: TestClient) -> None:
    """The deployment sits behind Nginx Proxy Manager, so the app only learns
    the real scheme from the forwarded header. Hardcoding Secure on breaks local
    development; hardcoding it off ships a session cookie over plaintext."""
    client.post("/api/v1/accounts", json=GOOD)
    response = client.post(
        "/api/v1/sessions", json=GOOD, headers={"x-forwarded-proto": "https"}
    )
    assert "secure" in response.headers["set-cookie"].lower()


def test_it_is_not_marked_secure_over_plain_http(client: TestClient) -> None:
    # Otherwise the cookie is set and then never sent back, and login silently
    # does nothing in local development.
    client.post("/api/v1/accounts", json=GOOD)
    response = client.post("/api/v1/sessions", json=GOOD)
    assert "secure" not in response.headers["set-cookie"].lower()


def test_an_expired_session_is_not_a_session(client: TestClient) -> None:
    from datetime import UTC, datetime, timedelta

    client.post("/api/v1/accounts", json=GOOD)
    client.post("/api/v1/sessions", json=GOOD)
    conn = app.dependency_overrides[get_connection]()
    conn.execute(
        "UPDATE session SET expires_at = ?",
        ((datetime.now(UTC) - timedelta(days=1)).isoformat(),),
    )
    conn.commit()
    assert client.get("/api/v1/accounts/me").status_code == 401


def test_no_password_or_token_appears_in_a_log_line(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """The plan's rule, checked rather than promised."""
    import logging

    with caplog.at_level(logging.DEBUG):
        client.post("/api/v1/accounts", json=GOOD)
        client.post("/api/v1/sessions", json=GOOD)
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert GOOD["password"] not in logged
    cookie = client.cookies.get("ninanatur_session")
    assert cookie is None or cookie not in logged


def test_an_eight_character_password_is_accepted(client: TestClient) -> None:
    """Ten was arbitrary and read as officious. Eight is the floor NIST
    SP 800-63B sets for a user-chosen secret, and the same guidance says not to
    add composition rules on top — so there are none."""
    made = client.post(
        "/api/v1/accounts",
        json={"username": "achtzeichen", "password": "garten12"},
    )
    assert made.status_code == 201, made.json()


def test_a_seven_character_password_is_still_refused(client: TestClient) -> None:
    """A floor, not a suggestion. Leaving it to the user entirely would put the
    account below every published guideline."""
    short = client.post(
        "/api/v1/accounts",
        json={"username": "siebenzeichen", "password": "garten1"},
    )
    assert short.status_code == 422


def test_nothing_is_demanded_of_a_password_but_length(client: TestClient) -> None:
    """Letters only, no digits, no symbols. A rule forcing a symbol produces
    "Passwort1!" and very little security."""
    plain = client.post(
        "/api/v1/accounts",
        json={"username": "nurbuchstaben", "password": "gartenzaun"},
    )
    assert plain.status_code == 201, plain.json()


def _sign_up(client: TestClient, username: str) -> None:
    client.post(
        "/api/v1/accounts", json={"username": username, "password": "gartenzaun"}
    )
    client.post(
        "/api/v1/sessions", json={"username": username, "password": "gartenzaun"}
    )


def test_a_garden_made_while_signed_in_belongs_to_that_account(
    client: TestClient,
) -> None:
    """Reported: "der Garten wird zu keinem Zeitpunkt gespeichert bzw. nicht auf
    der Landing Page angezeigt".

    Creating never set `owner_id` and nothing called `/claim` afterwards, so a
    garden made while signed in belonged to nobody — and the list that filters
    on owner found none of them. The account kept nothing.
    """
    _sign_up(client, "besitzerin")
    made = client.post(
        "/api/v1/gardens",
        json={"name": "Vorgarten", "latitude": 52.5, "longitude": 13.4},
    )
    assert made.status_code == 201

    mine = client.get("/api/v1/accounts/me/gardens").json()["gardens"]
    assert [g["name"] for g in mine] == ["Vorgarten"]


def test_a_garden_made_from_the_map_belongs_to_it_too(client: TestClient) -> None:
    """The way most people start. It had the same gap."""
    _sign_up(client, "kartennutzer")
    made = client.post(
        "/api/v1/gardens/from-map",
        json={
            "name": "Vom Plan",
            "outline": [
                {"lat": 52.5, "lon": 13.4},
                {"lat": 52.5004, "lon": 13.4},
                {"lat": 52.5004, "lon": 13.4006},
            ],
        },
    )
    assert made.status_code == 201, made.json()
    mine = client.get("/api/v1/accounts/me/gardens").json()["gardens"]
    assert [g["name"] for g in mine] == ["Vom Plan"]


def test_a_garden_made_by_nobody_still_works(client: TestClient) -> None:
    """Signing in stays optional. An anonymous garden is the ordinary case and
    its token is still the whole of its access control."""
    made = client.post(
        "/api/v1/gardens",
        json={"name": "Ohne Konto", "latitude": 52.5, "longitude": 13.4},
    )
    assert made.status_code == 201
    token = made.json()["share_token"]
    assert client.get(f"/api/v1/gardens/{token}").status_code == 200
