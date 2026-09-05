"""The horizon ring: what it says, and where it correctly says nothing.

Built from rasters made here rather than fetched, so the test can put a hill in
a known direction at a known distance and check the angle that comes back is the
one trigonometry gives.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from ninanatur.geo.horizon import AZIMUTHS, RING_CELL_M, blocks, ring_from
from ninanatur.geo.projection import LatLon

#: Far west in zone 32, where grid north is about 2.3° off true north.
WEST = LatLon(lat=51.0, lon=6.0)
SIZE = 502
#: The north-west corner of a raster centred on WEST, in UTM.
from ninanatur.geo.utm import to_utm  # noqa: E402

_E, _N = to_utm(WEST.lat, WEST.lon, 32)
CORNER_E = _E - SIZE / 2 * RING_CELL_M
CORNER_N = _N + SIZE / 2 * RING_CELL_M


def _ring(values: np.ndarray) -> list[float]:
    return ring_from(values, WEST, 32, CORNER_E, CORNER_N)


def test_flat_country_has_no_horizon_and_that_is_the_right_answer() -> None:
    """The feature's own honest limit. In the North German Plain this changes no
    number at all, and a feature that appears to do nothing is otherwise
    indistinguishable from a broken one."""
    ring = _ring(np.full((SIZE, SIZE), 40.0))
    assert len(ring) == AZIMUTHS
    assert max(ring) == pytest.approx(0.0, abs=0.01)


def test_a_hill_to_the_south_shows_up_to_the_south() -> None:
    """1 km away and 200 m up is 11.3° — a hill that eats a Berlin midwinter
    noon, which is 14.1°."""
    values = np.full((SIZE, SIZE), 0.0)
    south = SIZE // 2 + int(1000 / RING_CELL_M)
    values[south - 2 : south + 3, :] = 200.0
    ring = _ring(values)

    assert ring[180] == pytest.approx(math.degrees(math.atan2(200.0, 1000.0)), abs=0.6)
    assert ring[0] == pytest.approx(0.0, abs=0.01)
    assert ring[90] == pytest.approx(0.0, abs=0.01)


def test_ground_lower_than_the_garden_is_zero_not_negative() -> None:
    """A negative horizon would say the sun arrives from below the observer.
    True of a clifftop, and not a question this model is asked."""
    values = np.full((SIZE, SIZE), 0.0)
    values[SIZE // 2, SIZE // 2] = 100.0  # the garden stands on a knoll
    assert min(_ring(values)) >= 0.0


def _peak_at(gx: float, gy: float, height: float = 800.0) -> np.ndarray:
    """A raster with one compact hill at a given point in the **garden's** frame."""
    from ninanatur.geo.terrain import frame_map

    origin, per_x, per_y = frame_map(WEST, 32)
    east = origin[0] + per_x[0] * gx + per_y[0] * gy
    north = origin[1] + per_x[1] * gx + per_y[1] * gy
    col = int((east - CORNER_E) / RING_CELL_M)
    row = int((CORNER_N - north) / RING_CELL_M)
    values = np.zeros((SIZE, SIZE))
    values[row - 1 : row + 2, col - 1 : col + 2] = height
    return values


def test_the_ring_is_measured_on_true_north_not_grid_north() -> None:
    """A hill placed due south **in the garden's frame** must come back at
    azimuth 180.

    Grid north here is 2.33° off true north, so a ring built on the raster's own
    axes would put this hill at about 178 — and would then be compared against
    sun azimuths that are measured from true north. Four kilometres out, a
    three-cell hill spans less than a degree, so the peak is sharp enough for the
    difference to be visible.
    """
    ring = _ring(_peak_at(0.0, -4000.0))
    top = max(ring)
    assert [a for a in range(AZIMUTHS) if ring[a] > top - 0.01] == [180]
    assert top == pytest.approx(math.degrees(math.atan2(800.0, 4000.0)), abs=0.2)


def test_a_hill_due_north_lands_due_north() -> None:
    """The other axis, because an error in the sine and the cosine can cancel
    on one of them."""
    ring = _ring(_peak_at(0.0, 4000.0))
    assert [a for a in range(AZIMUTHS) if ring[a] > max(ring) - 0.01] == [0]


def test_an_observer_on_unsurveyed_ground_gets_a_flat_ring() -> None:
    """Rather than a ring of nonsense measured against a NaN."""
    values = np.full((SIZE, SIZE), 40.0)
    values[SIZE // 2][SIZE // 2] = np.nan
    assert max(_ring(values)) == pytest.approx(0.0, abs=0.01)


def test_blocks_reads_the_ring_the_way_the_sun_model_asks() -> None:
    ring = [0.0] * AZIMUTHS
    ring[180] = 12.0
    assert blocks(ring, 180.0, 10.0) is True
    assert blocks(ring, 180.0, 14.0) is False
    assert blocks(ring, 179.6, 10.0) is True, "rounds to the nearest whole degree"
    assert blocks(ring, 90.0, 1.0) is False
    assert blocks([], 180.0, 1.0) is False, "no ring is not a blocked sun"


# --- storage ---------------------------------------------------------------

def test_a_ring_survives_the_round_trip() -> None:
    from ninanatur.geo.terrain_store import load_horizon, save_horizon
    from ninanatur.ingest.db import connect, init_schema

    conn = connect(":memory:")
    init_schema(conn)
    ring = _ring(_peak_at(0.0, -4000.0))

    save_horizon(conn, "k", ring, "Nordrhein-Westfalen")
    back = load_horizon(conn, "k")

    assert back is not None
    assert len(back) == AZIMUTHS
    assert back[180] == pytest.approx(ring[180], abs=0.01)


def test_a_place_never_measured_is_none_not_a_flat_ring() -> None:
    """A horizon that is genuinely flat and one nobody has looked at are
    different states, and only one of them is worth fetching again."""
    from ninanatur.geo.terrain_store import load_horizon
    from ninanatur.ingest.db import connect, init_schema

    conn = connect(":memory:")
    init_schema(conn)
    assert load_horizon(conn, "nowhere") is None
