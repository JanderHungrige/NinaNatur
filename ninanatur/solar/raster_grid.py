"""The raster over a whole grid of cells — Wave 26, feature 2 (doc 117).

Per moment, each convex part whose swept box reaches the grid is asked about
the cells under that box (`raster.covered`); what passes accumulates
multiplicatively, as `field.ShadowField.halves_at` multiplies it, and the lit
share of each cell is added to its morning or its afternoon. The loop is over
moments and parts; the cells are arrays.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ninanatur.solar.raster import (
    Directions,
    Incidence,
    Moments,
    Part,
    cos_incidence,
    covered,
    sun_directions,
    visible,
)


@dataclass(frozen=True)
class Cells:
    """A regular grid of cell centres and what each one stands on."""

    #: Column and row centres, ascending, one cell apart.
    xs: np.ndarray
    ys: np.ndarray
    cell_m: float
    #: (rows, cols): the absolute height the sun is asked about — the ground,
    #: or a roof's surface for a cell on a roof.
    z: np.ndarray
    #: (rows, cols): the element whose roof the cell is on, or -1. That
    #: element's own parts are left out of the cell's shadows.
    owner: np.ndarray
    #: (rows, cols): which of `rings` is the cell's sky, or -1 for an open one.
    sky: np.ndarray
    #: (rings, degrees): how high the land stands in each degree of azimuth.
    rings: np.ndarray
    #: (3, rows, cols): each cell's surface as `raster.Plane` coefficients — the
    #: ground's slope, a roof's pitch (doc 119); None where every cell is level.
    plane: np.ndarray | None = None


def grid_hours(parts: list[Part], moments: Moments, cells: Cells,
               ) -> tuple[np.ndarray, np.ndarray]:
    """(morning, afternoon): mean daily sun hours per cell, rows × cols."""
    sums = grid_sums(parts, sun_directions(moments), cells)
    return sums[0], sums[1]


def grid_sums(parts: list[Part], directions: Directions, cells: Cells) -> np.ndarray:
    """(groups, rows, cols): each group's weighted sum of what reaches every
    cell — the sun's hours, or the share of the sky a cell sees."""
    return grid_sweep(parts, directions, cells)[0]


def grid_sweep(parts: list[Part], directions: Directions, cells: Cells,
               incidence: Incidence | None = None) -> tuple[np.ndarray, np.ndarray]:
    """`grid_sums`, and in the same sweep (incidence groups, rows, cols): the
    energy of what reaches each cell on its own surface (doc 119). The
    occlusion is the cost, so it is asked once and added twice."""
    rows, cols = cells.z.shape
    sums = np.zeros((directions.groups, rows, cols))
    energy = np.zeros((incidence.groups if incidence else 0, rows, cols))
    brings = None if incidence is None else _brings(directions, incidence, cells)
    seen = visible(cells.rings, directions) if len(cells.rings) else None
    boxes = _boxes(parts)
    tops = np.array([part.top for part in parts])
    lowest = float(cells.z.min()) if cells.z.size else 0.0
    for k in range(len(directions.azimuth)):
        az = math.radians(float(directions.azimuth[k]))
        sun_x, sun_y = math.sin(az), math.cos(az)
        cot = 1.0 / math.tan(math.radians(float(directions.altitude[k])))
        through = np.ones((rows, cols))
        month = int(directions.month[k])
        for j in _reaching(boxes, tops, lowest, sun_x, sun_y, cot, cells):
            _shade(parts[j], cells, through, sun_x, sun_y, cot, month, lowest)
        if seen is not None:
            open_sky = np.append(seen[k], True)  # index -1: no ring, always open
            through *= open_sky[cells.sky]
        sums[int(directions.group[k])] += through * float(directions.weight[k])
        if incidence is not None and brings is not None:
            energy[int(incidence.group[k])] += through * brings(k)
    return sums, energy


