"""The garden's stored location is too coarse for the data Wave 17 fetches.

This file asserts a *defect*, on purpose. It is not a guard against regression —
it is a guard against the defect being forgotten, because everything built on
top of it looks entirely plausible: a terrain window six kilometres away is
still a terrain window, with sensible heights and a believable slope.

Delete this file when the location question is settled, whichever way it goes.
"""
from __future__ import annotations

import math

import pytest

from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.position import Location


def test_a_gardens_stored_location_is_rounded_to_a_tenth_of_a_degree() -> None:
    """Deliberate, and documented in `create_garden`: coarse coordinates were a
    privacy choice made when they only fed sun angles."""
    conn = connect(":memory:")
    init_schema(conn)
    garden_id = create_garden(conn, name="G", latitude=51.2560, longitude=7.1500)

    stored = load_garden(conn, garden_id)

    assert stored.latitude == pytest.approx(51.3)
    assert stored.longitude == pytest.approx(7.2)


def test_which_puts_the_terrain_window_kilometres_from_the_garden() -> None:
    """The consequence, in metres, for the three places this was measured at.

    Wave 17 fetches a 200 m window, a 5 km horizon ring and a 1 km² building
    tile from this location. At Wuppertal the rounding moves all of them six
    kilometres — onto a different hillside, whose terrain reads 268 m where the
    garden's reads 147.
    """
    for latitude, longitude, expected_km in (
        (51.2560, 7.1500, 6.0),    # Wuppertal
        (51.3100, 9.4900, 1.3),    # Kassel
        (50.9250, 6.9250, 3.3),    # Köln
    ):
        coarse = Location(latitude=latitude, longitude=longitude)
        north = (coarse.latitude - latitude) * 111_320
        east = (coarse.longitude - longitude) * 111_320 * math.cos(math.radians(latitude))
        assert math.hypot(north, east) / 1000 == pytest.approx(expected_km, abs=0.2)


def test_the_offset_can_exceed_the_window_it_centres() -> None:
    """The clearest statement of the problem: the error is larger than the thing
    being fetched, so the window and the garden do not overlap at all."""
    from ninanatur.geo.terrain import WINDOW_M

    worst_case_m = 0.05 * 111_320  # half a rounding step in latitude alone
    assert worst_case_m > WINDOW_M * 10
