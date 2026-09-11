"""Sessions that end — Wave 20, feature 9.

Read on 2026-09-11, before any of this:

- `needs_rehash` existed and nothing called it, so raising the scrypt
  parameters would have raised them for new accounts only, for ever.
- An expired session was refused but never deleted; the table only grew.
- The cookie's lifetime was written out beside `SESSION_DAYS` instead of from it.
- `SameSite=Lax` keeps the cookie off other *sites* — but to a browser a site is
  the registrable domain, `w3rth.de`, and three other projects on this host live
  under it. Their pages are the same site: a POST without a body needs no
  preflight, carries the cookie, and `POST /gardens/{token}/claim` is exactly that.
- The account answer promised "Mit deiner E-Mail-Adresse lässt sich das Passwort
  zurücksetzen" — and there is no reset, anywhere.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from route_walk import WRITES, api_routes

from ninanatur.api import geo
from ninanatur.api.accounts import current_account
from ninanatur.api.deps import get_connection
from ninanatur.auth.passwords import SCRYPT_N, verify_password
from ninanatur.auth.sessions import COOKIE_NAME, SESSION_DAYS, token_hash
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

GOOD = {"username": "gaertnerin", "password": "ein langes Passwort"}
GARDEN = {"name": "G", "latitude": 51.2564, "longitude": 7.1501}
OUTLINE = [{"lat": 51.2564, "lon": 7.1501}, {"lat": 51.2565, "lon": 7.1501},
           {"lat": 51.2565, "lon": 7.1503}]
SAME = {"origin": "http://testserver", "sec-fetch-site": "same-origin"}
SISTER = {"origin": "https://3dmap.w3rth.de", "sec-fetch-site": "same-site"}
ELSEWHERE = {"origin": "https://example.org", "sec-fetch-site": "cross-site"}


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


def _registered() -> TestClient:
    client = TestClient(app)
    assert client.post("/api/v1/accounts", json=GOOD).status_code == 201
    return client


def _stored(conn: sqlite3.Connection) -> str:
    return str(conn.execute("SELECT password_hash FROM account").fetchone()[0])


def _weak_hash(password: str) -> str:
    """A real, verifying hash — made with the parameters of a smaller era."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**12, r=8, p=1, dklen=32)
    return f"scrypt${2**12}$8$1${salt.hex()}${digest.hex()}"


# --- the hash moves with the parameters ------------------------------------------------

def test_a_login_rehashes_a_password_stored_with_weaker_parameters(
    conn: sqlite3.Connection,
) -> None:
    """The one moment the password itself is in hand — the only moment a
    raised parameter can reach an existing account."""
    client = _registered()
    conn.execute("UPDATE account SET password_hash = ?", (_weak_hash(GOOD["password"]),))
    conn.commit()
    assert client.post("/api/v1/sessions", json=GOOD).status_code == 200
    stored = _stored(conn)
    assert stored.split("$")[1] == str(SCRYPT_N)
    assert verify_password(GOOD["password"], stored)


def test_a_login_with_current_parameters_leaves_the_hash_alone(
    conn: sqlite3.Connection,
) -> None:
    client = _registered()
    before = _stored(conn)
    assert client.post("/api/v1/sessions", json=GOOD).status_code == 200
    assert _stored(conn) == before


def test_a_failed_login_rehashes_nothing(conn: sqlite3.Connection) -> None:
    client = _registered()
    weak = _weak_hash(GOOD["password"])
    conn.execute("UPDATE account SET password_hash = ?", (weak,))
    conn.commit()
    assert client.post("/api/v1/sessions",
                       json={**GOOD, "password": "falsch aber lang"}).status_code == 401
    assert _stored(conn) == weak


# --- sessions that end -------------------------------------------------------------------

def _session(conn: sqlite3.Connection, token: str, *, days_left: int) -> None:
    now = datetime.now(UTC)
    conn.execute(
        "INSERT INTO session (token_hash, account_id, created_at, expires_at)"
        " VALUES (?, (SELECT account_id FROM account), ?, ?)",
        (token_hash(token), (now - timedelta(days=SESSION_DAYS)).isoformat(),
         (now + timedelta(days=days_left)).isoformat()),
    )
    conn.commit()


def _hashes(conn: sqlite3.Connection) -> set[str]:
    return {str(row[0]) for row in conn.execute("SELECT token_hash FROM session")}


def test_an_expired_session_is_deleted_when_it_comes_back(conn: sqlite3.Connection) -> None:
    client = _registered()
    _session(conn, "old-token", days_left=-1)
    client.cookies.set(COOKIE_NAME, "old-token")
    assert client.get("/api/v1/accounts/me").status_code == 401
    assert token_hash("old-token") not in _hashes(conn)


def test_expired_sessions_are_swept_whenever_anybody_logs_in(conn: sqlite3.Connection) -> None:
    """Nobody brings a forgotten session back. Without a sweep it stays for ever."""
    client = _registered()
    _session(conn, "forgotten", days_left=-3)
    _session(conn, "still-good", days_left=5)
    assert client.post("/api/v1/sessions", json=GOOD).status_code == 200
    kept = _hashes(conn)
    assert token_hash("forgotten") not in kept
    assert token_hash("still-good") in kept
    assert len(kept) == 2, "the one still valid, and the one just issued"


