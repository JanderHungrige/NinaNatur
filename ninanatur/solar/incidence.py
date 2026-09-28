"""What a moment of sun brings to a surface — Wave 26, feature 4 (doc 119).

The beam's weight (`Incidence`) and the surface it lands on (`Plane`): the
cosine of incidence on a cell's own ground or roof, which the sweep
(`raster_grid.grid_sweep`, `raster.point_sweep`) adds beside the hours. Split
out of `raster.py` when it passed the 300 lines a module may have.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Incidence:
    """What each direction's beam brings, beside what it is worth (doc 119):
    for the sun, the clear-sky beam at its altitude (`solar.beam`), added —
    times what passes and the cosine of its incidence on each cell's surface —
    to the energy sum named by `group`."""

    beam: np.ndarray
    group: np.ndarray
    groups: int


#: A surface as the sweep reads it: (cos s, −sin s·cos a, −sin s·sin a), which
#: dotted with the sun's (sin h, cos h·cos A, cos h·sin A) is the cosine of
#: incidence. Level ground is (1, 0, 0).
Plane = tuple[float, float, float]
LEVEL: Plane = (1.0, 0.0, 0.0)


def plane_of(slope_deg: float, aspect_deg: float) -> Plane:
    """A surface of this slope, its aspect uphill clockwise from north as every
    aspect here is (`slopes.slope_at`): it faces the other way, downhill."""
    s, a = np.radians(slope_deg), np.radians(aspect_deg)
    return (float(np.cos(s)), float(-np.sin(s) * np.cos(a)), float(-np.sin(s) * np.sin(a)))


def cos_incidence(altitude_deg: np.ndarray, azimuth_deg: np.ndarray,
                  plane: tuple[np.ndarray | float, ...]) -> np.ndarray:
    """The cosine of each direction's incidence on a surface (`Plane`), which
    may be a cell's arrays: sin h cos s − cos h sin s cos(A − a)."""
    h, az = np.radians(altitude_deg), np.radians(azimuth_deg)
    cos_i: np.ndarray = (np.sin(h) * plane[0] + np.cos(h) * np.cos(az) * plane[1]
                         + np.cos(h) * np.sin(az) * plane[2])
    return cos_i


__all__ = ["LEVEL", "Incidence", "Plane", "cos_incidence", "plane_of"]