def _brings(directions: Directions, incidence: Incidence,
            cells: Cells) -> Callable[[int], np.ndarray | float]:
    """Direction k's beam on each cell's surface, clamped at the surface's
    edge: a number where every cell is level, an array where they tilt."""
    level = incidence.beam * np.maximum(np.sin(np.radians(directions.altitude)), 0.0)
    if cells.plane is None:
        return lambda k: float(level[k])
    plane = (cells.plane[0], cells.plane[1], cells.plane[2])

    def on_surfaces(k: int) -> np.ndarray:
        cos_i = cos_incidence(directions.altitude[k], directions.azimuth[k], plane)
        tilted: np.ndarray = incidence.beam[k] * np.maximum(cos_i, 0.0)
        return tilted
    return on_surfaces


def _boxes(parts: list[Part]) -> np.ndarray:
    """(parts, 4): each part's min x, min y, max x, max y."""
    if not parts:
        return np.empty((0, 4))
    return np.array([[p.corners[:, 0].min(), p.corners[:, 1].min(),
                      p.corners[:, 0].max(), p.corners[:, 1].max()] for p in parts])


def _reaching(boxes: np.ndarray, tops: np.ndarray, lowest: float, sun_x: float,
              sun_y: float, cot: float, cells: Cells) -> np.ndarray:
    """The parts whose shadow, swept onto the lowest cell, can touch the grid."""
    if not len(boxes):
        return np.empty(0, dtype=int)
    reach = np.maximum(tops - lowest, 0.0) * cot
    dx, dy = -sun_x * reach, -sun_y * reach
    lo_x = np.minimum(boxes[:, 0], boxes[:, 0] + dx)
    hi_x = np.maximum(boxes[:, 2], boxes[:, 2] + dx)
    lo_y = np.minimum(boxes[:, 1], boxes[:, 1] + dy)
    hi_y = np.maximum(boxes[:, 3], boxes[:, 3] + dy)
    half = cells.cell_m / 2
    hits: np.ndarray = np.nonzero(
        (hi_x >= cells.xs[0] - half) & (lo_x <= cells.xs[-1] + half)
        & (hi_y >= cells.ys[0] - half) & (lo_y <= cells.ys[-1] + half)
    )[0]
    return hits


def _shade(part: Part, cells: Cells, through: np.ndarray, sun_x: float, sun_y: float,
           cot: float, month: int, lowest: float) -> None:
    """Multiply what passes through this part into the cells its shadow covers."""
    reach = max(part.top - lowest, 0.0) * cot
    xs = (part.corners[:, 0].min(), part.corners[:, 0].max())
    ys = (part.corners[:, 1].min(), part.corners[:, 1].max())
    c0, c1 = _span(cells.xs, cells.cell_m, min(xs[0], xs[0] - sun_x * reach),
                   max(xs[1], xs[1] - sun_x * reach))
    r0, r1 = _span(cells.ys, cells.cell_m, min(ys[0], ys[0] - sun_y * reach),
                   max(ys[1], ys[1] - sun_y * reach))
    if c0 >= c1 or r0 >= r1:
        return
    hit = covered(part, cells.xs[None, c0:c1], cells.ys[r0:r1, None],
                  cells.z[r0:r1, c0:c1], sun_x, sun_y, cot)
    if part.owner is not None:
        hit &= cells.owner[r0:r1, c0:c1] != part.owner
    if hit.any():
        through[r0:r1, c0:c1][hit] *= part.through(month)


def _span(centres: np.ndarray, cell: float, lo: float, hi: float) -> tuple[int, int]:
    """The index range of the centres within [lo, hi]."""
    first = max(0, math.ceil((lo - centres[0]) / cell - 1e-9))
    last = min(len(centres), math.floor((hi - centres[0]) / cell + 1e-9) + 1)
    return first, last


__all__ = ["Cells", "grid_hours", "grid_sums", "grid_sweep"]
