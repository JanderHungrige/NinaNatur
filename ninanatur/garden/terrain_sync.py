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
from ninanatur.geo.terrain import fetch_window
from ninanatur.geo.terrain_sources import by_state
from ninanatur.geo.terrain_store import (
    cache_key,
    load_horizon,
    load_window,
    save_horizon,
    save_window,
)

log = logging.getLogger(__name__)


def ensure_terrain(conn: sqlite3.Connection, garden: Garden) -> bool:
    """Fetch and store this location's ground if it is not already there.

    Returns whether the garden now has terrain. Both halves are attempted
    independently: a horizon that fails does not throw away a window that
    worked, because they are separate requests and the window is the one that
    every garden uses.
    """
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


__all__ = ["ensure_terrain"]
