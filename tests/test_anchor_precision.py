"""How precisely a garden's location is stored, and what it is precise enough for.

This file replaces one that asserted a *defect*. Until 2026-09-07 `create_garden`
rounded to 0.1° — about 6.6 km — which was right while the coordinates only fed
sun angles and ruinous once Wave 17 began fetching a 100 m terrain window, a
5 km horizon ring and a 1 km² building tile from them.

The rounding stayed; only its size changed. Four places is the coarsest a 100 m
window survives, and it is still less than the plan already shows: a garden
imported from the map stores its plot outline and every neighbouring building at
metre precision *relative* to this anchor.
"""
from __future__ import annotations

import math
import sqlite3

import pytest

from ninanatur.garden.store import create_garden, load_garden
from ninanatur.garden.terrain_sync import is_precise
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import WINDOW_M
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.position import Location

#: Half a rounding step: the furthest a stored coordinate can be from the real one.
HALF_STEP = 0.00005


@pytest.fixture()
def conn() -> sqlite3.Connection:
    made = connect(":memory:")
    init_schema(made)
    return made


def _metres(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> float:
    north = (to_lat - from_lat) * 111_320
    east = (to_lon - from_lon) * 111_320 * math.cos(math.radians(from_lat))
    return math.hypot(north, east)


def test_a_gardens_location_is_still_rounded_before_it_is_stored(
    conn: sqlite3.Connection,
) -> None:
    """Deliberate. A coordinate is personal data whatever it is used for, and the
    fifth decimal place buys nothing a 1 m terrain grid can see."""
    garden_id = create_garden(conn, name="G", latitude=51.2563871, longitude=7.1501234)

    stored = load_garden(conn, garden_id)

    assert stored.latitude == pytest.approx(51.2564)
    assert stored.longitude == pytest.approx(7.1501)


def test_the_rounding_never_moves_a_garden_out_of_its_own_window() -> None:
    """The number that decides the precision: the offset has to be small against
    the thing being fetched, not — as at 0.1° — sixty times larger than it."""
    worst = _metres(52.0, 10.0, 52.0 + HALF_STEP, 10.0 + HALF_STEP)
    assert worst < WINDOW_M / 10


def test_no_coordinate_is_moved_further_than_that() -> None:
    """The bound above is arithmetic; this is `Location` actually obeying it."""
    for latitude, longitude in (
        (51.2563871, 7.1501234),
        (51.3099999, 9.4900001),
        (50.9257777, 6.9253333),
        (54.7788888, 9.4366666),
    ):
        stored = Location(latitude=latitude, longitude=longitude)
        assert _metres(latitude, longitude, stored.latitude, stored.longitude) < WINDOW_M / 10


def test_wuppertal_is_no_longer_six_kilometres_from_itself() -> None:
    """The measured case the old rounding broke: its terrain read 268 m where
    the garden's ground is 147, because 0.1° moved it onto the next hillside."""
    latitude, longitude = 51.2563871, 7.1501234
    fine = Location(latitude=latitude, longitude=longitude)

    assert _metres(latitude, longitude, round(latitude, 1), round(longitude, 1)) > 5_000
    assert _metres(latitude, longitude, fine.latitude, fine.longitude) < 10


# --- the gardens that cannot be recovered -----------------------------------

def test_a_garden_from_before_the_change_is_recognised_and_left_flat() -> None:
    """Its precision is gone rather than hidden, so it keeps the flat ground
    every garden had before Wave 17 — never somebody else's hillside."""
    assert is_precise(LatLon(lat=51.3, lon=7.2)) is False
    assert is_precise(LatLon(lat=52.5, lon=13.4)) is False


def test_a_garden_stored_since_the_change_is_used() -> None:
    assert is_precise(LatLon(lat=51.2564, lon=7.1501)) is True
    # One axis on the old grid is not a legacy row: both have to be.
    assert is_precise(LatLon(lat=51.3, lon=7.1501)) is True


def test_the_rare_false_negative_costs_a_garden_its_ground_and_nothing_else(
    conn: sqlite3.Connection,
) -> None:
    """A new garden landing on the 0.1° grid in both axes is read as a legacy
    row. It is created and usable; only its relief is withheld. That is the safe
    direction to be wrong in — the other one serves a hillside 6 km away."""
    garden_id = create_garden(conn, name="Pech", latitude=51.300001, longitude=7.200002)

    stored = load_garden(conn, garden_id)

    assert stored.latitude == pytest.approx(51.3)
    assert is_precise(LatLon(lat=stored.latitude, lon=stored.longitude)) is False
