"""A horizon for everyone — Wave 25, feature 2 (doc 104).

`horizon.horizon_ring` asks a state's coverage service for five kilometres of
coarse terrain. Nine states run no such service, and until now a garden in any
of them had no horizon at all: the sun set on its plot at the astronomical
hour, whatever the hill to the south-west was doing.

Copernicus GLO-30 is the answer, and it is the same answer everywhere: one
cloud-optimised GeoTIFF per degree of the earth, thirty metres, free, and
served anonymously. Thirty metres places a ridge and not a hedge, which is all
a ring is for — it is measured at twenty and the light model already ignores
the sun below five degrees.

The tile is geographic and the ring is measured in the garden's own frame, so
the cell's heights are read onto a UTM grid first and `ring_from` does the rest
— one ring algorithm, whatever the ground arrived as.

A ring reaches five kilometres, so a garden within that of a degree line needs
its neighbour's cell too: those are fetched as well, and a cell that does not
arrive is NaN, which the ring already reads as "nothing known this way" rather
than as flat ground.
"""
from __future__ import annotations

import logging
import math

import numpy as np

from ninanatur.geo.horizon import AZIMUTHS, RING_CELL_M, RING_RADIUS_M, ring_from
from ninanatur.geo.projection import LatLon
from ninanatur.geo.tiff import WHOLE_TILE_PIXELS, Raster, TiffError, read_raster
from ninanatur.geo.tile_cache import Fetch, TileCache
from ninanatur.geo.tile_sources import glo30_url
from ninanatur.geo.utm import to_latlon, to_utm, zone_for
from ninanatur.ingest.http import get_bytes

log = logging.getLogger(__name__)

#: Reach, with the margin `horizon_ring` uses for the same reason.
REACH_M = RING_RADIUS_M + RING_CELL_M * 2


def cells_across(anchor: LatLon) -> list[tuple[int, int]]:
    """The degree cells the ring reaches into, as (south latitude, west longitude)."""
    across = REACH_M / 111_320.0
    down = across / max(0.1, math.cos(math.radians(anchor.lat)))
    lats = {math.floor(anchor.lat - across), math.floor(anchor.lat + across)}
    lons = {math.floor(anchor.lon - down), math.floor(anchor.lon + down)}
    return [(lat, lon) for lat in sorted(lats) for lon in sorted(lons)]


def _cell(anchor_lat: int, anchor_lon: int, cache: TileCache, fetch: Fetch) -> Raster | None:
    """One degree cell, from the volume or from Copernicus."""
    url = glo30_url(anchor_lat + 0.5, anchor_lon + 0.5)
    key = f"glo30/{url.rsplit('/', 1)[-1]}"
    try:
        return read_raster(cache.get(key, url, fetch), max_pixels=WHOLE_TILE_PIXELS)
    except (OSError, ValueError, TiffError) as trouble:
        log.warning("a Copernicus cell did not arrive; that direction stays unknown",
                    extra={"cell": f"{anchor_lat}_{anchor_lon}", "why": type(trouble).__name__})
        return None


def _heights_at(cells: dict[tuple[int, int], Raster], lats: np.ndarray,
                lons: np.ndarray) -> np.ndarray:
    """The height at every point, from whichever cell holds it.

    A GLO-30 cell is one degree tall and one degree wide however many columns
    it has — 3,600 rows always, and fewer columns the further north it is, so
    the step is read from the raster rather than assumed.
    """
    heights = np.full(lats.shape, np.nan)
    for (south, west), raster in cells.items():
        inside = ((lats >= south) & (lats < south + 1)
                  & (lons >= west) & (lons < west + 1))
        if not inside.any():
            continue
        rows = ((south + 1 - lats[inside]) * raster.height).astype(int)
        cols = ((lons[inside] - west) * raster.width).astype(int)
        rows = np.clip(rows, 0, raster.height - 1)
        cols = np.clip(cols, 0, raster.width - 1)
        heights[inside] = raster.values[rows, cols]
    return heights


def far_ring(anchor: LatLon, *, cache: TileCache, fetch: Fetch = get_bytes) -> list[float] | None:
    """The horizon around this garden from Copernicus GLO-30, or None if no
    cell arrived at all."""
    cells = {}
    for south, west in cells_across(anchor):
        raster = _cell(south, west, cache, fetch)
        if raster is not None:
            cells[(south, west)] = raster
    if not cells:
        return None

    zone = zone_for(anchor.lon)
    east, north = to_utm(anchor.lat, anchor.lon, zone)
    side = int(2 * REACH_M / RING_CELL_M)
    corner_e, corner_n = east - REACH_M, north + REACH_M
    # The UTM grid `ring_from` walks its rays over, filled from the geographic
    # cells: one ring algorithm, whatever the ground arrived as.
    eastings = corner_e + (np.arange(side) + 0.5) * RING_CELL_M
    northings = corner_n - (np.arange(side) + 0.5) * RING_CELL_M
    grid_e, grid_n = np.meshgrid(eastings, northings)
    lats, lons = _to_latlon(grid_e, grid_n, zone)
    values = _heights_at(cells, lats, lons)
    return ring_from(values, anchor, zone, corner_e, corner_n)


def _to_latlon(eastings: np.ndarray, northings: np.ndarray,
               zone: int) -> tuple[np.ndarray, np.ndarray]:
    """Every grid point in degrees. The projection is a per-point calculation;
    a quarter of a million of them is a tenth of a second, and the alternative
    is a linearisation that is wrong at the ring's edge, which is the part that
    decides whether a hill is in the way."""
    flat_e, flat_n = eastings.ravel(), northings.ravel()
    pairs = [to_latlon(float(e), float(n), zone) for e, n in zip(flat_e, flat_n, strict=True)]
    lats = np.array([lat for lat, _ in pairs]).reshape(eastings.shape)
    lons = np.array([lon for _, lon in pairs]).reshape(eastings.shape)
    return lats, lons


#: What the page says when a ring came from here rather than from a state.
GLO30_SOURCE = "Copernicus GLO-30"

__all__ = ["AZIMUTHS", "GLO30_SOURCE", "REACH_M", "cells_across", "far_ring"]
