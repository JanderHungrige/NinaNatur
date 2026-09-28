"""What a light grid over one box pays for — split out of `lightgrid.py`.

Counted once, for the cell ladder, the refusal and the scripts that hold the
estimate to measurements alike: the measuring scripts once counted for
themselves, and a price added to the grid's count would have gone unmeasured.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ninanatur.garden.ground import standing_on
from ninanatur.garden.lightcells import Roofed, roofs_of
from ninanatur.garden.lightgrid_cost import estimate_ms
from ninanatur.garden.lightgrid_extent import cells_at, grid_extent_of, stands_in
from ninanatur.garden.models import Garden
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.raster import Part, parts_of
from ninanatur.solar.shading import Obstacle

Box = tuple[float, float, float, float]

#: A neighbour off the grid whose shadow reaches it whenever the sun is below
#: this — within its own height of it — is paid for at most of a season's
#: moments, not only while shadows are long (`lightgrid_cost.REACH_PART_MS`).
#: Measured, not reasoned: 30° took in neighbours 11 to 15 m out, whose far
#: price held with room, and would have coarsened gardens for nothing.
REACH_ALTITUDE_DEG = 45.0


@dataclass(frozen=True)
class Load:
    """What the raster pays for over one box (`lightgrid_cost.estimate_ms`)."""

    parts: int
    near: int
    terrain: bool
    deciduous: bool
    tilted: bool
    near_planes: int
    far_planes: int
    far_crowns: int
    near_crowns: int
    reaching: int
    #: How far the grid's cells stand apart in height: the ground's relief
    #: over the box and the tallest roof on it (`relief_of`).
    relief_m: float

    def estimate_ms(self, cells: float) -> float:
        return estimate_ms(cells, self.parts, self.near, self.terrain, self.deciduous,
                           self.tilted, self.near_planes, self.far_planes,
                           far_crowns=self.far_crowns, near_crowns=self.near_crowns,
                           reaching=self.reaching, relief_m=self.relief_m)


def load_of(parts: list[Part], box: Box, ground: TerrainWindow | None,
            roofs: list[Roofed] | None = None) -> Load:
    """What a grid over `box` pays for. A part whose footprint reaches into
    the box is on it at every moment; a crown on it is priced as the part it
    is, and more the further the grid's cells stand apart in height (doc
    121); one off it costs more than a far part. A neighbour off it but
    within its own height of it costs more too. A far roof has no cell in the
    grid, so only planes on it make cells tilted (doc 119). `roofs` are the
    buildings whose roofs the grid's cells may stand on."""
    corners = [[(float(x), float(y)) for x, y in p.corners] for p in parts]
    standing = [stands_in(c, box) for c in corners]
    near_planes = sum(len(p.roof) for p, on in zip(parts, standing, strict=True) if on)
    terrain = ground is not None
    lowest, highest = relief_of(ground, box, roofs or [])
    return Load(
        parts=len(parts), near=sum(standing), terrain=terrain,
        deciduous=any(p.bare_transmission is not None for p in parts),
        tilted=terrain or near_planes > 0, near_planes=near_planes,
        far_planes=sum(len(p.roof) for p in parts) - near_planes,
        far_crowns=sum(1 for p, on in zip(parts, standing, strict=True)
                       if not on and p.crown is not None),
        near_crowns=sum(1 for p, on in zip(parts, standing, strict=True)
                        if on and p.crown is not None),
        reaching=sum(1 for p, c, on in zip(parts, corners, standing, strict=True)
                     if not on and p.crown is None and _reaches(p.top - lowest, c, box)),
        relief_m=highest - lowest,
    )


def _reaches(height: float, corners: list[tuple[float, float]], box: Box) -> bool:
    """Whether a footprint off the grid stands within its own shadow's length
    at `REACH_ALTITUDE_DEG` of the box — its height above the grid's lowest
    cell, as the raster measures it; measured square to the box's sides,
    which a corner overstates by at most √2."""
    reach = max(height, 0.0) / math.tan(math.radians(REACH_ALTITUDE_DEG))
    return stands_in(corners, (box[0] - reach, box[1] - reach, box[2] + reach, box[3] + reach))


#: How many samples of the ground across the box `relief_of` takes at most
#: along each side.
RELIEF_SAMPLES = 100


def relief_of(ground: TerrainWindow | None, box: Box,
              roofs: list[Roofed]) -> tuple[float, float]:
    """The lowest and the highest a grid cell over `box` can stand: the
    ground's range under it — sampled, at most `RELIEF_SAMPLES` to a side —
    and the ridge of every roof standing on it, of whatever shape. A roof
    raises the highest cell as surely as a hill does; level ground raises
    nothing, however surveyed (review of 45eb56a)."""
    heights: list[float] = []
    if ground is not None:
        step = max(ground.cell_m, (box[2] - box[0]) / RELIEF_SAMPLES,
                   (box[3] - box[1]) / RELIEF_SAMPLES)
        cols = int((box[2] - box[0]) / step) + 1
        rows = int((box[3] - box[1]) / step) + 1
        heights = [h for row in range(rows) for col in range(cols)
                   if (h := ground.at(box[0] + col * step, box[1] + row * step)) is not None]
    lowest = min(heights, default=0.0)
    highest = max(heights, default=0.0)
    for roofed in roofs:
        if roofed.surface is not None and stands_in(roofed.outline, box):
            highest = max(highest, roofed.base + roofed.surface.ridge_m)
    return lowest, highest


def grid_cost(garden: Garden, obstacles: list[Obstacle], cell: float,
              ground: TerrainWindow | None = None) -> float:
    """What the estimate says this garden's grid costs at this cell, in
    milliseconds — counted as the ladder counts it."""
    box = grid_extent_of(garden)
    if box is None:
        return 0.0
    load = load_of(parts_of(standing_on(obstacles, ground)), box, ground,
                   roofs_of(garden, ground))
    return load.estimate_ms(cells_at(max(box[2] - box[0], 1.0), max(box[3] - box[1], 1.0), cell))


__all__ = ["REACH_ALTITUDE_DEG", "Load", "grid_cost", "load_of", "relief_of"]
