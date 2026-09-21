"""A garden's window, built from tiles — Wave 25, feature 1 (doc 103).

Wave 17 named three tiers and built two: a coverage service where a state runs
one, nothing where it does not. This is the middle one, and with it a garden in
Bayern stops living on a flat world.

**Where a tile lives and what comes out of it is `geokachel.addressing`** — the
three kinds of address, the cache, the readers. What stays here is the half
that belongs to this app rather than to a library: pasting the rasters a place
touches into one, and resampling that onto the **garden's** axes, which are
metres from its anchor on *true* north.

That is the seam. UTM grid north is up to 2.3° off true north in Germany, which
a shadow model cannot ignore and a map-maker would not thank anybody for
imposing. So the package stops at a north-up raster in the source's own UTM and
the rotation happens here.

A tile that does not arrive leaves NaN, which the window already means by
"nobody surveyed this". Nothing arriving at all is None, which is what a state
without a source has always answered.
"""
from __future__ import annotations

import numpy as np
from geokachel.addressing import CELL_M, rasters, tiles_across
from geokachel.tiff import Raster
from geokachel.tile_cache import Fetch, TileCache
from geokachel.tile_sources import TileSource
from geokachel.utm import to_utm

from ninanatur.geo.projection import LatLon
from ninanatur.geo.surface import SurfaceWindow, above_ground
from ninanatur.geo.terrain import FETCH_M, TerrainWindow, resample
from ninanatur.ingest.http import get_bytes


def _pasted(tiles: dict[tuple[int, int], Raster], cell_m: float, *, east: float,
            north: float, reach_m: float) -> tuple[Raster, float, float]:
    """One raster over the window, and its north-west corner in UTM metres.

    The window rather than the tiles: four of Bayern's twenty-centimetre tiles
    are four hundred megabytes of mosaic for a four-hundred-metre window, and
    the window itself is five (doc 108). Tiles are the same product at the same
    resolution, so this is an arrangement of parts, not a reprojection.
    """
    corner_e, corner_n = east - reach_m, north + reach_m
    side = int(2 * reach_m / cell_m)
    values = np.full((side, side), np.nan, dtype="float32")
    for (tile_e, tile_n), raster in tiles.items():
        tile_west, tile_north = tile_e * 1000.0, (tile_n * 1000.0) + raster.height * cell_m
        # Where this tile lands in the window, and which of it is inside.
        left = int(round((tile_west - corner_e) / cell_m))
        top = int(round((corner_n - tile_north) / cell_m))
        from_col, from_row = max(0, -left), max(0, -top)
        to_col = min(raster.width, side - left)
        to_row = min(raster.height, side - top)
        if to_col <= from_col or to_row <= from_row:
            continue
        values[top + from_row:top + to_row, left + from_col:left + to_col] = (
            raster.values[from_row:to_row, from_col:to_col])
    return Raster(width=side, height=side, values=values), corner_e, corner_n


def tile_window(anchor: LatLon, source: TileSource, *, cache: TileCache,
                fetch: Fetch = get_bytes, cell_m: float = CELL_M) -> TerrainWindow | None:
    """The ground under this garden, from its state's tiles."""
    zone = 32 if source.epsg == 25832 else 33
    east, north = to_utm(anchor.lat, anchor.lon, zone)
    tiles = rasters(source, tiles_across(east, north, source, FETCH_M), cache,
                     fetch, cell_m)
    if not tiles:
        return None
    raster, corner_e, corner_n = _pasted(tiles, cell_m, east=east, north=north,
                                         reach_m=FETCH_M)
    min_xy, side, heights = resample(raster, anchor, cell_m, east, north, zone,
                                     corner=(corner_e, corner_n))
    return TerrainWindow(
        min_x=min_xy, min_y=min_xy, cell_m=cell_m, cols=side, rows=side, heights=heights,
        source=source.state, licence=source.licence, attribution=source.attribution,
        vertical_step_m=source.vertical_step_m or 0.01,
    )


def surface_window(anchor: LatLon, source: TileSource, ground: TerrainWindow, *,
                   cache: TileCache, fetch: Fetch = get_bytes) -> SurfaceWindow | None:
    """Object heights over this garden, from a state's surface tiles (doc 108).

    The same tiles as the ground, pointed at the other product, and then the
    terrain taken off it: a raw surface model is metres above sea level, and
    what a garden needs is metres above its own ground. A state's surface tiles
    without its ground are no answer at all, which is why `ground` is required
    rather than optional.
    """
    zone = 32 if source.epsg == 25832 else 33
    east, north = to_utm(anchor.lat, anchor.lon, zone)
    cell = source.cell_m or CELL_M
    tiles = rasters(source, tiles_across(east, north, source, FETCH_M), cache,
                     fetch, cell)
    if not tiles:
        return None
    raster, corner_e, corner_n = _pasted(tiles, cell, east=east, north=north,
                                         reach_m=FETCH_M)
    min_xy, side, values = resample(raster, anchor, cell, east, north, zone,
                                    corner=(corner_e, corner_n))
    # A normalised product is already the answer; everything else is metres
    # above the sea and has the garden's own ground taken off it.
    heights = (values if source.normalised
               else above_ground(values, ground, min_xy, cell, side))
    return SurfaceWindow(
        min_x=min_xy, min_y=min_xy, cell_m=cell, cols=side, rows=side,
        heights=heights,
        source=source.state, licence=source.licence, attribution=source.attribution,
    )


__all__ = ["surface_window", "tile_window"]
