"""Fetching what the surveys know about a garden's buildings, once.

The sibling of `terrain_sync`, and it runs in the same place and for the same
reason: on the explicit recompute, which is a button somebody pressed knowing it
would take a moment. A LoD2 tile is tens of megabytes and a surface window is
one request; neither belongs in a page load.

Everything here is allowed to fail. A garden whose buildings could not be
measured keeps the heights it had, which is what every garden had before this
existed — and that is a supported state rather than an error.
"""
from __future__ import annotations

import logging
import sqlite3

from ninanatur.garden.canopies_found import remember
from ninanatur.garden.measured import apply, measure
from ninanatur.garden.models import Garden
from ninanatur.garden.terrain_sync import TILE_CACHE_BYTES, ground_for, is_precise
from ninanatur.geo.canopy import canopies_in
from ninanatur.geo.lod2 import (
    MAX_TILE_BYTES,
    Lod2Building,
    buildings_from,
    in_garden_frame,
)
from ninanatur.geo.osm import state_at
from ninanatur.geo.projection import LatLon
from ninanatur.geo.surface import SurfaceWindow, fetch_surface
from ninanatur.geo.surface_sources import by_state, measures_buildings
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.geo.tile_cache import cache_at
from ninanatur.geo.tile_sources import TileProduct, lod2_tiles_for, sources_for
from ninanatur.geo.tile_zip import unpack
from ninanatur.geo.tiles import INSIDE, surface_window
from ninanatur.geo.utm import to_utm
from ninanatur.ingest.db import database_path
from ninanatur.ingest.http import get_bytes

log = logging.getLogger(__name__)

#: Which states publish a 3D building model as addressable tiles is a question
#: for the registry now (doc 102), not a constant here: Nordrhein-Westfalen was
#: the only one anybody had checked, and Bayern turned out to publish the same
#: CityGML 1.0 with the same `bldg:` namespace (doc 105). Everywhere else the
#: roof shape stays whatever it was.


def measure_buildings(conn: sqlite3.Connection, garden: Garden) -> int:
    """Measure this garden's buildings. Returns how many changed.

    Zero is an ordinary answer: no service for this state, nothing surveyed near
    enough to match, or every building already spoken for by the user.
    """
    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    if not is_precise(anchor):
        # Same check as the terrain: a surface window and a building tile
        # fetched six kilometres away measure somebody else's houses.
        return 0

    state = state_at(anchor.lat, anchor.lon)
    if state is None:
        return 0

    surveyed = _surveyed(anchor, state)
    surface = _surface(conn, anchor, state)
    if surveyed is None and surface is None:
        return 0
    changed = apply(conn, measure(garden, surveyed, surface))
    if surface is not None:
        # Trees are proposed, never applied — so this counts separately and does
        # not touch the plan. See `canopy.py` for why a laser cannot tell a
        # crown from a marquee.
        remember(conn, garden.garden_id,
                 canopies_in(surface, [list(o.footprint) for o in garden.obstacles]))
    return changed


def _surface_from_tiles(anchor: LatLon, state: str,
                        ground: TerrainWindow | None) -> SurfaceWindow | None:
    """The state's surface tiles, where it publishes them and runs no service.

    Without the ground there is nothing to subtract, and a surface model in
    metres above sea level says nothing about what stands in a garden.
    """
    if ground is None:
        return None
    source = next((s for s in sources_for(state) if s.product is TileProduct.DOM), None)
    if source is None:
        return None
    try:
        return surface_window(anchor, source, ground,
                              cache=cache_at(database_path().parent, TILE_CACHE_BYTES))
    except Exception:
        log.warning("surface tiles failed for %s", state, exc_info=True)
        return None


def _surveyed(anchor: LatLon, state: str) -> list[Lod2Building] | None:
    """The official 3D model for this square kilometre, on the garden's axes.

    The tile is not cached. A square kilometre of Munich is 161 MB of CityGML
    and what is kept of it is a few hundred bytes per building: fetched,
    streamed, parsed, dropped (doc 103).

    One tile, the garden's own. A neighbour across a kilometre line keeps
    whatever height it had — at 20 to 161 MB a tile, fetching the other three
    to measure a house fifty metres away is not a trade worth making.
    """
    source = lod2_tiles_for(state)
    if source is None:
        return None
    zone = 32 if source.epsg == 25832 else 33
    east, north = to_utm(anchor.lat, anchor.lon, zone)
    tile_e, tile_n = source.corner_of(east, north)
    try:
        arrived = get_bytes(source.url_for(tile_e, tile_n), max_bytes=MAX_TILE_BYTES)
        # Six states wrap the tile, and Baden-Württemberg puts four of its own
        # kilometre tiles in one archive — all four are this garden's
        # neighbourhood, so all four are read (doc 103).
        documents = unpack(arrived, want=INSIDE[source.fmt]) if source.zipped else [arrived]
        surveyed = [found for document in documents for found in buildings_from(document)]
        return in_garden_frame(surveyed, anchor, zone)
    except Exception:
        log.warning("LoD2 tile failed for %s", state, exc_info=True)
        return None


def _surface(
    conn: sqlite3.Connection, anchor: LatLon, state: str
) -> SurfaceWindow | None:
    """Object heights over this garden, from the state's surface model."""
    source = by_state(state)
    if source is None or not measures_buildings(source):
        return None
    ground = ground_for(conn, anchor)
    try:
        return fetch_surface(anchor, source, ground)
    except Exception:
        log.warning("surface model failed for %s", state, exc_info=True)
        return None


__all__ = ["measure_buildings"]
