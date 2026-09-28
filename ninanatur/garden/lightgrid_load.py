"""What a light grid over one box pays for — split out of `lightgrid.py`.

Counted once, for the cell ladder, the refusal and the scripts that hold the
estimate to measurements alike: the measuring scripts once counted for
themselves, and a price added to the grid's count would have gone unmeasured.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ninanatur.garden.ground import standing_on
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

    def estimate_ms(self, cells: float) -> float:
        return estimate_ms(cells, self.parts, self.near, self.terrain, self.deciduous,
                           self.tilted, self.near_planes, self.far_planes,
                           far_crowns=self.far_crowns, near_crowns=self.near_crowns,
                           reaching=self.reaching)


def load_of(parts: list[Part], box: Box, ground: TerrainWindow | None) -> Load:
    """What a grid over `box` pays for. A part whose footprint reaches into
    the box is on it at every moment; a crown on it is priced as the part it
    is, and more on uneven ground (doc 121); one off it costs more than a far
    part. A neighbour off it but within its own height of it costs more too.
    A far roof has no cell in the grid, so only planes on it make cells
    tilted (doc 119)."""
    corners = [[(float(x), float(y)) for x, y in p.corners] for p in parts]
    standing = [stands_in(c, box) for c in corners]
    near_planes = sum(len(p.roof) for p, on in zip(parts, standing, strict=True) if on)
    terrain = ground is not None
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
                     if not on and p.crown is None and _reaches(p.top, c, box, ground)),
    )


def _reaches(top: float, corners: list[tuple[float, float]], box: Box,
             ground: TerrainWindow | None) -> bool:
    """Whether a footprint off the grid stands within its own shadow's length
    at `REACH_ALTITUDE_DEG` of the box — measured square to the box's sides,
    which a corner overstates by at most √2."""
    under = [] if ground is None else [
        h for h in (ground.at(x, y) for x, y in corners) if h is not None]
    height = top - (min(under) if under else 0.0)
    reach = max(height, 0.0) / math.tan(math.radians(REACH_ALTITUDE_DEG))
    return stands_in(corners, (box[0] - reach, box[1] - reach, box[2] + reach, box[3] + reach))


def grid_cost(garden: Garden, obstacles: list[Obstacle], cell: float,
              ground: TerrainWindow | None = None) -> float:
    """What the estimate says this garden's grid costs at this cell, in
    milliseconds — counted as the ladder counts it."""
    box = grid_extent_of(garden)
    if box is None:
        return 0.0
    load = load_of(parts_of(standing_on(obstacles, ground)), box, ground)
    return load.estimate_ms(cells_at(max(box[2] - box[0], 1.0), max(box[3] - box[1], 1.0), cell))


__all__ = ["REACH_ALTITUDE_DEG", "Load", "grid_cost", "load_of"]
