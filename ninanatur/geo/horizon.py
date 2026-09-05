"""How high the land stands around a garden, in every direction.

A garden in a valley loses the winter sun to the hillside long before the sun
sets, and no amount of detail about its own 200 m of ground will say so. That is
a different question at a different scale: not *what shape is this plot* but
*what is between here and the sun*.

It is also a question with a very small answer. Five kilometres of terrain at
20 m — a megabyte of raster — reduces to **360 numbers**: for each degree of
azimuth, the highest angle above the horizontal that the land reaches. The
raster is fetched, measured, and thrown away.

**This will do nothing in flat country, and that is correct.** Measured at
Potsdam while Wave 17 was being planned: a maximum of 2.42°, a mean of 0.89° —
and the light model already discards the sun below `MIN_ALTITUDE = 5°`. In the
North German Plain the ring changes no number at all. In the Sauerland, the
Schwarzwald or the Alpenvorland it decides whether a garden sees December.
"""
from __future__ import annotations

import math

import numpy as np

from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import Fetch, frame_map
from ninanatur.geo.terrain_sources import TerrainSource
from ninanatur.geo.tiff import read_raster
from ninanatur.geo.utm import to_utm
from ninanatur.ingest.http import get_bytes

#: How far out the land is asked about. Beyond five kilometres a hill has to be
#: several hundred metres high to reach 5° — the altitude below which the light
#: model already stops counting the sun.
RING_RADIUS_M = 5000.0

#: The resolution the far field is asked for. A hill is not a garden: 20 m is
#: plenty to place a ridge, and it is what turns a 400 MB request into a 1 MB
#: one. The services do the downscaling themselves — every one of the six
#: accepts `SCALEFACTOR`, and it is faster than `SCALESIZE` on most of them.
RING_CELL_M = 20.0

#: One entry per degree of azimuth, measured clockwise from true north.
AZIMUTHS = 360


def horizon_ring(
    anchor: LatLon, source: TerrainSource, *, fetch: Fetch = get_bytes
) -> list[float]:
    """The highest terrain angle in each degree of azimuth, in degrees.

    Zero where the land is flat or lower than the garden — never negative. A
    negative horizon would say the sun arrives from below the observer, which is
    true of a clifftop and is not something this model is asked to answer.
    """
    zone = 32 if source.epsg == 25832 else 33
    east, north = to_utm(anchor.lat, anchor.lon, zone)
    reach = RING_RADIUS_M + RING_CELL_M * 2
    factor = source.cell_m / RING_CELL_M
    url = (
        f"{source.url}?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"
        f"&COVERAGEID={source.coverage}"
        f"&SUBSET={source.axes[0]}({east - reach:.0f},{east + reach:.0f})"
        f"&SUBSET={source.axes[1]}({north - reach:.0f},{north + reach:.0f})"
        f"&FORMAT=image/tiff&SCALEFACTOR={factor}"
    )
    raster = read_raster(fetch(url))
    return ring_from(raster.values, anchor, zone, east - reach, north + reach)


def ring_from(
    values: np.ndarray,
    anchor: LatLon,
    zone: int,
    corner_e: float,
    corner_n: float,
) -> list[float]:
    """Measure the ring from an already-fetched coarse raster.

    Rays are walked in the **garden's** frame rather than the raster's, for the
    same reason the window is resampled: UTM grid north is up to 2.3° off true
    north here, and a ring built on grid azimuths would be rotated by two of its
    own one-degree bins against the sun positions it is compared with.

    Earth curvature is ignored on purpose. Over five kilometres the drop is
    about 1.7 m once refraction is allowed for — 0.019° — which is two orders of
    magnitude below a terrain model that states ± 0.3 m.
    """
    rows, cols = values.shape
    origin, per_x, per_y = frame_map(anchor, zone)

    centre_c = int((origin[0] - corner_e) / RING_CELL_M)
    centre_r = int((corner_n - origin[1]) / RING_CELL_M)
    if not (0 <= centre_r < rows and 0 <= centre_c < cols):
        return [0.0] * AZIMUTHS
    observer = values[centre_r][centre_c]
    if math.isnan(observer):
        return [0.0] * AZIMUTHS

    steps = np.arange(RING_CELL_M, RING_RADIUS_M + RING_CELL_M, RING_CELL_M)
    bearings = np.radians(np.arange(AZIMUTHS, dtype=float))
    # Azimuth 0 is north and turns clockwise, which is how the sun model reports
    # it — not the mathematical convention, and worth saying rather than leaving
    # the reader to infer it from two sines.
    xs = np.outer(np.sin(bearings), steps)
    ys = np.outer(np.cos(bearings), steps)

    east = origin[0] + per_x[0] * xs + per_y[0] * ys
    north = origin[1] + per_x[1] * xs + per_y[1] * ys
    col = ((east - corner_e) / RING_CELL_M).astype(int)
    row = ((corner_n - north) / RING_CELL_M).astype(int)

    inside = (row >= 0) & (row < rows) & (col >= 0) & (col < cols)
    heights = np.full(xs.shape, np.nan)
    heights[inside] = values[row[inside], col[inside]]

    angles = np.degrees(np.arctan2(heights - observer, steps[None, :]))
    angles[~np.isfinite(angles)] = 0.0
    return [max(0.0, float(a)) for a in angles.max(axis=1)]


def blocks(ring: list[float], azimuth: float, altitude: float) -> bool:
    """Is the sun behind the land, at this azimuth and this height?

    Reading the nearest whole degree rather than interpolating: the ring's own
    bins are a degree wide, and the terrain it was measured from is 20 m and
    ± 0.3 m. Interpolating between two such numbers would look more careful and
    be no more true.
    """
    if not ring:
        return False
    return altitude < ring[int(round(azimuth)) % AZIMUTHS]


__all__ = ["AZIMUTHS", "RING_CELL_M", "RING_RADIUS_M", "blocks", "horizon_ring", "ring_from"]
