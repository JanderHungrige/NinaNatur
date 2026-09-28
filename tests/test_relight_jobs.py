"""A relight longer than a request should wait — doc 65, the owner's report of
2026-09-28.

The first "Sonne & Schatten" at a place reads the ground, the buildings and
the laser before the light; on the preview that ran past its proxy's 90 s,
the page got a 504 and showed nothing while the server went on, and a second
press started it all again. The relight runs as a job now: done within the
wait, the answer is the map; not, it is 202, and `/light/status` says when it
is done — or that it failed. A second press while it runs is answered 202 at
once, and asks the status like the first.

Against a database file, because the job opens one of its own: the in-memory
database every other API test uses is relit in the request, as before.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import light as routes
from ninanatur.api import ratelimit, relight_jobs
from ninanatur.api.deps import get_connection
from ninanatur.garden.lighting import recompute_light
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    path = tmp_path / "garden.sqlite"
    made = connect(str(path), same_thread=False)
    init_schema(made)
    made.commit()
    app.dependency_overrides[get_connection] = lambda: made
    # Long, so no test depends on how fast this machine relights a garden: a
    # test that wants a 202 holds its job at a gate and shortens the wait.
    monkeypatch.setattr(relight_jobs, "WAIT_S", 30.0)
    # The jobs are the process's, by share token.
    monkeypatch.setattr(relight_jobs, "_jobs", {})
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
    made.close()


@pytest.fixture()
def gate() -> Iterator[threading.Event]:
    """A relight held until the test lets it go — and let go however the test
    ends: a failed test once left its job parked, holding a heavy slot, and
    every test after it failed for that."""
    held = threading.Event()
    yield held
    held.set()
    for _ in range(200):
        if _free_slots() == ratelimit.HEAVY_SLOTS:
            return
        time.sleep(0.05)


def _garden(client: TestClient) -> str:
    token = str(client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.52, "longitude": 13.40}).json()["share_token"])
    client.post(f"/api/v1/gardens/{token}/beds", json={
        "name": "Beet", "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]]})
    client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "wall", "x": 2.0, "y": -2.0, "shape": "rect", "width": 6.0, "depth": 0.3,
        "height": 2.5})
    return token


def _relight(gate: threading.Event | None, calls: list[int],
             fail: bool = False) -> Callable[[sqlite3.Connection, int], None]:
    """The chain without the surveys: wait for the gate, then the light."""
    def relight(conn: sqlite3.Connection, garden_id: int) -> None:
        calls.append(garden_id)
        if gate is not None:
            assert gate.wait(10), "the test never opened the gate"
        if fail:
            raise RuntimeError("the laser service answered nonsense")
        recompute_light(conn, garden_id)
    return relight


def _free_slots() -> int:
    taken = 0
    while ratelimit.HEAVY.acquire(blocking=False):
        taken += 1
    for _ in range(taken):
        ratelimit.HEAVY.release()
    return taken


def _settled(client: TestClient, token: str) -> dict[str, bool]:
    for _ in range(200):
        state: dict[str, bool] = client.get(f"/api/v1/gardens/{token}/light/status").json()
        if not state["running"]:
            return state
        time.sleep(0.05)
    raise AssertionError("the relight never ended")


def test_a_long_relight_answers_202_goes_on_and_lands(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, gate: threading.Event,
) -> None:
    token = _garden(client)
    calls: list[int] = []
    monkeypatch.setattr(routes, "relight", _relight(gate, calls))
    monkeypatch.setattr(relight_jobs, "WAIT_S", 0.3)

    first = client.post(f"/api/v1/gardens/{token}/light")
    assert first.status_code == 202 and first.json() is None
    assert client.get(f"/api/v1/gardens/{token}/light/status").json() == {
        "running": True, "failed": False, "known": True}
    assert _free_slots() == ratelimit.HEAVY_SLOTS - 1, "the job holds its slot"

    gate.set()
    assert _settled(client, token) == {"running": False, "failed": False, "known": True}
    assert client.get(f"/api/v1/gardens/{token}/light").json() is not None
    assert _free_slots() == ratelimit.HEAVY_SLOTS


def test_a_press_while_one_runs_is_answered_at_once_and_holds_nothing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, gate: threading.Event,
) -> None:
    """It waited for the running job at first: a server thread held for 20 s
    with no slot and no count, and forty such presses stalled every page
    while the health check stayed green (review of c2ec593)."""
    token = _garden(client)
    calls: list[int] = []
    monkeypatch.setattr(routes, "relight", _relight(gate, calls))
    monkeypatch.setattr(relight_jobs, "WAIT_S", 0.3)
    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 202
    counted, slots = [], []
    monkeypatch.setattr(routes.ratelimit, "check", lambda *a: counted.append(a))
    real_slot = relight_jobs.heavy_now
    monkeypatch.setattr(relight_jobs, "heavy_now", lambda: slots.append(1) or real_slot())
    monkeypatch.setattr(relight_jobs, "WAIT_S", 30.0)

    began = time.perf_counter()
    again = client.post(f"/api/v1/gardens/{token}/light")

    assert again.status_code == 202 and time.perf_counter() - began < 5
    assert (calls, counted, slots) == ([calls[0]], [], []), "no second job, count or slot"
    gate.set()
    assert _settled(client, token)["failed"] is False


def test_a_relight_that_fails_says_so_and_gives_its_slot_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, gate: threading.Event,
) -> None:
    token = _garden(client)
    calls: list[int] = []
    monkeypatch.setattr(routes, "relight", _relight(gate, calls, fail=True))
    monkeypatch.setattr(relight_jobs, "WAIT_S", 0.3)

    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 202
    gate.set()
    assert _settled(client, token) == {"running": False, "failed": True, "known": True}
    assert client.get(f"/api/v1/gardens/{token}/light").json() is None
    assert _free_slots() == ratelimit.HEAVY_SLOTS

    # Pressed again, it starts afresh — and a relight that works clears it.
    monkeypatch.setattr(routes, "relight", _relight(None, calls))
    monkeypatch.setattr(relight_jobs, "WAIT_S", 30.0)
    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 200
    assert client.get(f"/api/v1/gardens/{token}/light/status").json() == {
        "running": False, "failed": False, "known": True}


def test_a_garden_this_server_holds_no_relight_of_says_so(client: TestClient) -> None:
    """After a restart — a deployment rolling the image — a job the page waits
    for is gone; "not running" alone read as done, and the page would have
    said the shade was computed with nothing new to show."""
    token = _garden(client)
    assert client.get(f"/api/v1/gardens/{token}/light/status").json() == {
        "running": False, "failed": False, "known": False}


def test_a_job_whose_connection_will_not_open_still_gives_its_slot_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Opened before its `try`, a connection that failed kept the slot for
    good: two such failures and every heavy route answered 429 (review of
    c2ec593)."""
    token = _garden(client)
    monkeypatch.setattr(routes, "relight", _relight(None, []))

    def refuse(*args: object, **kwargs: object) -> sqlite3.Connection:
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(relight_jobs, "connect", refuse)
    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 500
    assert _free_slots() == ratelimit.HEAVY_SLOTS
    assert client.get(f"/api/v1/gardens/{token}/light/status").json()["failed"] is True


