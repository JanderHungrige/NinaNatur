"""Wave 20, feature 3: what the app says about itself.

Measured on 2026-09-10: the live site sent no security header at all — Nginx
Proxy Manager adds nothing but `Server` and `X-Served-By` — and `/openapi.json`
and `/api/docs` answered anybody. Two failure paths were reproduced against the
app's own client: an unreachable upstream came back as a bare 500, and an
upstream that answered HTML instead of JSON came back as a **422 carrying the
parser's message**, which blames the caller for somebody else's outage.

These tests are also one of the wave's three CI gates: the header assertions
keep holding after the wave is done.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import geo
from ninanatur.api.deps import get_connection
from ninanatur.geo.orthophotos import ORTHOPHOTOS
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.http import HttpError
from ninanatur.web.app import app

pytestmark = pytest.mark.gate

PROXY = ("172.27.0.1", 50000)
FIXED = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def directive(policy: str, name: str) -> str:
    for part in policy.split(";"):
        part = part.strip()
        if part.startswith(name + " "):
            return part
    return ""


def assert_guarded(headers: object) -> None:
    got = {k.lower(): v for k, v in dict(headers).items()}  # type: ignore[call-overload]
    for name, value in FIXED.items():
        assert got.get(name) == value, f"{name}: {got.get(name)!r}"
    policy = got.get("content-security-policy", "")
    assert "frame-ancestors 'none'" in policy
    assert directive(policy, "script-src") == "script-src 'self'"
    assert "object-src 'none'" in policy
    assert "unsafe-inline" not in policy and "unsafe-eval" not in policy


# --- every kind of answer carries the headers --------------------------------

@pytest.mark.parametrize("method, path, body", [
    ("get", "/", None),
    ("get", "/healthz", None),
    ("get", "/api/v1/gardens/nichtda", None),          # a 404
    ("post", "/api/v1/gardens", {"name": ""}),          # a 422
])
def test_every_kind_of_answer_carries_the_headers(
    client: TestClient, method: str, path: str, body: dict[str, str] | None
) -> None:
    response = getattr(client, method)(path, **({"json": body} if body else {}))
    assert_guarded(response.headers)


def test_even_a_refused_oversized_body_carries_them(client: TestClient) -> None:
    r = client.post("/api/v1/gardens", content=" " * 1_100_000,
                    headers={"content-type": "application/json"})
    assert r.status_code == 413
    assert_guarded(r.headers)


# --- the policy names exactly what the page loads ----------------------------

def test_the_policy_names_every_host_the_plan_draws_from(client: TestClient) -> None:
    """Tiles, both Wikimedia hosts — `thumb.` served five of seven photos in the
    local catalogue, and a policy naming only `upload.` would have blanked
    them — and every state's aerial imagery, read from the registry so a new
    state cannot be forgotten here."""
    img = directive(client.get("/healthz").headers["content-security-policy"], "img-src")
    for origin in ("https://tile.openstreetmap.org",
                   "https://upload.wikimedia.org", "https://thumb.wikimedia.org"):
        assert origin in img
    for service in ORTHOPHOTOS:
        parsed = urlparse(service.url)
        assert f"{parsed.scheme}://{parsed.netloc}" in img, service.state


def test_the_policy_allows_nothing_the_page_does_not_use(client: TestClient) -> None:
    policy = client.get("/healthz").headers["content-security-policy"]
    assert directive(policy, "connect-src") == "connect-src 'self'"
    assert directive(policy, "media-src") == "media-src 'self'"
    for loose in ("data:", "blob:", " * ", "http:"):
        assert loose not in directive(policy, "img-src") + " ", loose


# --- HSTS, where TLS is: via the proxy only ----------------------------------

def test_hsts_over_https_via_the_proxy() -> None:
    r = TestClient(app, client=PROXY).get("/healthz", headers={"x-forwarded-proto": "https"})
    assert r.headers.get("strict-transport-security", "").startswith("max-age=")


def test_no_hsts_over_plain_http(client: TestClient) -> None:
    assert "strict-transport-security" not in client.get("/healthz").headers


# --- whose name the app answers to --------------------------------------------

@pytest.mark.parametrize("host", ["ninanatur.w3rth.de", "ninanatur-dev.w3rth.de", "127.0.0.1"])
def test_the_real_names_are_answered(client: TestClient, host: str) -> None:
    assert client.get("/healthz", headers={"host": host}).status_code == 200


def test_a_forged_host_is_refused(client: TestClient) -> None:
    r = client.get("/healthz", headers={"host": "evil.example"})
    assert r.status_code == 400
    assert_guarded(r.headers)


# --- the API description: dark in production, up on the preview --------------

def test_the_api_description_is_dark_in_production(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NINANATUR_ENV", raising=False)
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/api/docs").status_code == 404


def test_the_api_description_stays_up_on_the_preview(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NINANATUR_ENV", "dev")
    assert client.get("/openapi.json").json()["info"]["title"] == "NinaNatur"
    docs = client.get("/api/docs")
    assert docs.status_code == 200
    # Swagger UI needs its CDN and an inline script; only this page gets them.
    assert "cdn.jsdelivr.net" in docs.headers["content-security-policy"]


# --- somebody else's outage is not the caller's fault -------------------------

def test_an_unreachable_service_is_a_502_that_names_nobody(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def down(*_a: object, **_k: object) -> object:
        raise HttpError("GET https://nominatim.openstreetmap.org/search?q=Hauptstr failed: 503")

    monkeypatch.setattr(geo, "search_address", down)
    r = client.get("/api/v1/geo/search", params={"q": "Hauptstr 1"})
    assert r.status_code == 502
    assert "nominatim" not in r.text.lower() and "http" not in r.text.lower()


def test_a_service_answering_nonsense_is_a_502_not_the_callers_fault(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def nonsense(*_a: object, **_k: object) -> object:
        return json.loads("<html>Bad Gateway</html>")

    monkeypatch.setattr(geo, "search_address", nonsense)
    r = client.get("/api/v1/geo/search", params={"q": "Hauptstr 1"})
    assert r.status_code == 502
    assert "Expecting value" not in r.text


def test_our_own_refusals_still_explain_themselves(client: TestClient) -> None:
    """The domain's ValueErrors are reasons written for the caller, and stay 422."""
    token = client.post("/api/v1/gardens",
                        json={"name": "G", "latitude": 51.2564, "longitude": 7.1501}
                        ).json()["share_token"]
    r = client.post(f"/api/v1/gardens/{token}/beds",
                    json={"name": "Linie", "polygon": [[0, 0], [1, 1]]})
    assert r.status_code == 422
    assert "at least" in r.json()["detail"]
