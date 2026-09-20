"""A window built from tiles — Wave 25, feature 1 (doc 103).

Wave 17 named three tiers and built two: a coverage service where a state runs
one, nothing where it does not. This is the middle one, and with it a garden in
Bayern stops living on a flat world.

The difference a tile makes is where the garden sits in it. A service is asked
for the window and returns exactly it; a tile is a fixed square of the country,
and a 200 m window fits inside a 1 km tile only when the garden is 100 m from
every edge — 64 % of the time. The rest of the time the window crosses one line
or two, so every tile it touches is fetched and they are pasted into one raster
before a single resample puts the ground on the garden's axes.

A tile that does not arrive leaves NaN, which the window already means by
"nobody surveyed this". Nothing arriving at all is None, which is what a state
without a source has always answered.
"""
from __future__ import annotations

import logging

import numpy as np

from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import FETCH_M, TerrainWindow, resample
from ninanatur.geo.tiff import Raster, TiffError, read_raster
from ninanatur.geo.tile_cache import Fetch, TileCache
from ninanatur.geo.tile_sources import TileSource
from ninanatur.geo.utm import to_utm
from ninanatur.ingest.http import get_bytes

log = logging.getLogger(__name__)

#: What a DGM1 tile's cell is, in metres. The product's name is its resolution.
CELL_M = 1.0


def tiles_across(east: float, north: float, source: TileSource,
                 reach_m: float) -> list[tuple[int, int]]:
    """Every tile the window around this point touches, by south-west corner."""
    step = source.tile_km
    first_e, first_n = source.corner_of(east - reach_m, north - reach_m)
    last_e, last_n = source.corner_of(east + reach_m, north + reach_m)
    return [(e, n)
            for e in range(first_e, last_e + 1, step)
            for n in range(first_n, last_n + 1, step)]


def _cache_key(source: TileSource, east_km: int, north_km: int) -> str:
    """Where this tile lives on the volume: what it is, never who asked."""
    suffix = {"GeoTIFF": "tif", "CityGML": "gml", "LAZ": "laz"}.get(source.fmt, "bin")
    return (f"{source.state.lower()}/{source.product.value}/"
            f"{source.tile_name(east_km, north_km)}.{suffix}")


def _rasters(source: TileSource, corners: list[tuple[int, int]], cache: TileCache,
             fetch: Fetch) -> dict[tuple[int, int], Raster]:
    """The tiles that arrived. One missing is a hole, not a failure: a state's
    portal short of a tile is not a reason for a garden to have no ground."""
    got: dict[tuple[int, int], Raster] = {}
    for east_km, north_km in corners:
        url = source.url_for(east_km, north_km)
        try:
            got[(east_km, north_km)] = read_raster(
                cache.get(_cache_key(source, east_km, north_km), url, fetch))
        except (OSError, ValueError, TiffError) as trouble:
            log.warning("a tile did not arrive; that ground stays unknown",
                        extra={"source": source.name, "tile": f"{east_km}_{north_km}",
                               "why": type(trouble).__name__})
    return got


def _pasted(source: TileSource, tiles: dict[tuple[int, int], Raster],
            cell_m: float) -> tuple[Raster, float, float]:
    """One raster over every tile that arrived, and its north-west corner in
    UTM metres. Tiles are the same product at the same resolution, so this is
    an arrangement, not a reprojection."""
    easts = [e for e, _ in tiles]
    norths = [n for _, n in tiles]
    west, south = min(easts), min(norths)
    east, north = max(easts) + source.tile_km, max(norths) + source.tile_km
    side = int(source.tile_km * 1000 / cell_m)
    width, height = int((east - west) * 1000 / cell_m), int((north - south) * 1000 / cell_m)
    values = np.full((height, width), np.nan, dtype="float32")
    for (tile_e, tile_n), raster in tiles.items():
        # Rows run north to south, so the topmost tile is the highest northing.
        top = int((north - (tile_n + source.tile_km)) * 1000 / cell_m)
        left = int((tile_e - west) * 1000 / cell_m)
        values[top:top + side, left:left + side] = raster.values[:side, :side]
    return Raster(width=width, height=height, values=values), west * 1000.0, north * 1000.0


def tile_window(anchor: LatLon, source: TileSource, *, cache: TileCache,
                fetch: Fetch = get_bytes, cell_m: float = CELL_M) -> TerrainWindow | None:
    """The ground under this garden, from its state's tiles."""
    zone = 32 if source.epsg == 25832 else 33
    east, north = to_utm(anchor.lat, anchor.lon, zone)
    tiles = _rasters(source, tiles_across(east, north, source, FETCH_M), cache, fetch)
    if not tiles:
        return None
    raster, corner_e, corner_n = _pasted(source, tiles, cell_m)
    min_xy, side, heights = resample(raster, anchor, cell_m, east, north, zone,
                                     corner=(corner_e, corner_n))
    return TerrainWindow(
        min_x=min_xy, min_y=min_xy, cell_m=cell_m, cols=side, rows=side, heights=heights,
        source=source.state, licence=source.licence, attribution=source.attribution,
        vertical_step_m=source.vertical_step_m or 0.01,
    )


__all__ = ["CELL_M", "tile_window", "tiles_across"]
