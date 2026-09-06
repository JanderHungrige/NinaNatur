"""Getting a garden's ground, once, at a moment somebody is willing to wait.

The window and the ring are read on every recompute and fetched almost never —
terrain does not change. But something has to fetch them the first time, and
where that happens is a decision rather than a detail.

**Not on garden creation.** A state survey answers a window in one to eight
seconds and a horizon in three to twenty, and a person drawing their first bed
should not be watching a spinner for that.

**Not inside a recompute either**, because those run while the page waits.

It happens on the explicit *Schatten neu berechnen*, which is a button somebody
pressed knowing it would take a moment. After that the garden has its ground for
good, and every later recompute reads it for nothing.

A survey that fails, times out, or has no service for this state leaves the
garden flat. That is a supported state — nine Bundesländer have no service at
all — and never an error the gardener has to care about.
"""
from __future__ import annotations

import logging
import sqlite3

from ninanatur.garden.models import Garden
from ninanatur.geo.horizon import horizon_ring
from ninanatur.geo.osm import state_at
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import TerrainWindow, fetch_window
from ninanatur.geo.terrain_sources import by_state
from ninanatur.geo.terrain_store import (
    cache_key,
    load_horizon,
    load_window,
    save_horizon,
    save_window,
)

log = logging.getLogger(__name__)

#: Whether a garden's stored location is precise enough to fetch its ground.
#:
#: **False, and this is a hold rather than a preference.** `create_garden` rounds
#: latitude and longitude to 0.1° before storing them — deliberately, and rightly
#: when they only fed sun angles. That puts a 200 m terrain window, a 5 km
#: horizon ring and a 1 km² building tile up to **six kilometres** from the
#: garden: measured at Wuppertal, where the real ground is 147 m and the rounded
#: point's is 268.
#:
#: Absolute height hardly matters, since a window is relative throughout. What is
#: wrong is *which land* — another hillside's slope, another valley's horizon,
#: another street's building bases. On a slope that is worse than the flat
#: assumption it replaced, because it is confidently wrong.
#:
#: So the elevation features fall back to what every garden had before Wave 17:
#: flat ground, and a page that says so. Wave 17's own feature 6 already writes
#: that sentence.
#:
#: Flip this to True when the location question is settled — see Wave 17's doc
#: for the three ways out, and `tests/test_anchor_precision.py` for the defect.
LOCATION_IS_PRECISE = False


def ensure_terrain(conn: sqlite3.Connection, garden: Garden) -> bool:
    """Fetch and store this location's ground if it is not already there.

    Returns whether the garden now has terrain. Both halves are attempted
    independently: a horizon that fails does not throw away a window that
    worked, because they are separate requests and the window is the one that
    every garden uses.
    """
    if not LOCATION_IS_PRECISE:
        log.info("not fetching ground: the garden's stored location is rounded")
        return False

    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    key = cache_key(anchor)
    have_window = load_window(conn, key) is not None
    have_ring = load_horizon(conn, key) is not None
    if have_window and have_ring:
        return True

    state = state_at(anchor.lat, anchor.lon)
    source = by_state(state) if state else None
    if source is None:
        log.info("no terrain service for %s at %s", state, key)
        return have_window

    if not have_window:
        try:
            window = fetch_window(anchor, source)
        except Exception:
            # Logged with its context and swallowed on purpose: this is the one
            # place in the project where failing means "the garden stays flat",
            # which is exactly what it was yesterday.
            log.warning("terrain window failed for %s (%s)", key, source.state, exc_info=True)
        else:
            if window is not None:
                save_window(conn, key, window)
                have_window = True

    if not have_ring:
        try:
            ring = horizon_ring(anchor, source)
        except Exception:
            log.warning("horizon failed for %s (%s)", key, source.state, exc_info=True)
        else:
            save_horizon(conn, key, ring, source.state)

    return have_window


def ground_for(conn: sqlite3.Connection, anchor: LatLon) -> TerrainWindow | None:
    """The stored ground for a location — and nothing at all while the hold is on.

    Holding the *fetch* was not enough. Windows fetched before the hold are still
    in the database, keyed by the rounded location, so every garden near
    Wuppertal was still being served the same wrong hillside. Readers go through
    here rather than through the store, so the hold has one place to be.
    """
    if not LOCATION_IS_PRECISE:
        return None
    return load_window(conn, cache_key(anchor))


def horizon_for(conn: sqlite3.Connection, anchor: LatLon) -> list[float] | None:
    """The stored ring, under the same hold and for the same reason."""
    if not LOCATION_IS_PRECISE:
        return None
    return load_horizon(conn, cache_key(anchor))


__all__ = ["LOCATION_IS_PRECISE", "ensure_terrain", "ground_for", "horizon_for"]
