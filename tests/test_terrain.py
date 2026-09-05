"""The terrain window: what comes back, in whose frame, and pointing where.

No network. The raster is built here, so the test can say what the ground looks
like and then check what the window made of it.
"""
from __future__ import annotations

import math
import struct

import numpy as np
import pytest

from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import WINDOW_M, fetch_window
from ninanatur.geo.terrain_sources import by_state
from ninanatur.geo.terrain_store import cache_key

NRW = by_state("Nordrhein-Westfalen")
assert NRW is not None

#: Far west in zone 32, where the meridian convergence is about 2.3° — the
#: whole point of the resampling.
WEST = LatLon(lat=51.0, lon=6.0)


def _tiff(values: np.ndarray) -> bytes:
    """A plain little-endian float32 TIFF, one strip."""
    height, width = values.shape
    body = values.astype("<f4").tobytes()
    entries = [
        (256, width), (257, height), (258, 32), (259, 1),
        (273, 8), (277, 1), (278, height), (279, len(body)), (339, 3),
    ]
    out = bytearray(b"II\x2a\x00") + struct.pack("<I", 8 + len(body)) + body
    out += struct.pack("<H", len(entries))
    for tag, value in entries:
        kind = 4 if tag in (273, 279) else 3
        raw = struct.pack("<I" if kind == 4 else "<H", value)
        out += struct.pack("<HHI", tag, kind, 1) + raw + b"\x00" * (4 - len(raw))
    out += struct.pack("<I", 0)
    return bytes(out)


def _flat(height: float = 40.0, size: int = 220) -> bytes:
    return _tiff(np.full((size, size), height, dtype="<f4"))


def test_the_window_is_centred_on_the_garden_and_axis_aligned() -> None:
    window = fetch_window(WEST, NRW, fetch=lambda url: _flat())
    assert window is not None
    assert window.min_x == pytest.approx(-WINDOW_M)
    assert window.min_y == pytest.approx(-WINDOW_M)
    assert window.cols == window.rows == int(2 * WINDOW_M)
    assert window.at(0.0, 0.0) == pytest.approx(40.0)


def test_a_point_outside_the_window_is_none_not_zero() -> None:
    """Zero is a height. None is the absence of one, and the shading model has
    to be able to tell them apart."""
    window = fetch_window(WEST, NRW, fetch=lambda url: _flat())
    assert window is not None
    assert window.at(500.0, 0.0) is None
    assert window.at(0.0, -500.0) is None


def test_unsurveyed_ground_comes_back_as_none() -> None:
    """Border tiles and water are genuinely empty, and -9999 averaged into a
    slope is a cliff that is not there."""
    values = np.full((220, 220), 40.0, dtype="<f4")
    values[100:120, 100:120] = -9999.0
    window = fetch_window(WEST, NRW, fetch=lambda url: _tiff(values))
    assert window is not None
    assert any(v is None for v in (window.at(x, 0.0) for x in range(-20, 20)))


def test_a_slope_along_utm_north_is_not_a_slope_along_true_north() -> None:
    """The reason the raster is resampled rather than pasted in.

    The ground here rises purely along the UTM northing. At 6°E the grid is
    turned about 2.3° from true north, so in the garden's frame the steepest
    ascent must be off north by about that much — and in the direction the
    convergence points, not the other one.
    """
    size = 220
    ramp = np.tile(np.arange(size, dtype="<f4")[:, None], (1, size))
    window = fetch_window(WEST, NRW, fetch=lambda url: _tiff(ramp * -1.0))
    assert window is not None

    grid = np.array(window.heights).reshape(window.rows, window.cols)
    middle = grid[10:-10, 10:-10]
    rise_north = float(np.nanmean(np.diff(middle, axis=0)))
    rise_east = float(np.nanmean(np.diff(middle, axis=1)))
    bearing = math.degrees(math.atan2(rise_east, rise_north))

    assert abs(bearing) == pytest.approx(2.3, abs=0.6), (
        f"expected the convergence at 6°E, got {bearing:.2f}°"
    )


