"""The sky a cell sees — Wave 26, feature 3 (doc 118).

Half the light of a German growing season comes from the sky rather than the
sun (DWD, diffuse against global radiation, 2015–2025), and a plant under an
open sky with two hours of sun is not in the same light as one under a crown
with a noon gap and the same two hours. The sky-view factor says how much of
the sky's light reaches a cell: every patch of the sky tested with the
occlusion the sun's moments are tested with — houses, crowns, the slope, the
hills (`raster_grid.grid_sums`) — each weighted by what it contributes to the
light on level ground.

The sky is Tregenza's 145 patches, the standard subdivision for daylight: seven
bands 12° high and a cap at the zenith — or Reinhart's 577, each patch split
in four, the finer sky Radiance uses. Tested at its centre, a patch counts
wholly in or out, and beside an edge Tregenza's is off by up to 0.04 of the
sky; Reinhart's by 0.02 (review, 2026-09-22). The sky a map shows, and a light
value may be read from, is Reinhart's. It is weighted for the CIE standard
overcast sky (Moon & Spencer), whose zenith is three times as bright as its
horizon — the sky diffuse light comes from on the days it matters, and the one
Ellenberg's light values were measured under. An isotropic sky is kept beside
it for the geometric checks, where the answer is known in closed form.
"""
from __future__ import annotations

import math

import numpy as np

from ninanatur.solar.raster import Directions

#: Tregenza's bands: centre altitude and patches round it. The last is the cap.
TREGENZA_BANDS: tuple[tuple[float, int], ...] = (
    (6.0, 30), (18.0, 30), (30.0, 24), (42.0, 24), (54.0, 18), (66.0, 12), (78.0, 6), (90.0, 1),
)
#: Each band is 12° high; the cap reaches down to 84°.
BAND_HALF_DEG = 6.0
#: How many ways each of Tregenza's patches is split, in altitude and in
#: azimuth alike: 1 is Tregenza's sky, 2 Reinhart's (the cap stays whole).
TREGENZA, REINHART = 1, 2


def _bands(split: int) -> list[tuple[float, float, int]]:
    """(lowest, highest altitude, patches) of every band, the cap last."""
    bands: list[tuple[float, float, int]] = []
    for centre, count in TREGENZA_BANDS:
        if centre >= 90.0:
            bands.append((90.0 - BAND_HALF_DEG, 90.0, 1))
            continue
        step = 2 * BAND_HALF_DEG / split
        low = centre - BAND_HALF_DEG
        bands.extend((low + k * step, low + (k + 1) * step, count * split) for k in range(split))
    return bands


def sky_directions(month: int, overcast: bool = True, split: int = REINHART) -> Directions:
    """The sky's patches as directions, their weights summing to one: an open
    sky seen from level ground is 1, and what a cell's surroundings hide of it
    is taken off (`grid_sums`). `month` says which leaves the crowns have."""
    azimuths: list[float] = []
    altitudes: list[float] = []
    weights: list[float] = []
    for low, high, count in _bands(split):
        cap = high >= 90.0
        # The solid angle of the band, shared among its patches.
        solid = 2 * math.pi * (math.sin(math.radians(high)) - math.sin(math.radians(low)))
        # What the band gives level ground: its brightness, times the cosine
        # of its zenith angle, over its solid angle.
        centre = 90.0 if cap else (low + high) / 2
        altitude = math.radians(88.0 if cap else centre)
        brightness = (1 + 2 * math.sin(altitude)) / 3 if overcast else 1.0
        share = brightness * math.sin(altitude) * solid / count
        for k in range(count):
            azimuths.append((k + 0.5) * 360.0 / count)
            altitudes.append(centre)
            weights.append(share)
    total = sum(weights)
    return Directions(
        azimuth=np.array(azimuths), altitude=np.array(altitudes),
        month=np.full(len(azimuths), month), weight=np.array(weights) / total,
        group=np.zeros(len(azimuths), dtype=int), groups=1,
    )


__all__ = ["REINHART", "TREGENZA", "TREGENZA_BANDS", "sky_directions"]