def test_the_cookie_ends_when_the_session_does(conn: sqlite3.Connection) -> None:
    answer = _registered().post("/api/v1/sessions", json=GOOD)
    assert f"Max-Age={SESSION_DAYS * 24 * 60 * 60}" in answer.headers["set-cookie"]


# --- where a request comes from ----------------------------------------------------------

@pytest.fixture()
def no_overpass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(geo, "buildings_in", lambda *_a, **_k: [])
    monkeypatch.setattr(geo, "streets_in", lambda *_a, **_k: [])


def _acts_on_login() -> list[tuple[str, str, dict[str, Any] | None]]:
    return [
        ("post", "/api/v1/accounts", {**GOOD, "username": "zweite"}),
        ("post", "/api/v1/sessions", GOOD),
        ("delete", "/api/v1/sessions", None),
        ("post", "/api/v1/gardens", GARDEN),
        ("post", "/api/v1/gardens/from-map", {"name": "G", "outline": OUTLINE}),
        ("post", "/api/v1/gardens/{token}/claim", None),
    ]


@pytest.mark.parametrize("headers", [SISTER, ELSEWHERE, {"origin": "null"},
                                     {"sec-fetch-site": "same-site"}],
                         ids=["a sister site on w3rth.de", "another site", "an opaque origin",
                              "same-site without an origin"])
@pytest.mark.parametrize(("method", "path", "body"), _acts_on_login(),
                         ids=[f"{m} {p}" for m, p, _ in _acts_on_login()])
def test_a_request_from_another_page_is_refused(
    conn: sqlite3.Connection, no_overpass: None, headers: dict[str, str],
    method: str, path: str, body: dict[str, Any] | None,
) -> None:
    client = _registered()
    client.post("/api/v1/sessions", json=GOOD)
    token = str(TestClient(app).post("/api/v1/gardens", json=GARDEN).json()["share_token"])
    call: Callable[..., Any] = getattr(client, method)
    kwargs: dict[str, Any] = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    assert call(path.format(token=token), **kwargs).status_code == 403


def test_a_sister_site_cannot_make_a_logged_in_visitor_claim_a_garden(
    conn: sqlite3.Connection,
) -> None:
    """The one route the preflight did not cover: no body, so no preflight."""
    client = _registered()
    assert client.post("/api/v1/sessions", json=GOOD).status_code == 200
    token = TestClient(app).post("/api/v1/gardens", json=GARDEN).json()["share_token"]
    assert client.post(f"/api/v1/gardens/{token}/claim", headers=SISTER).status_code == 403
    assert conn.execute("SELECT owner_id FROM garden").fetchone()[0] is None


def test_our_own_page_is_let_through(conn: sqlite3.Connection) -> None:
    client = _registered()
    assert client.post("/api/v1/sessions", json=GOOD, headers=SAME).status_code == 200
    token = TestClient(app).post("/api/v1/gardens", json=GARDEN).json()["share_token"]
    assert client.post(f"/api/v1/gardens/{token}/claim", headers=SAME).status_code == 200
    assert client.delete("/api/v1/sessions", headers=SAME).status_code == 204


def _calls(dependant: Any) -> Iterator[Any]:
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _calls(dependency)


@pytest.mark.gate
def test_every_route_that_acts_on_a_login_checks_where_it_came_from() -> None:
    """So a route added next year cannot forget it: anything that changes state
    and reads the session — or sets or clears it — carries the check.

    Walked the way the API document walks them (`route_walk.py`). The first
    version looped over `app.routes`, which since FastAPI 0.141 holds included
    routers as opaque entries: it met three routes, none of them a write, and
    passed by checking nothing. So it now also says what it checked.
    """
    from ninanatur.api.origin import same_origin

    checked: set[str] = set()
    for route in api_routes(app):
        if not set(route.methods) & WRITES:
            continue
        calls = set(_calls(route.dependant))
        if current_account in calls or route.path in ("/api/v1/sessions", "/api/v1/accounts"):
            assert same_origin in calls, f"{route.path} acts on a login without the check"
            checked.add(route.path)
    assert checked >= {"/api/v1/accounts", "/api/v1/sessions", "/api/v1/gardens",
                       "/api/v1/gardens/from-map", "/api/v1/gardens/{token}/claim"}


# --- what the account answer may promise -------------------------------------------------

def test_with_an_email_nothing_is_promised_that_does_not_exist(conn: sqlite3.Connection) -> None:
    body = TestClient(app).post(
        "/api/v1/accounts", json={**GOOD, "email": "jemand@example.org"}).json()
    note = body["recovery_note"]
    assert "nicht bestätigt" in note
    assert "noch nicht" in note, "a reset that does not exist is not offered"


def test_no_password_reset_exists_while_email_addresses_are_unverified(
    conn: sqlite3.Connection,
) -> None:
    """A reset mailed to an address nobody confirmed hands the account to
    whoever typed it. If a reset route ever appears, verification comes first."""
    paths = [str(route.path).lower() for route in api_routes(app)]
    resets = [p for p in paths if "reset" in p or "recover" in p]
    columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(account)")}
    assert not resets or "email_verified_at" in columns
