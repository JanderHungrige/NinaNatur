"""What the log knows — Wave 20, feature 6, part 1.

Measured on 2026-09-11 before this: production's container log held a line for
every request with the visitor's full address and the whole path — and on the
garden routes the path *is* the share token, the one thing standing between a
garden and anybody. `upstream_failed` wrote the same path into its warning.
There was no logging configuration at all, so the app's own INFO lines went
nowhere, and nothing told a failed login apart from a page view.

Now: one access line per request, written by the app and naming the route
rather than the path — the token masked by construction, with a short hash so
one garden's lines can still be followed; a request id in and out of every
request and on every line written while it runs; a security channel for failed
logins, refusals and server errors; addresses kept only to their network; JSON
lines from a config the image starts uvicorn with; and a formatter that masks
any token the route template did not.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import gardens, ratelimit
from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web import logs
from ninanatur.web.app import app

ROOT = Path(__file__).resolve().parent.parent
PROXY = ("172.27.0.1", 50000)
VISITOR = {"x-forwarded-for": "198.51.100.7", "x-forwarded-proto": "https"}
GOOD = {"username": "gaertnerin", "password": "ein langes Passwort"}
#: The shape of `secrets.token_urlsafe(32)`: 43 characters of the URL-safe alphabet.
TOKENISH = "Zq3mB9xT2vLw8pR4sN6yH1cK5dF7gJ0aE2uI4oP6tY8"


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


@pytest.fixture()
def seen(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.INFO, logger="ninanatur")
    return caplog


def _client(**kwargs: Any) -> TestClient:
    return TestClient(app, client=PROXY, **kwargs)


def _garden(client: TestClient) -> str:
    made = client.post("/api/v1/gardens", headers=VISITOR,
                       json={"name": "G", "latitude": 51.2564, "longitude": 7.1501})
    return str(made.json()["share_token"])


def _only(caplog: pytest.LogCaptureFixture, name: str) -> logging.LogRecord:
    found = [r for r in caplog.records if r.name == name]
    assert len(found) == 1, f"{name}: {[r.getMessage() for r in found]}"
    return found[0]


def _fields(record: logging.LogRecord) -> dict[str, Any]:
    return dict(getattr(record, "fields", {}))


def _line(record: logging.LogRecord) -> str:
    return logs.JsonFormatter().format(record)


# --- the access line -------------------------------------------------------------

def test_an_access_line_names_the_route_and_never_the_token(
    conn: sqlite3.Connection, seen: pytest.LogCaptureFixture,
) -> None:
    client = _client()
    token = _garden(client)
    seen.clear()
    assert client.get(f"/api/v1/gardens/{token}", headers=VISITOR).status_code == 200
    line = _only(seen, "ninanatur.access")
    fields = _fields(line)
    assert fields["path"] == "/api/v1/gardens/{token}"
    assert fields["garden"] == hashlib.sha256(token.encode()).hexdigest()[:8]
    assert (fields["method"], fields["status"]) == ("GET", 200)
    assert token not in _line(line)


def test_a_path_no_route_matches_is_masked_all_the_same(seen: pytest.LogCaptureFixture) -> None:
    answer = _client().get(f"/api/v1/gardens/{TOKENISH}/nothing-here", headers=VISITOR)
    assert answer.status_code == 404
    line = _only(seen, "ninanatur.access")
    assert _fields(line)["path"] == "/api/v1/gardens/{token}/nothing-here"
    assert TOKENISH not in _line(line)


def test_an_address_is_kept_only_to_its_network(seen: pytest.LogCaptureFixture) -> None:
    _client().get("/healthz", headers=VISITOR)
    assert _fields(_only(seen, "ninanatur.access"))["client"] == "198.51.100.0"


@pytest.mark.parametrize(("address", "kept"), [
    ("198.51.100.7", "198.51.100.0"),
    ("2001:db8:1234:5678::1", "2001:db8:1234::"),
    ("unknown", "unknown"),
])
def test_the_network_of_an_address(address: str, kept: str) -> None:
    assert logs.network_of(address) == kept


# --- the request id ------------------------------------------------------------------

def test_every_answer_carries_a_request_id_and_its_access_line_the_same(
    seen: pytest.LogCaptureFixture,
) -> None:
    answer = _client().get("/healthz")
    request_id = answer.headers["x-request-id"]
    assert len(request_id) >= 8
    assert getattr(_only(seen, "ninanatur.access"), "request_id", None) == request_id


@pytest.mark.parametrize(("incoming", "kept"), [
    ("npm-4f2a9c1e", True),
    ("a" * 200, False),
    ("bad id; drop", False),
])
def test_a_sane_incoming_request_id_is_kept_and_anything_else_replaced(
    incoming: str, kept: bool,
) -> None:
    answer = _client().get("/healthz", headers={"x-request-id": incoming})
    assert (answer.headers["x-request-id"] == incoming) is kept


def test_a_line_written_during_a_request_carries_that_requests_id(
    conn: sqlite3.Connection, seen: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(ratelimit.LIMITS, "login", (0, 300.0))  # every login refused
    answer = _client().post("/api/v1/sessions", json=GOOD, headers=VISITOR)
    assert answer.status_code == 429
    event = _only(seen, "ninanatur.security")
    line = _only(seen, "ninanatur.access")
    assert getattr(event, "request_id", None) == getattr(line, "request_id", None)
    assert getattr(line, "request_id", None) == answer.headers["x-request-id"]
    assert (_fields(event)["event"], _fields(event)["bucket"]) == ("rate_limited", "login")


# --- the security channel --------------------------------------------------------------

def test_a_failed_login_is_a_security_event_that_names_nobody(
    conn: sqlite3.Connection, seen: pytest.LogCaptureFixture,
) -> None:
    client = _client()
    client.post("/api/v1/accounts", json=GOOD, headers=VISITOR)
    seen.clear()
    wrong = {**GOOD, "password": "falsch aber lang"}
    assert client.post("/api/v1/sessions", json=wrong, headers=VISITOR).status_code == 401
    event = _only(seen, "ninanatur.security")
    fields = _fields(event)
    assert fields["event"] == "login_failed"
    assert fields["client"] == "198.51.100.0"
    assert fields["account"] == hashlib.sha256(b"gaertnerin").hexdigest()[:8]
    written = _line(event)
    assert "gaertnerin" not in written and "falsch aber lang" not in written


def test_a_full_house_is_a_security_event(
    conn: sqlite3.Connection, seen: pytest.LogCaptureFixture,
) -> None:
    client = _client()
    token = _garden(client)
    for _ in range(ratelimit.HEAVY_SLOTS):
        assert ratelimit.HEAVY.acquire(blocking=False)
    try:
        seen.clear()
        assert client.post(f"/api/v1/gardens/{token}/recompute",
                           headers=VISITOR).status_code == 429
    finally:
        for _ in range(ratelimit.HEAVY_SLOTS):
            ratelimit.HEAVY.release()
    assert _fields(_only(seen, "ninanatur.security"))["event"] == "busy"


def test_a_server_error_is_a_security_event_that_names_its_route(
    conn: sqlite3.Connection, seen: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(raise_server_exceptions=False)
    token = _garden(client)

    def broken(*_a: object, **_k: object) -> None:
        raise RuntimeError("the computation fell over")

    monkeypatch.setattr(gardens, "recompute_light", broken)
    seen.clear()
    assert client.post(f"/api/v1/gardens/{token}/recompute", headers=VISITOR).status_code == 500
    event = _only(seen, "ninanatur.security")
    assert _fields(event)["event"] == "server_error"
    assert _fields(event)["path"] == "/api/v1/gardens/{token}/recompute"
    assert token not in _line(event)


# --- what is written, and how the image writes it ----------------------------------------

def test_the_formatter_masks_a_token_whatever_wrote_it() -> None:
    """`upstream_failed` logged `request.url.path` — on a garden route, the token."""
    record = logging.LogRecord(
        "ninanatur.web.security", logging.WARNING, __file__, 1,
        "upstream failure on %s %s: %r",
        ("POST", f"/api/v1/gardens/{TOKENISH}/light", "timeout"), None,
    )
    written = logs.JsonFormatter().format(record)
    line = json.loads(written)
    assert TOKENISH not in written
    assert "/api/v1/gardens/{token}/light" in line["msg"]
    assert (line["level"], line["logger"]) == ("WARNING", "ninanatur.web.security")


def test_the_image_starts_uvicorn_with_this_config_and_without_its_access_log() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert '"--log-config", "ninanatur/web/log_config.json"' in dockerfile
    assert '"--no-access-log"' in dockerfile


def test_the_log_config_writes_json_through_the_masking_formatter() -> None:
    config = json.loads((ROOT / "ninanatur/web/log_config.json").read_text())
    assert config["formatters"]["json"]["()"] == "ninanatur.web.logs.JsonFormatter"
    assert config["loggers"]["uvicorn.access"] == {"handlers": [], "propagate": False}
    assert config["disable_existing_loggers"] is False
    for section in ("formatters", "filters"):
        for spec in config[section].values():
            module, _, name = spec["()"].rpartition(".")
            assert hasattr(importlib.import_module(module), name), spec["()"]
