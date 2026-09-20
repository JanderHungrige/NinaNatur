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

A survey that fails, times out, has no service for this state, or is asked about
a garden too old to know where it is leaves that garden flat. That is a
supported state — nine Bundesländer have no service at all — and never an error
the gardener has to care about.
"""
from __future__ import annotations

import logging
import sqlite3

from ninanatur.garden.models import Garden
from ninanatur.geo.far_horizon import GLO30_SOURCE, far_ring
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
from ninanatur.geo.tile_cache import TileCache, cache_at
from ninanatur.geo.tile_sources import TileSource, ground_tiles_for
from ninanatur.geo.tiles import tile_window
from ninanatur.ingest.db import database_path

log = logging.getLogger(__name__)

#: How much of the volume the tile cache may hold. A Bavarian DGM1 tile is
#: 2.5 MB and a garden needs at most four, so this is about a hundred gardens'
#: worth of ground before the oldest tiles start to go (doc 103).
TILE_CACHE_BYTES = 1_000_000_000

def is_precise(anchor: LatLon) -> bool:
    """Whether this garden's stored location is precise enough to fetch ground.

    False for gardens created before 2026-09-07. Until then `create_garden`
    rounded to 0.1° — rightly, while the coordinates only fed sun angles, and
    ruinously once Wave 17 started fetching a 100 m terrain window, a 5 km
    horizon ring and a 1 km² building tile from them. At Wuppertal that put all
    three **6.6 km** away, on a hillside reading 268 m where the garden's ground
    is 147.

    Those rows cannot be recovered — the precision is gone, not hidden — so they
    keep what every garden had before Wave 17: flat ground, and a page that says
    so. That is a supported state; nine Bundesländer have no service at all.

    Recognised by shape rather than by a stored flag: a legacy row sits exactly
    on the 0.1° grid in *both* axes, which a coordinate rounded to four places
    does about once in a million times. The rare false negative costs that
    garden its relief and nothing else, which is the safe direction to be wrong
    in.
    """
    return not (
        anchor.lat == round(anchor.lat, 1) and anchor.lon == round(anchor.lon, 1)
    )


def ensure_terrain(conn: sqlite3.Connection, garden: Garden) -> bool:
    """Fetch and store this location's ground if it is not already there.

    Returns whether the garden now has terrain. Both halves are attempted
    independently: a horizon that fails does not throw away a window that
    worked, because they are separate requests and the window is the one that
    every garden uses.
    """
    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    if not is_precise(anchor):
        log.info("not fetching ground: this garden predates the precise anchor")
        return False

    key = cache_key(anchor)
    have_window = load_window(conn, key) is not None
    have_ring = load_horizon(conn, key) is not None
    if have_window and have_ring:
        return True

    state = state_at(anchor.lat, anchor.lon)
    source = by_state(state) if state else None
    # A service is one request for exactly the window; tiles are up to four for
    # the same ground, so they are the tier underneath (doc 103).
    tiles = ground_tiles_for(state) if state and source is None else None
    if source is None and tiles is None:
        log.info("no terrain service and no tiles for %s at %s", state, key)
        return have_window

    if not have_window:
        try:
            window = (fetch_window(anchor, source) if source is not None
                      else _from_tiles(anchor, tiles) if tiles is not None else None)
        except Exception:
            # Logged with its context and swallowed on purpose: this is the one
            # place in the project where failing means "the garden stays flat",
            # which is exactly what it was yesterday.
            whose = source.state if source is not None else f"{state} tiles"
            log.warning("terrain window failed for %s (%s)", key, whose, exc_info=True)
        else:
            if window is not None:
                save_window(conn, key, window)
                have_window = True

    if not have_ring:
        # A state's own service where there is one; Copernicus GLO-30 where
        # there is not, which is nine states that never had a horizon (doc 104).
        whose = source.state if source is not None else GLO30_SOURCE
        try:
            ring = (horizon_ring(anchor, source) if source is not None
                    else far_ring(anchor, cache=_tile_cache()))
        except Exception:
            log.warning("horizon failed for %s (%s)", key, whose, exc_info=True)
        else:
            if ring is not None:
                save_horizon(conn, key, ring, whose)

    return have_window


def _tile_cache() -> TileCache:
    """On the volume beside the database — never in the container layer, where a
    rolled image loses it and a full disk is the deployment (doc 103)."""
    return cache_at(database_path().parent, TILE_CACHE_BYTES)


def _from_tiles(anchor: LatLon, source: TileSource) -> TerrainWindow | None:
    """The ground from a state's own tiles (doc 103)."""
    return tile_window(anchor, source, cache=_tile_cache())


def ground_for(conn: sqlite3.Connection, anchor: LatLon) -> TerrainWindow | None:
    """The stored ground for a location, or None where it must not be used.

    Guarding the *fetch* was never enough. Windows fetched under the old rounding
    are still in the database, keyed by the rounded location, so every garden
    near Wuppertal would still be served the same wrong hillside. Readers go
    through here rather than through the store, so the check has one place to
    live.
    """
    if not is_precise(anchor):
        return None
    return load_window(conn, cache_key(anchor))


def horizon_for(conn: sqlite3.Connection, anchor: LatLon) -> list[float] | None:
    """The stored ring, under the same check and for the same reason."""
    if not is_precise(anchor):
        return None
    return load_horizon(conn, cache_key(anchor))


__all__ = ["ensure_terrain", "ground_for", "horizon_for", "is_precise"]
