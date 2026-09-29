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
import math
import sqlite3
import statistics
from pathlib import Path

from geokachel.addressing import addressed
from geokachel.tile_cache import TileCache, cache_at
from geokachel.tile_sources import TileProduct, TileSource, sources_for
from geokachel.tile_zip import extract
from geokachel.utm import to_utm

from ninanatur.garden.casting import crown_disc
from ninanatur.garden.footprint import covers
from ninanatur.garden.models import Garden
from ninanatur.garden.terrain_sync import TILE_CACHE_BYTES, is_precise
from ninanatur.geo.cloud_store import load_cloud, save_cloud, stored_cloud
from ninanatur.geo.lod2 import Lod2Building
from ninanatur.geo.osm import state_at
from ninanatur.geo.pointcloud import CloudWindow, window_from
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain_store import cache_key
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

    `buildings` is the survey's building model on the garden's axes — what
    tells a roof from a crown (doc 107) — or None where none was read. A
    window is read again when it does not say which garden it was read around,
    or when a building model has arrived that it was read without (doc 121).

    Slow on purpose — tens of megabytes and a second of arithmetic — so this
    belongs on the background path with the light model, never in a request.
    """
    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    if not is_precise(anchor):
        return False
    key = cache_key(anchor)
    stored = stored_cloud(conn, key)
    if stored is not None and stored.anchored and (stored.classified or buildings is None):
        return True

    state = state_at(anchor.lat, anchor.lon)
    source = laser_for(state)
    if source is None:
        log.info("no open point cloud for %s at %s", state, key)
        return False

    window = _read(anchor, source, buildings or [])
    if window is None:
        return stored is not None
    save_cloud(conn, key, window, anchor, classified=buildings is not None)
    return True


def _unwrapped(source: TileSource, cache: TileCache, stem: str,
               tile_e: int, tile_n: int) -> Path:
    """The tile as a file the reader can stream, wrapper and all.

    Thüringen, Sachsen and Brandenburg zip their point clouds. The archive is
    kept under its own key and the member written out beside it, once — both
    are ordinary entries under the cap, and either can be dropped and made
    again (doc 103).
    """
    found = addressed(source, [(tile_e, tile_n)], cache, get_bytes)
    if not found:
        raise FileNotFoundError(f"{source.name} holds no tile at {tile_e}_{tile_n}")
    grab = found[0][2]
    if not source.zipped:
        # Saarland's member comes out of a 12.5 GB archive already a .laz.
        return cache.file_into(f"{stem}.laz", grab)
    archive = cache.file_into(f"{stem}.zip", grab)
    return extract(archive, want=(".laz", ".las"), out=cache.path_for(f"{stem}.laz"))


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
    stem = f"{source.state.lower()}/{source.product.value}/{source.tile_name(tile_e, tile_n)}"
    key = f"{stem}.laz"
    try:
        path = _unwrapped(source, cache, stem, tile_e, tile_n)
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


def cloud_for(conn: sqlite3.Connection, anchor: LatLon) -> CloudWindow | None:
    """The stored laser window on this garden's axes, where its crown bases can
    be trusted: read under the same check as the ground
    (`terrain_sync.ground_for`), around a garden it can be moved from, and
    with a building model that told its roofs from its crowns (doc 121)."""
    if not is_precise(anchor):
        return None
    key = cache_key(anchor)
    stored = stored_cloud(conn, key)
    if stored is None or not stored.classified:
        return None
    return load_cloud(conn, key, around=anchor)


def crown_base_under(window: CloudWindow, x: float, y: float, radius: float,
                     buildings: list[list[tuple[float, float]]] | None = None) -> float | None:
    """Where the laser saw this crown start (doc 121), or None where it saw
    no canopy under it.

    The median over the cells within half its radius. Nearer the rim, the
    lowest leaves of a round crown are its side rather than its base; and the
    median rather than the lowest, because a cell can hold a shrub under the
    tree, whose leaves the laser reads as the crown's. Cells inside a drawn
    building are left out: a roof the survey's model does not know reads as a
    crown too.
    """
    reach = max(radius / 2, window.cell_m / 2)
    steps = int(reach // window.cell_m) + 1
    bases = []
    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            px, py = x + i * window.cell_m, y + j * window.cell_m
            if math.hypot(px - x, py - y) > reach or any(
                    covers(outline, (px, py)) for outline in buildings or []):
                continue
            base = window.crown_at(px, py)
            if base is not None:
                bases.append(base)
    return None if not bases else round(statistics.median(bases), 2)


def fill_crown_bases(conn: sqlite3.Connection, garden: Garden) -> int:
    """Where the laser saw each tree's crown start, for the trees nobody has
    said it of (doc 121). Returns how many it filled.

    Only where nobody has spoken: a base the gardener typed is theirs, one
    measured stays measured, and one emptied is nobody's again — so the laser
    may answer it, as the survey answers emptied eaves (doc 93). Only trees:
    a shrub branches from the ground, and the laser's lowest leaves over one
    are its own. On the light's path, after the window is read.
    """
    window = cloud_for(conn, LatLon(lat=garden.latitude, lon=garden.longitude))
    if window is None:
        return 0
    built = [list(o.footprint) for o in garden.obstacles if o.kind in ("house", "shed")]
    filled = 0
    for tree in garden.obstacles:
        if tree.kind != "tree" or tree.crown_base_m is not None:
            continue
        disc = crown_disc(tree)
        if tree.crown_base_source is not None or disc is None:
            continue
        base = crown_base_under(window, disc[0], disc[1], disc[2], built)
        if base is None:
            continue
        # Asked again of the row itself: the garden was read before the laser
        # was, and a base typed in between is the gardener's (review of stage
        # 3, 2026-09-28) — the survey guards its own writes the same way.
        written = conn.execute(
            "UPDATE element SET crown_base_m = ?, crown_base_source = 'measured'"
            " WHERE element_id = ? AND crown_base_m IS NULL AND crown_base_source IS NULL",
            (base, tree.element_id))
        filled += written.rowcount
    conn.commit()
    return filled


__all__ = ["cloud_for", "crown_base_under", "ensure_cloud", "fill_crown_bases", "laser_for"]
