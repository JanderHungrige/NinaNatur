"""Fetching a garden's ground once, and surviving it not being there.

Every path here is offline: the point is what happens around the request, not
the request.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden import terrain_sync
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.geo.terrain_store import cache_key, load_horizon, load_window
from ninanatur.ingest.db import connect, init_schema


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:")
    init_schema(connection)
    yield connection


def _garden(conn: sqlite3.Connection, lat: float = 51.0, lon: float = 6.0) -> object:
    garden_id = create_garden(conn, name="G", latitude=lat, longitude=lon)
    return load_garden(conn, garden_id)


def _window() -> TerrainWindow:
    return TerrainWindow(
        min_x=-5.0, min_y=-5.0, cell_m=1.0, cols=10, rows=10,
        heights=[100.0] * 100, source="Nordrhein-Westfalen", licence="dl-de/zero-2-0",
        attribution="© Geobasis NRW", vertical_step_m=0.01,
    )


def _patch(monkeypatch: pytest.MonkeyPatch, **kwargs: object) -> None:
    """Replace the three things that would otherwise reach the network."""
    defaults = {
        "state_at": lambda *_: "Nordrhein-Westfalen",
        "fetch_window": lambda *_a, **_k: _window(),
        "horizon_ring": lambda *_a, **_k: [1.5] * 360,
    }
    for name, fallback in defaults.items():
        monkeypatch.setattr(terrain_sync, name, kwargs.get(name, fallback))


def test_a_garden_gets_its_ground_and_its_horizon(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(monkeypatch)
    garden = _garden(conn)

    assert terrain_sync.ensure_terrain(conn, garden) is True  # type: ignore[arg-type]

    key = cache_key(LatLon(lat=51.0, lon=6.0))
    assert load_window(conn, key) is not None
    assert load_horizon(conn, key) is not None


def test_the_second_garden_in_the_street_costs_nothing(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reason the key is a location. Two neighbours share one window, and
    the survey is asked once."""
    calls = {"n": 0}

    def counted(*_a: object, **_k: object) -> TerrainWindow:
        calls["n"] += 1
        return _window()

    _patch(monkeypatch, fetch_window=counted)
    terrain_sync.ensure_terrain(conn, _garden(conn))  # type: ignore[arg-type]
    terrain_sync.ensure_terrain(conn, _garden(conn, lat=51.00005, lon=6.00005))  # type: ignore[arg-type]

    assert calls["n"] == 1


def test_a_state_with_no_service_leaves_the_garden_flat(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nine Bundesländer have none. Flat is what every garden was yesterday, and
    it is not an error the gardener has to care about."""
    _patch(monkeypatch, state_at=lambda *_: "Bayern")

    assert terrain_sync.ensure_terrain(conn, _garden(conn)) is False  # type: ignore[arg-type]
    assert load_window(conn, cache_key(LatLon(lat=51.0, lon=6.0))) is None


def test_a_survey_that_fails_leaves_the_garden_flat_rather_than_broken(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: object, **_k: object) -> TerrainWindow:
        raise TimeoutError("the survey did not answer")

    _patch(monkeypatch, fetch_window=boom)

    assert terrain_sync.ensure_terrain(conn, _garden(conn)) is False  # type: ignore[arg-type]


def test_a_failed_horizon_does_not_throw_away_a_window_that_worked(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two requests, two fates. The window is the one every garden uses."""
    def boom(*_a: object, **_k: object) -> list[float]:
        raise TimeoutError("no")

    _patch(monkeypatch, horizon_ring=boom)

    assert terrain_sync.ensure_terrain(conn, _garden(conn)) is True  # type: ignore[arg-type]
    key = cache_key(LatLon(lat=51.0, lon=6.0))
    assert load_window(conn, key) is not None
    assert load_horizon(conn, key) is None
