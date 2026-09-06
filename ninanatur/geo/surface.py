"""How tall the things standing around a garden actually are.

Every building height in this model is a guess: `height` where OSM happens to
carry it, `building:levels × 3 m` where it carries that, and a per-garden
assumption where it carries neither. Wave 17 put those guesses on measured
ground, which is the wrong way round — a guess standing on a measurement.

A surface model answers directly. Where the state publishes an **nDOM** the
values are already heights above ground; where it publishes a **DOM** the
terrain is subtracted here, which is why this needs Wave 17's window and returns
nothing without one.

The measuring itself is `measure.py`. This is only the fetch.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ninanatur.geo.projection import LatLon
from ninanatur.geo.surface_sources import NORMALISED, SurfaceSource
from ninanatur.geo.terrain import FETCH_M, Fetch, TerrainWindow, resample
from ninanatur.geo.tiff import read_raster
from ninanatur.geo.utm import to_utm
from ninanatur.ingest.http import get_bytes


@dataclass(frozen=True)
class SurfaceWindow:
    """Object heights above ground, on the garden's own axes.

    Row-major from the south-west corner, like everything else here. NaN is
    ground nobody surveyed — and a *zero* is bare ground, which is the ordinary
    case over most of a garden and must not be confused with the other.
    """

    min_x: float
    min_y: float
    cell_m: float
    cols: int
    rows: int
    #: Metres above the ground beneath. Never below zero after the subtraction:
    #: a surface cannot be under its own terrain, and where the two rasters
    #: disagree at an edge it is noise rather than a hole.
    heights: list[float]
    source: str
    licence: str
    attribution: str

    def at(self, x: float, y: float) -> float | None:
        col = int((x - self.min_x) // self.cell_m)
        row = int((y - self.min_y) // self.cell_m)
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return None
        value = self.heights[row * self.cols + col]
        return None if math.isnan(value) else value


def fetch_surface(
    anchor: LatLon,
    source: SurfaceSource,
    ground: TerrainWindow | None = None,
    *,
    fetch: Fetch = get_bytes,
) -> SurfaceWindow | None:
    """One request, one window of object heights.

    `ground` is required for a `dom` source and ignored for an `ndom` one.
    Returning None rather than raising when a DOM has no terrain to stand on:
    that is a state of the world — a garden whose terrain fetch failed — and not
    a programming error.
    """
    if source.kind != NORMALISED and ground is None:
        return None

    zone = 32 if source.epsg == 25832 else 33
    east, north = to_utm(anchor.lat, anchor.lon, zone)
    box = (
        f"{source.axes[0]}({east - FETCH_M:.0f},{east + FETCH_M:.0f})"
        f"&SUBSET={source.axes[1]}({north - FETCH_M:.0f},{north + FETCH_M:.0f})"
    )
    url = (
        f"{source.url}?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"
        f"&COVERAGEID={source.coverage}&SUBSET={box}&FORMAT=image/tiff"
    )
    raster = read_raster(fetch(url))
    min_xy, side, values = resample(
        raster, anchor, source.cell_m, east, north, zone
    )

    if source.kind != NORMALISED:
        values = _above_ground(values, ground, min_xy, source.cell_m, side)
    else:
        values = [v if math.isnan(v) else max(0.0, v) for v in values]

    return SurfaceWindow(
        min_x=min_xy,
        min_y=min_xy,
        cell_m=source.cell_m,
        cols=side,
        rows=side,
        heights=values,
        source=source.state,
        licence=source.licence,
        attribution=source.attribution,
    )


def _above_ground(
    surface: list[float],
    ground: TerrainWindow | None,
    min_xy: float,
    cell_m: float,
    side: int,
) -> list[float]:
    """Subtract the terrain, cell by cell, in the garden's own frame.

    Both rasters are already resampled onto the same axes, so this is a lookup
    rather than a second reprojection — and the lookup is by position rather
    than by index, because the two sources need not share a cell size. NRW's
    nDOM is half a metre where its DGM1 is one, and a DOM elsewhere could differ
    the same way.

    Clamped at zero. A surface below its own terrain is the two models
    disagreeing at an edge, not a hole in the ground.
    """
    if ground is None:
        return [float("nan")] * len(surface)
    out: list[float] = []
    for row in range(side):
        y = min_xy + (row + 0.5) * cell_m
        for col in range(side):
            x = min_xy + (col + 0.5) * cell_m
            top = surface[row * side + col]
            below = ground.at(x, y)
            out.append(
                float("nan") if math.isnan(top) or below is None else max(0.0, top - below)
            )
    return out


__all__ = ["SurfaceWindow", "fetch_surface"]
