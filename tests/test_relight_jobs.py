"""A relight longer than a request should wait — doc 65, the owner's report of
2026-09-28.

The first "Sonne & Schatten" at a place reads the ground, the buildings and
the laser before the light; on the preview that ran past its proxy's 90 s,
the page got a 504 and showed nothing while the server went on, and a second
press started it all again. The relight runs as a job now: done within the
wait, the answer is the map; not, it is 202, and `/light/status` says when it
is done — or that it failed. A second press waits for the same job.

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
    monkeypatch.setattr(relight_jobs, "WAIT_S", 0.3)
    # The jobs are the process's, by garden id — which every test's database
    # starts again at 1.
    monkeypatch.setattr(relight_jobs, "_jobs", {})
    yield TestClient(app)
    app.dependency_overrides.clear()
    made.close()


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
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _garden(client)
    gate, calls = threading.Event(), []
    monkeypatch.setattr(routes, "relight", _relight(gate, calls))

    first = client.post(f"/api/v1/gardens/{token}/light")
    assert first.status_code == 202 and first.json() is None
    assert client.get(f"/api/v1/gardens/{token}/light/status").json() == {
        "running": True, "failed": False, "known": True}
    assert _free_slots() == ratelimit.HEAVY_SLOTS - 1, "the job holds its slot"

    again = client.post(f"/api/v1/gardens/{token}/light")
    assert again.status_code == 202
    assert len(calls) == 1, "a second press waits for the same job"
    assert _free_slots() == ratelimit.HEAVY_SLOTS - 1, "and takes no second slot"

    gate.set()
    assert _settled(client, token) == {"running": False, "failed": False, "known": True}
    assert client.get(f"/api/v1/gardens/{token}/light").json() is not None
    assert _free_slots() == ratelimit.HEAVY_SLOTS


def test_a_relight_that_fails_says_so_and_gives_its_slot_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _garden(client)
    gate, calls = threading.Event(), []
    monkeypatch.setattr(routes, "relight", _relight(gate, calls, fail=True))

    assert client.post(f"/api/v1/gardens/{token}/light").status_code == 202
    gate.set()
    assert _settled(client, token) == {"running": False, "failed": True, "known": True}
    assert client.get(f"/api/v1/gardens/{token}/light").json() is None
    assert _free_slots() == ratelimit.HEAVY_SLOTS

    # Pressed again, it starts afresh — and a relight that works clears it.
    monkeypatch.setattr(routes, "relight", _relight(None, calls))
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