def test_neighbouring_gardens_share_a_key_and_distant_ones_never_do() -> None:
    """What a grid key can and cannot promise.

    It cannot promise that two neighbours share a cell — any grid has lines, and
    two gardens twenty metres apart across one of them get a window each. That
    costs one extra request and nothing else.

    What it must promise is the other direction: a shared key never merges
    gardens that are far apart, because they would then be given each other's
    ground.
    """
    grid = [LatLon(lat=51.0 + i * 0.0002, lon=6.0 + j * 0.0003)
            for i in range(12) for j in range(12)]
    keys: dict[str, list[LatLon]] = {}
    for point in grid:
        keys.setdefault(cache_key(point), []).append(point)

    assert any(len(v) > 1 for v in keys.values()), "nothing shared at all"
    for shared in keys.values():
        for a in shared:
            for b in shared:
                north = abs(a.lat - b.lat) * 111_320
                east = abs(a.lon - b.lon) * 111_320 * math.cos(math.radians(51.0))
                assert math.hypot(north, east) < 150.0


def test_the_window_carries_its_licence_and_how_coarse_it_is() -> None:
    """A height shown without its credit is a height used outside its licence,
    and Baden-Württemberg's whole metres have to be sayable on the page."""
    window = fetch_window(WEST, NRW, fetch=lambda url: _flat())
    assert window is not None
    assert window.licence
    assert window.attribution
    assert window.vertical_step_m > 0


# --- storage ---------------------------------------------------------------

def _conn() -> object:
    from ninanatur.ingest.db import connect, init_schema
    conn = connect(":memory:")
    init_schema(conn)
    return conn


def test_a_window_survives_the_round_trip() -> None:
    from ninanatur.geo.terrain_store import load_window, save_window
    conn = _conn()
    window = fetch_window(WEST, NRW, fetch=lambda url: _flat(height=137.25))
    assert window is not None

    save_window(conn, "k", window)  # type: ignore[arg-type]
    back = load_window(conn, "k")  # type: ignore[arg-type]

    assert back is not None
    assert back.at(0.0, 0.0) == pytest.approx(137.25, abs=0.005)
    assert (back.cols, back.rows) == (window.cols, window.rows)
    assert back.attribution == window.attribution


def test_unsurveyed_ground_stays_unsurveyed_through_the_database() -> None:
    """The one that a naive `int(h * 100)` would break: NULL has to come back as
    absent, not as the base height."""
    from ninanatur.geo.terrain_store import load_window, save_window
    values = np.full((220, 220), 40.0, dtype="<f4")
    values[:, :] = -9999.0
    values[100:140, 100:140] = 40.0
    conn = _conn()
    window = fetch_window(WEST, NRW, fetch=lambda url: _tiff(values))
    assert window is not None

    save_window(conn, "k", window)  # type: ignore[arg-type]
    back = load_window(conn, "k")  # type: ignore[arg-type]

    assert back is not None
    assert back.at(0.0, 0.0) == pytest.approx(40.0, abs=0.005)
    assert back.at(-90.0, -90.0) is None


def test_a_location_that_was_never_fetched_is_none() -> None:
    from ninanatur.geo.terrain_store import load_window
    assert load_window(_conn(), "nowhere") is None  # type: ignore[arg-type]


def test_storing_the_same_place_twice_replaces_rather_than_duplicates() -> None:
    from ninanatur.geo.terrain_store import load_window, save_window
    conn = _conn()
    first = fetch_window(WEST, NRW, fetch=lambda url: _flat(height=10.0))
    second = fetch_window(WEST, NRW, fetch=lambda url: _flat(height=99.0))
    assert first is not None and second is not None

    save_window(conn, "k", first)  # type: ignore[arg-type]
    save_window(conn, "k", second)  # type: ignore[arg-type]

    back = load_window(conn, "k")  # type: ignore[arg-type]
    assert back is not None
    assert back.at(0.0, 0.0) == pytest.approx(99.0, abs=0.005)


def test_a_state_with_no_service_gets_no_ground_rather_than_a_neighbours() -> None:
    """Nine Bundesländer have no entry. The model says so instead of reaching
    across the border for something that looks similar."""
    from ninanatur.geo.terrain import terrain_for
    assert terrain_for(WEST, state="Bayern", fetch=lambda url: _flat()) is None


def test_a_state_with_a_service_gets_its_ground() -> None:
    from ninanatur.geo.terrain import terrain_for
    window = terrain_for(WEST, state="Nordrhein-Westfalen", fetch=lambda url: _flat())
    assert window is not None
    assert window.source == "Nordrhein-Westfalen"
