"""One cell of the light grid, on whatever surface is actually there.

Split out of `lightgrid.py` when roofs arrived and pushed it past the length
limit. The seam is real rather than convenient: `lightgrid` decides how fine the
grid is and what it covers, and this decides what a single point's answer *is* —
which since 2026-09-07 is two questions, because a cell under a building is not
ground.

It takes a centre rather than a grid and a column, so it needs nothing from
`lightgrid` and the dependency runs one way.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import Polygon

from ninanatur.garden.ground import height_at
from ninanatur.garden.models import Garden
from ninanatur.garden.objects import ObjectKind, is_roofed
from ninanatur.garden.roofs import Roof
from ninanatur.garden.roofshape import RoofSurface, surface_of
from ninanatur.garden.slopes import ASPECT_STEP_DEG, SLOPE_STEP_DEG, ring_for, slope_at
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.raster_grid import Cells

#: A ring gives the land's height in each degree of azimuth.
DEGREES = 360


@dataclass(frozen=True)
class Roofed:
    """One building's outline, its roof surface, and what it stands on."""

    outline: list[tuple[float, float]]
    surface: RoofSurface | None
    element_id: int
    base: float


@dataclass(frozen=True)
class Surface:
    """What one cell's sun is asked about — since Wave 26 the raster asks it
    for every cell at once (`solar.raster_grid`); this says what each cell is.

    `z` is the absolute height it stands at, `ring` how high the land stands
    around it in each degree (empty for an open sky), `owner` the building
    whose roof it is, left out of its own shadows. `answered` is False only for
    a roof nobody has given a height, which the model has skipped since Wave 8.
    """

    z: float
    ring: tuple[float, ...]
    owner: int | None
    on_a_roof: bool
    answered: bool = True


def roofs_of(garden: Garden, ground: TerrainWindow | None) -> list[Roofed]:
    """The buildings, each with the roof surface the sun will be asked about.

    Read off the garden rather than off the shading obstacles, which have
    already been reduced to footprints and heights and no longer know what
    shape they are.
    """
    roofed: list[Roofed] = []
    for element in garden.obstacles:
        if not is_roofed(ObjectKind(element.kind)):
            continue
        outline = [(float(x), float(y)) for x, y in element.footprint]
        heights = [h for h in (
            None if ground is None else ground.at(x, y) for x, y in outline
        ) if h is not None]
        roofed.append(Roofed(
            outline=outline,
            surface=surface_of(outline, Roof(element.roof), element.height,
                               element.eaves_m, element.roof_fall_deg),
            element_id=element.element_id,
            base=sum(heights) / len(heights) if heights else 0.0,
        ))
    return roofed


def surface_at(
    centre: tuple[float, float],
    ground: TerrainWindow | None,
    horizon: list[float] | None,
    floor: float,
    roofs: list[Roofed],
    height_above_ground: float = 0.0,
    rings: dict[tuple[float, float], tuple[float, ...]] | None = None,
) -> Surface:
    """One cell, on whatever surface is actually there.

    Ground, unless a building stands on it — and then the roof, at its own
    height and its own pitch, with that building left out of its own shadow.
    Answering the ground under a house is answering a place the sun has never
    reached, and painting the result on a plan says *deep shade* where anyone
    looking down sees a sunlit roof.

    The pitch is folded into the sky the way a hillside already is: a north
    pitch has its own ridge standing between it and the southern sun. On the
    ground the ring is built per cell, because the near field is the slope and
    the slope is a property of the cell; without terrain there is no slope,
    and the garden's own ring is used unchanged.

    `rings` shares one ring among every cell of one slope and aspect, as the
    ring rounds them: kept per cell, a hillside's grid held a 360-number ring
    for each of forty thousand cells (review, 2026-09-22).
    """
    from ninanatur.garden.footprint import covers

    x, y = centre
    for roofed in roofs:
        if not covers(roofed.outline, (x, y)):
            continue
        if roofed.surface is None:
            # Unanswered, and on the lowest ground: a height of zero on a
            # garden 150 m up swept every shadow from 150 m below it (review).
            return Surface(z=floor, ring=(), owner=None, on_a_roof=True, answered=False)
        slope, aspect = roofed.surface.slope_aspect_at(x, y)
        return Surface(z=roofed.base + roofed.surface.height_at(x, y),
                       ring=_ring(horizon, slope, aspect, rings), owner=roofed.element_id,
                       on_a_roof=True)
    ring = tuple(horizon or ()) if ground is None else _ring(horizon, *slope_at(ground, x, y),
                                                             rings)
    return Surface(z=height_at(ground, x, y, floor) + height_above_ground, ring=ring,
                   owner=None, on_a_roof=False)


