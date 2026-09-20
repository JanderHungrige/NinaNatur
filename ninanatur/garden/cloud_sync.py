"""Reading the laser for one garden — Wave 25, feature 4 (doc 107).

The same shape as `terrain_sync`: ask once per place, keep the window, and let
every garden in the street share it. What differs is the size of the thing
being read — a laser tile is tens to hundreds of megabytes against a GeoTIFF's
two and a half — so it is fetched to the volume, streamed off it, and the tile
may fall out of the cache the moment the window exists.

It also needs something the terrain does not: the building model. NRW's cloud
carries no building class (doc 107), so what stands inside a surveyed footprint
is a roof and everything else that stands is a crown. The footprints come from
the same LoD2 tile feature 3 reads, which means a state with a cloud and no
building model gets heights and no crown bases — and says so rather than
calling every roof a tree.
"""
from __future__ import annotations

import logging
import sqlite3

from ninanatur.garden.models import Garden
from ninanatur.garden.terrain_sync import TILE_CACHE_BYTES, is_precise
from ninanatur.geo.cloud_store import load_cloud, save_cloud
from ninanatur.geo.lod2 import Lod2Building
from ninanatur.geo.osm import state_at
from ninanatur.geo.pointcloud import CloudWindow, window_from
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain_store import cache_key
from ninanatur.geo.tile_cache import cache_at
from ninanatur.geo.tile_sources import TileProduct, TileSource, sources_for
from ninanatur.geo.utm import to_utm
from ninanatur.ingest.db import database_path
from ninanatur.ingest.http import get_bytes

log = logging.getLogger(__name__)


def laser_for(state: str | None) -> TileSource | None:
    """The state's point cloud, where it publishes one openly (doc 102)."""
    if state is None:
        return None
    for source in sources_for(state):
        if source.product is TileProduct.LAZ:
            return source
    return None


def ensure_cloud(conn: sqlite3.Connection, garden: Garden, *,
                 buildings: list[Lod2Building] | None = None) -> bool:
    """Read the laser for this garden's place, if it has not been read.

    Returns whether the place now has a window. False is an ordinary answer:
    most states publish no open cloud, and a garden there keeps the rasters it
    always had.

    Slow on purpose — tens of megabytes and a second of arithmetic — so this
    belongs on the background path with the light model, never in a request.
    """
    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    if not is_precise(anchor):
        return False
    key = cache_key(anchor)
    if load_cloud(conn, key) is not None:
        return True

    state = state_at(anchor.lat, anchor.lon)
    source = laser_for(state)
    if source is None:
        log.info("no open point cloud for %s at %s", state, key)
        return False

    window = _read(anchor, source, buildings or [])
    if window is None:
        return False
    save_cloud(conn, key, window)
    return True


def _read(anchor: LatLon, source: TileSource,
          buildings: list[Lod2Building]) -> CloudWindow | None:
    """The tile this garden sits in, read into a window.

    One tile, the garden's own. A window reaches 150 m and a tile is a
    kilometre, so a garden within 150 m of a tile line loses what is beyond it
    — at up to 445 MB a tile, that is the trade doc 107 names rather than four
    of them for one garden.
    """
    zone = 32 if source.epsg == 25832 else 33
    east, north = to_utm(anchor.lat, anchor.lon, zone)
    tile_e, tile_n = source.corner_of(east, north)
    cache = cache_at(database_path().parent, TILE_CACHE_BYTES)
    key = f"{source.state.lower()}/{source.product.value}/{source.tile_name(tile_e, tile_n)}.laz"
    try:
        path = cache.file_for(key, source.url_for(tile_e, tile_n), get_bytes)
        return window_from(
            path, anchor, zone=zone, source=source.state, licence=source.licence,
            attribution=source.attribution,
            footprints=[[(x, y) for x, y in b.outline] for b in buildings],
        )
    except Exception:
        # Same rule as the terrain: a garden whose laser could not be read keeps
        # the rasters it had, and that is not a request that failed.
        log.warning("point cloud failed for %s (%s)", key, source.name, exc_info=True)
        return None


__all__ = ["ensure_cloud", "laser_for"]
