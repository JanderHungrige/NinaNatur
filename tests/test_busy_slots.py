"""Busy, not broken — Wave 20, feature 5, part 2: a full house says so.

The three expensive routes each cost seconds of CPU, and the host has two cores.
Without a cap a burst queues in the thread pool until every request — the cheap
page loads included — waits behind it. With one, the request that would have
queued is told at once, with a 429 and when to try again, and the site stays
answerable for everybody else.

The per-visitor rate limit (feature 1) answers *how often one visitor may ask*;
this answers *how much may run at once*, whoever is asking.
"""
from __future__ import annotations

import inspect
import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import gardens, ratelimit
from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app, healthz

PROXY = ("172.27.0.1", 50000)
VISITOR = {"x-forwarded-for": "198.51.100.7", "x-forwarded-proto": "https"}
ROUTES = [("light", "/api/v1/gardens/{token}/light"),
          ("recompute", "/api/v1/gardens/{token}/recompute")]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


@pytest.fixture()
def full_house() -> Iterator[None]:
    """Every slot taken, as if the computations were already running."""
    for _ in range(ratelimit.HEAVY_SLOTS):
        assert ratelimit.HEAVY.acquire(blocking=False)
    yield
    for _ in range(ratelimit.HEAVY_SLOTS):
        ratelimit.HEAVY.release()


def _garden(client: TestClient) -> str:
    made = client.post("/api/v1/gardens", json={"name": "G", "latitude": 51.2564,
                                                "longitude": 7.1501})
    return str(made.json()["share_token"])


@pytest.mark.parametrize(("bucket", "path"), ROUTES)
def test_a_full_house_is_a_429_with_a_time_to_come_back(
    conn: sqlite3.Connection, full_house: None, bucket: str, path: str,
) -> None:
    client = TestClient(app, client=PROXY)
    token = _garden(client)
    answer = client.post(path.format(token=token), headers=VISITOR)
    assert answer.status_code == 429
    assert answer.json()["detail"] == ratelimit.BUSY
    assert int(answer.headers["retry-after"]) > 0


@pytest.mark.parametrize(("bucket", "path"), ROUTES)
def test_being_turned_away_for_a_full_house_costs_the_visitor_nothing(
    conn: sqlite3.Connection, full_house: None, bucket: str, path: str,
) -> None:
    """It was not their request that was too many, so it must not count
    against their own limit."""
    client = TestClient(app, client=PROXY)
    token = _garden(client)
    client.post(path.format(token=token), headers=VISITOR)
    counted = conn.execute("SELECT count(*) FROM rate_limit WHERE bucket = ?",
                           (bucket,)).fetchone()[0]
    assert counted == 0


def test_a_full_house_turns_the_map_import_away_before_it_asks_anybody(
    conn: sqlite3.Connection, full_house: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ninanatur.api import geo

    calls = {"n": 0}

    def counted(*_a: object, **_k: object) -> list[object]:
        calls["n"] += 1
        return []

    monkeypatch.setattr(geo, "buildings_in", counted)
    monkeypatch.setattr(geo, "streets_in", counted)
    outline = [{"lat": 51.2564, "lon": 7.1501}, {"lat": 51.2565, "lon": 7.1501},
               {"lat": 51.2565, "lon": 7.1503}]
    answer = TestClient(app, client=PROXY).post(
        "/api/v1/gardens/from-map", json={"name": "G", "outline": outline}, headers=VISITOR)
    assert answer.status_code == 429
    assert calls["n"] == 0, "a full house still asked Overpass"


def test_the_last_free_slot_is_used(conn: sqlite3.Connection) -> None:
    """The cap refuses the one too many, not the last one that fits."""
    client = TestClient(app, client=PROXY)
    token = _garden(client)
    for _ in range(ratelimit.HEAVY_SLOTS - 1):
        assert ratelimit.HEAVY.acquire(blocking=False)
    try:
        answer = client.post(f"/api/v1/gardens/{token}/recompute", headers=VISITOR)
    finally:
        for _ in range(ratelimit.HEAVY_SLOTS - 1):
            ratelimit.HEAVY.release()
    assert answer.status_code == 200


def test_a_computation_that_fails_gives_its_slot_back(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Otherwise every crash would shrink the house by one, until it answered
    nobody at all."""
    client = TestClient(app, client=PROXY, raise_server_exceptions=False)
    token = _garden(client)

    def broken(*_a: object, **_k: object) -> None:
        raise RuntimeError("the computation fell over")

    monkeypatch.setattr(gardens, "recompute_light", broken)
    for _ in range(ratelimit.HEAVY_SLOTS + 1):
        assert client.post(f"/api/v1/gardens/{token}/recompute",
                           headers=VISITOR).status_code == 500
    monkeypatch.undo()
    assert client.post(f"/api/v1/gardens/{token}/recompute",
                       headers=VISITOR).status_code == 200


def test_the_probe_does_not_wait_for_a_thread() -> None:
    """A sync handler runs in the same thread pool the computations fill, so a
    busy app used to look like a dead one to the deploy cron and the proxy.
    On the event loop it answers regardless."""
    assert inspect.iscoroutinefunction(healthz)
