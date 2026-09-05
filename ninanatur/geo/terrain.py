"""The ground under one garden, fetched once and kept small.

The national DGM1 is a terabyte. No garden needs it: a 200 m window at 1 m is
40,000 numbers, one request, and about a quarter of a megabyte on the wire. So
nothing is precomputed and nothing national is stored — the window is fetched
per location, distilled, and shared by every garden within a hundred metres.

Two hundred metres because the obstacle model reaches fifty metres beyond the
plot boundary (`surroundings.MARGIN_M`), so that covers every building the
shading already knows about with enough ground around it to measure a slope in.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from ninanatur.geo.osm import state_at
from ninanatur.geo.projection import LatLon, Metres
from ninanatur.geo.projection import to_latlon as to_latlon_local
from ninanatur.geo.terrain_sources import TerrainSource, by_state
from ninanatur.geo.tiff import Raster, read_raster
from ninanatur.geo.utm import to_utm
from ninanatur.ingest.http import get_bytes

#: Half-width of the fetched window, in metres.
WINDOW_M = 100.0

#: What is actually requested. A little larger than the window that is kept,
#: because the UTM grid is rotated against the garden's and the corners of an
#: axis-aligned window reach outside a same-sized rotated one — 100 m times
#: sin(2.3°) is 4 m, so 10 m of margin is generous.
FETCH_M = WINDOW_M + 10.0


class Fetch(Protocol):
    """How the bytes are got. Injected so tests never touch the network — and so
    a caller that already has the response does not fetch it twice."""

    def __call__(self, url: str) -> bytes: ...


@dataclass(frozen=True)
class TerrainWindow:
    """Ground heights over a square around a garden, in the garden's own frame.

    `heights` is row-major from the **south-west** corner, the same convention
    the light grid uses, so the two can be indexed the same way. NaN is ground
    nobody surveyed — border tiles and water — and is never averaged into a
    slope.
    """

    min_x: float
    min_y: float
    cell_m: float
    cols: int
    rows: int
    heights: list[float]
    source: str
    licence: str
    attribution: str
    #: How finely the source quantises height. Baden-Württemberg says 1 m where
    #: the DGM1 specification says 0.01, and a page that does not say so is
    #: claiming precision it was not given.
    vertical_step_m: float

    def at(self, x: float, y: float) -> float | None:
        """The height at a point in garden metres, or None outside the window."""
        col = int((x - self.min_x) // self.cell_m)
        row = int((y - self.min_y) // self.cell_m)
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return None
        value = self.heights[row * self.cols + col]
        return None if math.isnan(value) else value


def fetch_window(
    anchor: LatLon, source: TerrainSource, *, fetch: Fetch = get_bytes
) -> TerrainWindow | None:
    """One request, one window, in the garden's own metres.

    Returns None when the service answers with something unreadable rather than
    raising: a garden whose ground could not be fetched is a garden that keeps
    the flat assumption and says so, not a request that fails.
    """
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
    return _into_garden_frame(raster, anchor, source, east, north, zone)


def terrain_for(
    anchor: LatLon, *, state: str | None = None, fetch: Fetch = get_bytes
) -> TerrainWindow | None:
    """The ground under this garden, or None where nobody publishes it.

    None is an answer. Nine Bundesländer have no service in the registry, and
    the model says so rather than borrowing a neighbour's ground.

    `state` may be passed when the caller already knows it — the map picker
    looks it up for the orthophoto anyway, and a second reverse-geocode for the
    same point is a request Nominatim does not need to serve.
    """
    if state is None:
        state = state_at(anchor.lat, anchor.lon)
    if state is None:
        return None
    source = by_state(state)
    if source is None:
        return None
    return fetch_window(anchor, source, fetch=fetch)


def _into_garden_frame(
    raster: Raster,
    anchor: LatLon,
    source: TerrainSource,
    east: float,
    north: float,
    zone: int,
) -> TerrainWindow:
    """Resample a UTM raster onto the garden's own axes.

    **Not a translation.** UTM's grid north is up to about two degrees off true
    north in Germany — at 6°E it is 2.3° — so the raster is rotated with respect
    to the frame the garden is drawn in. Pasting it in unchanged would turn a
    south-facing slope into one facing 2° off south and rotate every hill in the
    horizon ring by two of its one-degree bins.

    Over two hundred metres the map between the two frames is a rotation, a
    scale and a shift to well under a millimetre, so it is measured from three
    points rather than computed per cell.
    """
    cell = source.cell_m
    half = int(WINDOW_M / cell)
    corner_e, corner_n = east - FETCH_M, north + FETCH_M

    origin, per_x, per_y = _frame_map(anchor, zone)
    cols = rows = 2 * half
    heights: list[float] = []
    for row in range(rows):
        y = (row + 0.5 - half) * cell
        for col in range(cols):
            x = (col + 0.5 - half) * cell
            e = origin[0] + per_x[0] * x + per_y[0] * y
            n = origin[1] + per_x[1] * x + per_y[1] * y
            c = int((e - corner_e) / cell)
            r = int((corner_n - n) / cell)
            if 0 <= r < raster.height and 0 <= c < raster.width:
                heights.append(float(raster.values[r][c]))
            else:
                heights.append(float("nan"))

    return TerrainWindow(
        min_x=-half * cell,
        min_y=-half * cell,
        cell_m=cell,
        cols=cols,
        rows=rows,
        heights=heights,
        source=source.state,
        licence=source.licence,
        attribution=source.attribution,
        vertical_step_m=source.vertical_step_m,
    )


def _frame_map(
    anchor: LatLon, zone: int
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Where the garden's origin and its two axes land in UTM.

    Measured by walking 100 m east and 100 m north in the garden's own frame and
    seeing where each ends up. That captures the convergence, the scale factor
    and the shift in one go, without a second copy of the projection formulas.
    """
    def utm(x: float, y: float) -> tuple[float, float]:
        point = to_latlon_local(Metres(x=x, y=y), anchor)
        return to_utm(point.lat, point.lon, zone)

    o = utm(0.0, 0.0)
    ex = utm(100.0, 0.0)
    ey = utm(0.0, 100.0)
    return (
        o,
        ((ex[0] - o[0]) / 100.0, (ex[1] - o[1]) / 100.0),
        ((ey[0] - o[0]) / 100.0, (ey[1] - o[1]) / 100.0),
    )


__all__ = ["FETCH_M", "WINDOW_M", "Fetch", "TerrainWindow", "fetch_window", "terrain_for"]
