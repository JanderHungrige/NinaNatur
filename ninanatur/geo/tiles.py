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
from ninanatur.geo.surface import SurfaceWindow, above_ground
from ninanatur.geo.terrain import FETCH_M, TerrainWindow, resample
from ninanatur.geo.tiff import WHOLE_TILE_PIXELS, Raster, TiffError, read_raster
from ninanatur.geo.tile_cache import Fetch, TileCache
from ninanatur.geo.tile_grid import TileLookup, corner_in
from ninanatur.geo.tile_index import SAFE_NAME
from ninanatur.geo.tile_sources import TileSource
from ninanatur.geo.tile_zip import ArchiveError, named
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


#: What the wanted member of an archive is called, per format. CityGML is
#: `.gml` in most states and `.xml` in Berlin and Schleswig-Holstein.
INSIDE: dict[str, tuple[str, ...]] = {
    "GeoTIFF": (".tif", ".tiff"),
    "CityGML": (".gml", ".xml"),
    "LAZ": (".laz", ".las"),
}


def _cache_key(source: TileSource, east_km: int, north_km: int) -> str:
    """Where this tile lives on the volume: what it is, never who asked."""
    suffix = {"GeoTIFF": "tif", "CityGML": "gml", "LAZ": "laz"}.get(source.fmt, "bin")
    return (f"{source.state.lower()}/{source.product.value}/"
            f"{source.tile_name(east_km, north_km)}.{'zip' if source.zipped else suffix}")


def _parts(source: TileSource, data: bytes,
           corner: tuple[int, int]) -> list[tuple[tuple[int, int], Raster]]:
    """The rasters in what arrived, each with the corner it belongs at."""
    if not source.zipped:
        return [(corner, read_raster(data, max_pixels=WHOLE_TILE_PIXELS))]
    return [(corner_in(name, corner), read_raster(body, max_pixels=WHOLE_TILE_PIXELS))
            for name, body in named(data, want=INSIDE[source.fmt])]


#: A state's list of what it holds, parsed once per process. Rheinland-Pfalz's
#: ground is twelve megabytes of XML and twenty-one thousand names: a thing to
#: read once for a deployment, not once for a garden. The file itself is on the
#: volume under the same cap as the tiles.
_LISTINGS: dict[str, dict[tuple[int, int], str]] = {}


def _listing(lookup: TileLookup, cache: TileCache,
             fetch: Fetch) -> dict[tuple[int, int], str]:
    """Which tiles the state says it has, and what each is called."""
    if lookup.index_url not in _LISTINGS:
        leaf = lookup.index_url.rsplit("/", 1)[-1]
        key = f"index/{leaf if SAFE_NAME.match(leaf) else 'listing'}"
        _LISTINGS[lookup.index_url] = lookup.parse(cache.get(key, lookup.index_url, fetch))
    return _LISTINGS[lookup.index_url]


def _addresses(source: TileSource, corners: list[tuple[int, int]], cache: TileCache,
               fetch: Fetch) -> list[tuple[tuple[int, int], str, str]]:
    """Each tile's corner, its address, and the key to keep it under.

    For nearly every state the address is arithmetic. For the two that write a
    flight year into the name it is the registry's own folder plus a name their
    list gave us — never a URL out of that list (doc 103).
    """
    if source.lookup is None:
        return [(corner, source.url_for(*corner), _cache_key(source, *corner))
                for corner in corners]
    names = _listing(source.lookup, cache, fetch)
    found = []
    for corner in corners:
        name = names.get(corner)
        if name is None:
            # The state's own list says it has nothing there. A gap in a flight,
            # or a garden near the border — either way not a failed request.
            continue
        found.append((corner, source.lookup.folder + name,
                      f"{source.state.lower()}/{source.product.value}/{name}"))
    return found


def _rasters(source: TileSource, corners: list[tuple[int, int]], cache: TileCache,
             fetch: Fetch) -> dict[tuple[int, int], Raster]:
    """The tiles that arrived. One missing is a hole, not a failure: a state's
    portal short of a tile is not a reason for a garden to have no ground."""
    got: dict[tuple[int, int], Raster] = {}
    try:
        wanted = _addresses(source, corners, cache, fetch)
    except (OSError, ValueError) as trouble:
        log.warning("a state's tile list could not be read; no ground from it",
                    extra={"source": source.name, "why": type(trouble).__name__})
        return got
    for corner, url, key in wanted:
        try:
            got.update(_parts(source, cache.get(key, url, fetch), corner))
        except (OSError, ValueError, TiffError, ArchiveError) as trouble:
            log.warning("a tile did not arrive; that ground stays unknown",
                        extra={"source": source.name, "tile": f"{corner[0]}_{corner[1]}",
                               "why": type(trouble).__name__})
    return got


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
    tiles = _rasters(source, tiles_across(east, north, source, FETCH_M), cache, fetch)
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
    tiles = _rasters(source, tiles_across(east, north, source, FETCH_M), cache, fetch)
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


__all__ = ["CELL_M", "surface_window", "tile_window", "tiles_across"]