def _ring(horizon: list[float] | None, slope: float, aspect: float,
          rings: dict[tuple[float, float], tuple[float, ...]] | None) -> tuple[float, ...]:
    """`ring_for`, shared among the cells it rounds to the same ring."""
    if rings is None:
        return ring_for(horizon, slope, aspect)
    key = (-1.0, 0.0) if slope <= 0.0 else (
        round(slope / SLOPE_STEP_DEG) * SLOPE_STEP_DEG,
        round(aspect / ASPECT_STEP_DEG) * ASPECT_STEP_DEG)
    found = rings.get(key)
    if found is None:
        found = rings[key] = ring_for(horizon, slope, aspect)
    return found


def surfaces_of(xs: list[float], ys: list[float], ground: TerrainWindow | None,
                horizon: list[float] | None, floor: float, roofs: list[Roofed],
                height_above_ground: float = 0.0) -> list[list[Surface]]:
    """Every cell's surface, rows from the south: `surface_at` for a grid.

    Which roof a cell is on is asked of each roof once, for every cell at
    once — asked per cell, a garden of forty houses spent more time finding
    roofs than computing sun (doc 117). A cell on the ground with no terrain
    under it has nothing of its own, and shares one surface with the rest.
    """
    x, y = np.meshgrid(np.asarray(xs, dtype=float), np.asarray(ys, dtype=float))
    whose = np.full(x.shape, -1, dtype=int)
    for index, roofed in enumerate(roofs):
        if len(roofed.outline) < 3:
            continue
        on = shapely.intersects_xy(shapely.make_valid(Polygon(roofed.outline)), x, y)
        whose[(whose < 0) & on] = index
    flat = None if ground is not None else Surface(
        z=height_above_ground, ring=tuple(horizon or ()), owner=None, on_a_roof=False)
    rings: dict[tuple[float, float], tuple[float, ...]] = {}
    return [[flat if flat is not None and whose[r, c] < 0 else
             surface_at((xs[c], ys[r]), ground, horizon, floor,
                        [] if whose[r, c] < 0 else [roofs[int(whose[r, c])]],
                        height_above_ground, rings)
             for c in range(len(xs))] for r in range(len(ys))]


def cells_of(surfaces: list[list[Surface]], xs: list[float], ys: list[float],
             cell_m: float) -> Cells:
    """The raster's arrays for a grid of surfaces, rows from the south.

    Rings are shared: on a uniform hillside every cell has the same one, and
    it is stored once. One of another length than a degree each is spread over
    the 360 degrees the way the sun reads it, by the degree modulo its length.
    """
    # By identity: `surfaces_of` shares each ring, and hashing 360 numbers per
    # cell cost more than the rest of the step.
    index_of: dict[int, int] = {}
    kept: list[tuple[float, ...]] = []
    sky = np.full((len(ys), len(xs)), -1, dtype=int)
    for r, row in enumerate(surfaces):
        for c, surface in enumerate(row):
            if surface.ring:
                found = index_of.get(id(surface.ring))
                if found is None:
                    found = index_of[id(surface.ring)] = len(kept)
                    kept.append(surface.ring)
                sky[r, c] = found
    table = np.array([[ring[d % len(ring)] for d in range(DEGREES)] for ring in kept],
                     dtype=float).reshape(-1, DEGREES)
    return Cells(
        xs=np.array(xs, dtype=float), ys=np.array(ys, dtype=float), cell_m=cell_m,
        z=np.array([[s.z for s in row] for row in surfaces], dtype=float),
        owner=np.array([[-1 if s.owner is None else s.owner for s in row]
                        for row in surfaces], dtype=int),
        sky=sky, rings=table,
    )


__all__ = ["Roofed", "Surface", "cells_of", "roofs_of", "surface_at", "surfaces_of"]
