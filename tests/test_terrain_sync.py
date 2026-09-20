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


def _garden(conn: sqlite3.Connection, lat: float = 51.2564, lon: float = 7.1501) -> object:
    garden_id = create_garden(conn, name="G", latitude=lat, longitude=lon)
    return load_garden(conn, garden_id)


def _window() -> TerrainWindow:
    return TerrainWindow(
        min_x=-5.0, min_y=-5.0, cell_m=1.0, cols=10, rows=10,
        heights=[100.0] * 100, source="Nordrhein-Westfalen", licence="dl-de/zero-2-0",
        attribution="© Geobasis NRW", vertical_step_m=0.01,
    )


def _tile_window() -> TerrainWindow:
    """What a Bavarian garden gets from its state's own tiles."""
    return TerrainWindow(
        min_x=-5.0, min_y=-5.0, cell_m=1.0, cols=10, rows=10,
        heights=[520.0] * 100, source="BY", licence="CC-BY-4.0",
        attribution="Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de",
        vertical_step_m=0.01,
    )


def _patch(monkeypatch: pytest.MonkeyPatch, **kwargs: object) -> None:
    """Replace the three things that would otherwise reach the network."""
    defaults = {
        "state_at": lambda *_: "Nordrhein-Westfalen",
        "fetch_window": lambda *_a, **_k: _window(),
        "horizon_ring": lambda *_a, **_k: [1.5] * 360,
        # The tile tier under the services (doc 103) and the Copernicus ring
        # under them both (doc 104); nothing here may reach a portal either.
        "_from_tiles": lambda *_a, **_k: _tile_window(),
        "far_ring": lambda *_a, **_k: [3.5] * 360,
    }
    for name, fallback in defaults.items():
        monkeypatch.setattr(terrain_sync, name, kwargs.get(name, fallback))


def test_a_garden_gets_its_ground_and_its_horizon(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(monkeypatch)
    garden = _garden(conn)

    assert terrain_sync.ensure_terrain(conn, garden) is True  # type: ignore[arg-type]

    key = cache_key(LatLon(lat=51.2564, lon=7.1501))
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
    terrain_sync.ensure_terrain(conn, _garden(conn, lat=51.2565, lon=7.1502))  # type: ignore[arg-type]

    assert calls["n"] == 1


def test_a_state_with_neither_a_service_nor_tiles_leaves_the_garden_flat(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flat is what every garden was yesterday, and it is not an error the
    gardener has to care about.

    No Bundesland is this case any more — see the test below — so the state
    named here is one that does not exist. The behaviour still has to hold: a
    garden somewhere this project has no source for keeps the flat world, and
    says nothing about it."""
    _patch(monkeypatch, state_at=lambda *_: "Vorarlberg")

    assert terrain_sync.ensure_terrain(conn, _garden(conn)) is False  # type: ignore[arg-type]
    assert load_window(conn, cache_key(LatLon(lat=51.2564, lon=7.1501))) is None


def test_a_state_with_no_service_but_tiles_gets_its_ground_from_them(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wave 25's point (doc 103): Bayern runs no coverage service anybody may
    use and publishes every square kilometre as a file. A Munich garden stops
    living on a flat world, and its page says whose ground it is standing on."""
    _patch(monkeypatch, state_at=lambda *_: "Bayern")
    garden = _garden(conn, lat=48.137, lon=11.575)

    assert terrain_sync.ensure_terrain(conn, garden) is True  # type: ignore[arg-type]

    key = cache_key(LatLon(lat=48.137, lon=11.575))
    stored = load_window(conn, key)
    assert stored is not None
    assert stored.licence == "CC-BY-4.0"
    assert "Bayerische Vermessungsverwaltung" in stored.attribution


def test_a_state_with_no_service_still_gets_a_horizon(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Feature 2 (doc 104): nine Bundesländer have no coverage service and until
    now had no ring at all — the sun set on the plot at the astronomical hour,
    whatever the hill to the south-west was doing. Copernicus GLO-30 is 30 m
    everywhere, which places a ridge and not a hedge, which is all a ring is."""
    _patch(monkeypatch, state_at=lambda *_: "Bayern")
    key = cache_key(LatLon(lat=48.137, lon=11.575))

    terrain_sync.ensure_terrain(conn, _garden(conn, lat=48.137, lon=11.575))  # type: ignore[arg-type]

    assert load_horizon(conn, key) == [3.5] * 360
    whose = conn.execute("SELECT source FROM terrain_horizon WHERE place_key = ?",
                         (key,)).fetchone()[0]
    assert whose == "Copernicus GLO-30"


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
    key = cache_key(LatLon(lat=51.2564, lon=7.1501))
    assert load_window(conn, key) is not None
    assert load_horizon(conn, key) is None


def test_nothing_is_fetched_while_the_location_is_rounded(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A garden created before 2026-09-07 holds coordinates rounded to 0.1°. A
    window fetched six kilometres away is worse than no window, because it is
    confidently wrong — so that garden keeps the flat assumption it had before
    Wave 17, and the page says so. Nothing is even asked of the network."""
    calls = {"n": 0}

    def counted(*_a: object, **_k: object) -> None:
        calls["n"] += 1
        raise AssertionError("should not have been reached")

    monkeypatch.setattr(terrain_sync, "state_at", counted)
    legacy = _garden(conn, lat=51.3, lon=7.2)

    assert terrain_sync.ensure_terrain(conn, legacy) is False  # type: ignore[arg-type]
    assert calls["n"] == 0


def test_a_window_stored_under_the_old_rounding_is_not_served_either(
    conn: sqlite3.Connection,
) -> None:
    """Guarding the fetch was never enough.

    Windows fetched before the change are still in the database, keyed by the
    rounded location — so every garden near Wuppertal would still be served the
    same wrong hillside. Readers go through `ground_for`, which is where the
    check lives.
    """
    from ninanatur.geo.terrain_store import save_window

    precise = LatLon(lat=51.2564, lon=7.1501)
    legacy = LatLon(lat=51.3, lon=7.2)
    for anchor in (precise, legacy):
        save_window(conn, cache_key(anchor), _window())

    assert terrain_sync.ground_for(conn, precise) is not None
    assert terrain_sync.ground_for(conn, legacy) is None
    assert terrain_sync.horizon_for(conn, legacy) is None


def test_every_bundesland_now_has_ground() -> None:
    """Wave 25's whole point, as an assertion rather than a claim.

    Before it, nine of the sixteen states had no terrain at all and a garden
    there was computed on a flat world. Each one arrived by a different route —
    a coverage service, a computable tile, a name out of the state's own list,
    or a member of a whole-region archive — and this does not care which, only
    that every state has one.

    If this ever fails, a state has withdrawn something and the health check
    (doc 109) will have said so first.
    """
    from geokachel.terrain_sources import by_state as service
    from geokachel.tile_sources import STATES, ground_tiles_for, name_of

    without = [name_of(key) for key in STATES
               if ground_tiles_for(key) is None and service(name_of(key)) is None]
    assert without == [], f"no ground for {', '.join(without)}"
    assert len(STATES) == 16