def test_a_new_garden_never_joins_the_job_of_one_deleted_before_it(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, gate: threading.Event,
) -> None:
    """SQLite gives a deleted garden's id to the next one; keyed by it, a new
    garden's first press joined the dead garden's job (review of c2ec593)."""
    calls: list[int] = []
    monkeypatch.setattr(routes, "relight", _relight(gate, calls))
    monkeypatch.setattr(relight_jobs, "WAIT_S", 0.3)
    gone = _garden(client)
    assert client.post(f"/api/v1/gardens/{gone}/light").status_code == 202
    assert client.delete(f"/api/v1/gardens/{gone}").status_code == 204

    fresh = _garden(client)
    assert client.get(f"/api/v1/gardens/{fresh}/light/status").json()["known"] is False
    assert client.post(f"/api/v1/gardens/{fresh}/light").status_code == 202
    assert len(calls) == 2, "its press starts its own job"
    gate.set()
    _settled(client, fresh)


def test_a_quick_relight_answers_with_the_map_as_before(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _garden(client)
    monkeypatch.setattr(routes, "relight", _relight(None, []))

    answer = client.post(f"/api/v1/gardens/{token}/light")

    assert answer.status_code == 200
    assert answer.json()["cell_m"] > 0
    assert _free_slots() == ratelimit.HEAVY_SLOTS


def test_each_relight_says_in_the_log_what_took_how_long(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The question that had no answer from outside the server: which step of
    a first analysis was the slow one. Each run names every step's time."""
    from ninanatur.garden.models import ObstacleInput
    from ninanatur.garden.relight import relight
    from ninanatur.garden.store import add_obstacle, create_garden

    made = connect(":memory:")
    init_schema(made)
    garden_id = create_garden(made, name="G", latitude=52.52, longitude=13.40)
    add_obstacle(made, garden_id, ObstacleInput(kind="wall", x=0, y=0, shape="rect", width=4,
                                                depth=0.3, height=2.0, label="Mauer"))
    made.commit()
    with caplog.at_level("INFO", logger="ninanatur.garden.relight"):
        relight(made, garden_id)
    [line] = [r.getMessage() for r in caplog.records if r.name == "ninanatur.garden.relight"]
    for step in ("terrain", "buildings", "laser", "crown bases", "light"):
        assert f"{step} " in line and " s" in line, line
