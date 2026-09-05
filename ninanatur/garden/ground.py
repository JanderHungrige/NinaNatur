"""Putting a garden and the things in it onto real ground.

Everything here answers one question the shading model could not ask before
Wave 17: how high is this? A building stands on the ground beneath its own
footprint; a cell of the light grid stands on the ground beneath itself; and the
whole garden has a lowest point, which is the height every shadow polygon is
swept onto so the fast rejections stay fast.

Split from `lightgrid.py`, which was at its length limit. The seam is honest —
that module decides where to sample, this one decides how high each sample is.
"""
from __future__ import annotations

from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.shading import Obstacle


def standing_on(
    obstacles: list[Obstacle], ground: TerrainWindow | None
) -> list[Obstacle]:
    """Put each obstacle on the ground under its own footprint.

    The mean of the cells its outline covers rather than one corner: the terrain
    under a building is interpolated in the first place — a laser does not see
    through a roof — so a corner is no more truthful than an average and is
    noisier.
    """
    if ground is None:
        return obstacles
    placed: list[Obstacle] = []
    for obstacle in obstacles:
        heights = [
            h for h in (ground.at(x, y) for x, y in obstacle.footprint) if h is not None
        ]
        base = sum(heights) / len(heights) if heights else 0.0
        placed.append(
            Obstacle(
                footprint=obstacle.footprint,
                height=obstacle.height,
                base=base,
                transmission=obstacle.transmission,
                bare_transmission=obstacle.bare_transmission,
            )
        )
    return placed


def lowest_ground(
    ground: TerrainWindow | None,
    min_x: float,
    min_y: float,
    cell: float,
    cols: int,
    rows: int,
) -> float:
    """The lowest ground any cell of this garden stands on.

    Every shadow polygon is swept onto this height, which makes it a superset of
    the shadow reaching any real cell — so the fast rejections stay fast and
    only cells standing higher pay for the exact check.
    """
    if ground is None:
        return 0.0
    found = [
        h
        for row in range(rows)
        for col in range(cols)
        if (h := ground.at(min_x + (col + 0.5) * cell, min_y + (row + 0.5) * cell))
        is not None
    ]
    return min(found) if found else 0.0


def height_at(
    ground: TerrainWindow | None, x: float, y: float, floor: float
) -> float:
    """The ground at a point, falling back to the floor where it is unsurveyed.

    The floor rather than zero: a hole in the data should make a cell behave
    like the lowest ground in the garden, which is the cautious direction — it
    is the height that sees the least.
    """
    if ground is None:
        return 0.0
    height = ground.at(x, y)
    return floor if height is None else height


__all__ = ["height_at", "lowest_ground", "standing_on"]
