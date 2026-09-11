"""Busy, not broken — Wave 20, feature 5, part 4: the light in a process of its own.

Measured on the preview on 2026-09-11, before this: a garden of 87 elements
took 12.9 s to relight alone; two at once took **37.8 s each**, and a plain
`GET` of a garden went from 8 ms to a median of 220 ms and a worst of 1.05 s
while they ran. The light is pure Python arithmetic, and in the serving process
it holds the interpreter lock that every other request needs.

In a process of its own it holds nobody's lock but its own. These tests check
that it really runs elsewhere, that elsewhere computes exactly what here did,
and that the ways a second process can go wrong — a lock the request still
holds, a database only this process can see, a worker that dies — do not.
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import ratelimit
from ninanatur.api.deps import get_connection
from ninanatur.garden import light_worker, lighting
from ninanatur.garden.store import create_garden
from ninanatur.ingest.db import DB_PATH_ENV, connect, init_schema
from ninanatur.web.app import app

PROXY = ("172.27.0.1", 50000)
VISITOR = {"x-forwarded-for": "198.51.100.9", "x-forwarded-proto": "https"}


@pytest.fixture()
def pool() -> Iterator[None]:
    light_worker.start()
    yield
    light_worker.stop()


@pytest.fixture()
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "ninanatur.sqlite"
    monkeypatch.setenv(DB_PATH_ENV, str(path))
    conn = connect(path)
    init_schema(conn)
    conn.close()
    return path


def _drawn(client: TestClient) -> str:
    """A garden with something to shade and something to be shaded."""
    token = str(client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 51.2564, "longitude": 7.1501}).json()["share_token"])
    client.post(f"/api/v1/gardens/{token}/beds",
                json={"name": "B", "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]]})
    client.post(f"/api/v1/gardens/{token}/obstacles", json={"kind": "tree", "x": 2, "y": 6})
    return token


# --- it runs elsewhere, and elsewhere is right --------------------------------------

def test_the_pool_is_a_process_of_its_own(pool: None) -> None:
    assert light_worker.running()
    worker = light_worker.warm_pid()
    assert worker is not None and worker != os.getpid()


def test_a_relight_through_the_app_runs_in_the_worker_and_agrees_with_one_run_here(
    db: Path,
) -> None:
    with TestClient(app, client=PROXY) as client:
        token = _drawn(client)
        assert client.post(f"/api/v1/gardens/{token}/recompute",
                           headers=VISITOR).status_code == 200
        assert light_worker.last_worker_pid() not in (None, os.getpid())

    conn = connect(db)
    try:
        there = conn.execute("SELECT sun_hours FROM element WHERE ellenberg_l IS NOT NULL"
                             ).fetchall()
        garden_id = conn.execute("SELECT garden_id FROM garden").fetchone()[0]
        lighting.recompute_light(conn, garden_id)  # the same job, in this process
        here = conn.execute("SELECT sun_hours FROM element WHERE ellenberg_l IS NOT NULL"
                            ).fetchall()
    finally:
        conn.close()
    assert [tuple(r) for r in there] == [tuple(r) for r in here] != []


# --- the ways a second process goes wrong -------------------------------------------

def test_the_requests_own_write_does_not_lock_the_worker_out(db: Path, pool: None) -> None:
    """The worker has a connection of its own. A write the request has not
    committed would hold the lock it needs, and it would wait out the busy
    timeout and fail with 'database is locked'."""
    conn = connect(db)
    try:
        garden_id = create_garden(conn, name="G", latitude=51.2564, longitude=7.1501,
                                  owner_id=None)
        conn.execute("UPDATE garden SET name = 'renamed' WHERE garden_id = ?", (garden_id,))
        assert light_worker.recompute_light(conn, garden_id) == 0
    finally:
        conn.close()
    other = sqlite3.connect(db)
    try:
        assert other.execute("SELECT name FROM garden").fetchone()[0] == "renamed"
    finally:
        other.close()


def test_a_database_only_this_process_can_see_is_computed_here(pool: None) -> None:
    """An in-memory database — every API test's — has no file to open elsewhere."""
    conn = connect(":memory:")
    init_schema(conn)
    garden_id = create_garden(conn, name="G", latitude=51.2564, longitude=7.1501,
                              owner_id=None)
    before = light_worker.last_worker_pid()
    assert light_worker.recompute_light(conn, garden_id) == 0
    assert light_worker.last_worker_pid() == before


def test_a_worker_that_dies_is_replaced(db: Path) -> None:
    """Killed for memory, say. The next relight must not inherit a broken pool."""
    with TestClient(app, client=PROXY) as client:
        token = _drawn(client)
        # What the kernel's OOM killer would do, from inside the worker.
        pool = light_worker._pool
        assert pool is not None
        with pytest.raises(BrokenProcessPool):
            pool.submit(os._exit, 3).result(timeout=30)
        assert client.post(f"/api/v1/gardens/{token}/recompute",
                           headers=VISITOR).status_code == 200
        assert light_worker.last_worker_pid() not in (None, os.getpid())


def test_there_is_a_worker_for_every_slot() -> None:
    """Fewer, and a relight holding a slot would queue for a process; more, and
    they would sit idle holding memory the host shares with four projects."""
    assert light_worker.DEFAULT_WORKERS == ratelimit.HEAVY_SLOTS


def test_no_workers_when_told_so(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(light_worker.WORKERS_ENV, "0")
    try:
        assert light_worker.start() is None
        assert not light_worker.running()
    finally:
        light_worker.stop()


def test_the_app_starts_the_pool_and_stops_it(db: Path) -> None:
    with TestClient(app):
        assert light_worker.running()
    assert not light_worker.running()


# --- the month view: seconds of CPU on a GET ----------------------------------------

@pytest.fixture()
def memory_app() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


@pytest.fixture()
def full_house() -> Iterator[None]:
    for _ in range(ratelimit.HEAVY_SLOTS):
        assert ratelimit.HEAVY.acquire(blocking=False)
    yield
    for _ in range(ratelimit.HEAVY_SLOTS):
        ratelimit.HEAVY.release()


def test_a_month_view_waits_for_a_slot_like_every_other_computation(
    memory_app: sqlite3.Connection, full_house: None,
) -> None:
    """A month is computed on the spot — about a quarter of a relight, seconds
    on a big garden — and it was the one computation nothing capped."""
    client = TestClient(app, client=PROXY)
    token = _drawn(client)
    answer = client.get(f"/api/v1/gardens/{token}/light?month=3", headers=VISITOR)
    assert answer.status_code == 429
    assert int(answer.headers["retry-after"]) > 0


def test_the_stored_map_is_not_a_computation_and_is_never_turned_away(
    memory_app: sqlite3.Connection, full_house: None,
) -> None:
    client = TestClient(app, client=PROXY)
    token = _drawn(client)
    assert client.get(f"/api/v1/gardens/{token}/light", headers=VISITOR).status_code == 200


def test_a_month_view_is_limited_per_visitor(
    memory_app: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(ratelimit.LIMITS, "month", (3, 600.0))
    client = TestClient(app, client=PROXY)
    token = _drawn(client)
    url = f"/api/v1/gardens/{token}/light?month=4"
    codes = [client.get(url, headers=VISITOR).status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429
    other = {**VISITOR, "x-forwarded-for": "198.51.100.10"}
    assert client.get(url, headers=other).status_code == 200
