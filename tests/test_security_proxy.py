"""Wave 20, feature 1: whom the app believes about who is asking.

Nginx Proxy Manager reaches the app from the Docker network's gateway — measured
on the host as 172.27.0.1 for production — and says who the visitor was in
`X-Forwarded-For`. Before this, the app believed nobody: every visitor was the
proxy, so the login limit put the whole site in one bucket. The opposite mistake
is as bad: believing *anybody's* header lets a visitor pick their own identity,
or somebody else's.

`TestClient(client=...)` stands in for the connection's source address, which is
exactly the thing the trust decision is made on.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import ratelimit
from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

PROXY = ("172.27.0.1", 50000)      # the prod network's gateway, as measured
STRANGER = ("203.0.113.50", 50000)  # a direct connection from the internet
GOOD = {"username": "gaertnerin", "password": "ein langes Passwort"}
WRONG = {**GOOD, "password": "falsch aber lang"}


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


def via_proxy() -> TestClient:
    return TestClient(app, client=PROXY)


def as_visitor(address: str) -> dict[str, str]:
    """What NPM sends: `$proxy_add_x_forwarded_for`, the visitor's address last."""
    return {"x-forwarded-for": address, "x-forwarded-proto": "https"}


def _fail_logins(client: TestClient, headers: dict[str, str], times: int) -> list[int]:
    return [client.post("/api/v1/sessions", json=WRONG, headers=headers).status_code
            for _ in range(times)]


# --- the limit is per visitor, not per site ---------------------------------

def test_one_visitors_failures_do_not_lock_out_another(conn: sqlite3.Connection) -> None:
    """The finding: keyed on the proxy, ten wrong passwords from anybody locked
    the login for everybody."""
    client = via_proxy()
    client.post("/api/v1/accounts", json=GOOD, headers=as_visitor("198.51.100.1"))
    assert 429 in _fail_logins(client, as_visitor("198.51.100.1"), 12)

    other = client.post("/api/v1/sessions", json=GOOD, headers=as_visitor("198.51.100.2"))
    assert other.status_code == 200


def test_a_forged_left_hand_address_does_not_buy_a_fresh_bucket(
    conn: sqlite3.Connection,
) -> None:
    """A visitor can put anything in the header before NPM appends the real
    address. Only the rightmost one is the proxy's statement."""
    client = via_proxy()
    client.post("/api/v1/accounts", json=GOOD, headers=as_visitor("198.51.100.7"))
    _fail_logins(client, as_visitor("198.51.100.7"), 12)

    forged = client.post("/api/v1/sessions", json=WRONG,
                         headers=as_visitor("10.0.0.99, 198.51.100.7"))
    assert forged.status_code == 429


def test_a_stranger_cannot_claim_to_be_somebody(conn: sqlite3.Connection) -> None:
    """A header from a connection that is not the proxy means nothing — else a
    stranger could lock a chosen victim out by naming their address."""
    victim, stranger = via_proxy(), TestClient(app, client=STRANGER)
    victim.post("/api/v1/accounts", json=GOOD, headers=as_visitor("198.51.100.9"))
    _fail_logins(stranger, as_visitor("198.51.100.9"), 12)

    assert victim.post("/api/v1/sessions", json=GOOD,
                       headers=as_visitor("198.51.100.9")).status_code == 200


# --- the scheme, for the cookie ----------------------------------------------

def test_https_via_the_proxy_marks_the_cookie_secure(conn: sqlite3.Connection) -> None:
    client = via_proxy()
    client.post("/api/v1/accounts", json=GOOD, headers=as_visitor("198.51.100.3"))
    r = client.post("/api/v1/sessions", json=GOOD, headers=as_visitor("198.51.100.3"))
    assert "secure" in r.headers["set-cookie"].lower()


def test_a_strangers_forwarded_proto_is_not_believed(conn: sqlite3.Connection) -> None:
    """Read raw, the header let anybody talking to the app directly decide
    whether the session cookie was marked Secure."""
    client = TestClient(app, client=STRANGER)
    client.post("/api/v1/accounts", json=GOOD)
    r = client.post("/api/v1/sessions", json=GOOD, headers={"x-forwarded-proto": "https"})
    assert "secure" not in r.headers["set-cookie"].lower()


# --- it survives a restart ----------------------------------------------------

def test_the_count_survives_the_process(conn: sqlite3.Connection) -> None:
    """In a dict it was forgotten on every image roll. On the volume it is not:
    a second client over the same database — a new process — still refuses."""
    first = via_proxy()
    first.post("/api/v1/accounts", json=GOOD, headers=as_visitor("198.51.100.4"))
    _fail_logins(first, as_visitor("198.51.100.4"), 12)

    after_restart = via_proxy()
    r = after_restart.post("/api/v1/sessions", json=WRONG, headers=as_visitor("198.51.100.4"))
    assert r.status_code == 429


# --- the expensive routes -----------------------------------------------------

@pytest.mark.parametrize("bucket, method, path", [
    ("light", "post", "/api/v1/gardens/{token}/light"),
    ("recompute", "post", "/api/v1/gardens/{token}/recompute"),
])
def test_an_expensive_route_is_limited_per_visitor(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
    bucket: str, method: str, path: str,
) -> None:
    """Each can cost seconds of CPU and an outbound survey query, and neither
    needs an account."""
    monkeypatch.setitem(ratelimit.LIMITS, bucket, (3, 600.0))
    client = via_proxy()
    token = client.post("/api/v1/gardens", json={"name": "G", "latitude": 51.2564,
                                                  "longitude": 7.1501}).json()["share_token"]
    url = path.format(token=token)
    codes = [getattr(client, method)(url, headers=as_visitor("198.51.100.5")).status_code
             for _ in range(4)]
    assert codes[:3] != [429] * 3 and codes[3] == 429
    other = getattr(client, method)(url, headers=as_visitor("198.51.100.6"))
    assert other.status_code != 429


def test_the_map_import_is_limited_before_it_asks_anybody(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ninanatur.api import geo

    calls = {"n": 0}

    def counted(*_a: object, **_k: object) -> list[object]:
        calls["n"] += 1
        return []

    monkeypatch.setattr(geo, "buildings_in", counted)
    monkeypatch.setattr(geo, "streets_in", counted)
    monkeypatch.setitem(ratelimit.LIMITS, "from-map", (2, 600.0))
    outline = [{"lat": 51.2564, "lon": 7.1501}, {"lat": 51.2565, "lon": 7.1501},
               {"lat": 51.2565, "lon": 7.1503}]
    client = via_proxy()
    codes = [client.post("/api/v1/gardens/from-map", json={"name": "G", "outline": outline},
                         headers=as_visitor("198.51.100.8")).status_code for _ in range(3)]
    assert codes[2] == 429
    assert calls["n"] <= 4, "the refused import still asked Overpass"
