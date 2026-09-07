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

from ninanatur.garden.ground import height_at
from ninanatur.garden.models import Garden
from ninanatur.garden.objects import ObjectKind, is_roofed
from ninanatur.garden.roofs import Roof
from ninanatur.garden.roofshape import RoofSurface, surface_of
from ninanatur.garden.slopes import ring_for, slope_at
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.field import ShadowAt, ShadowField


def _on_the_ground(
    field_of: ShadowField,
    centre: tuple[float, float],
    ground: TerrainWindow | None,
    horizon: list[float] | None,
    floor: float,
    skies: dict[tuple[float, ...], list[tuple[list[ShadowAt], bool]]],
) -> tuple[float, float]:
    """One cell's morning and afternoon, at its own height and under its own sky.

    The ring is built per cell rather than per garden because the near field is
    the slope and the slope is a property of the cell. Without terrain there is
    no slope to add, so the garden's ring is used unchanged — and without a ring
    either, the whole question disappears.
    """
    x, y = centre
    z = height_at(ground, x, y, floor)
    ring = (
        tuple(horizon or ())
        if ground is None
        else ring_for(horizon, *slope_at(ground, x, y))
    )
    if ring not in skies:
        skies[ring] = field_of.moments_under(ring or None)
    return field_of.halves_at(x, y, z, under=skies[ring])


@dataclass(frozen=True)
class Roofed:
    """One building's outline, its roof surface, and what it stands on."""

    outline: list[tuple[float, float]]
    surface: RoofSurface | None
    element_id: int
    base: float


@dataclass(frozen=True)
class Answer:
    """One cell: its two halves, and whether they are about a roof."""

    halves: tuple[float, float] | None
    on_a_roof: bool


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
                               element.eaves_m),
            element_id=element.element_id,
            base=sum(heights) / len(heights) if heights else 0.0,
        ))
    return roofed


def answer_at(
    field_of: ShadowField,
    centre: tuple[float, float],
    ground: TerrainWindow | None,
    horizon: list[float] | None,
    floor: float,
    skies: dict[tuple[float, ...], list[tuple[list[ShadowAt], bool]]],
    roofs: list[Roofed],
) -> Answer:
    """One cell, on whatever surface is actually there.

    Ground, unless a building stands on it — and then the roof, at its own
    height and its own pitch, with that building left out of its own shadow.
    Answering the ground under a house is answering a place the sun has never
    reached, and painting the result on a plan says *deep shade* where anyone
    looking down sees a sunlit roof.
    """
    from ninanatur.garden.footprint import covers

    x, y = centre
    for roofed in roofs:
        if not covers(roofed.outline, (x, y)):
            continue
        if roofed.surface is None:
            # A building nobody has recorded the height of. Skipped by the
            # shading model since Wave 8, and there is no surface to stand on.
            return Answer(halves=None, on_a_roof=True)
        z = roofed.base + roofed.surface.height_at(x, y)
        slope, aspect = roofed.surface.slope_aspect_at(x, y)
        # The pitch, folded into the sky the way a hillside already is: a north
        # pitch has its own ridge standing between it and the southern sun.
        ring = ring_for(horizon, slope, aspect)
        if ring not in skies:
            skies[ring] = field_of.moments_under(ring or None)
        return Answer(
            halves=field_of.halves_at(x, y, z, under=skies[ring],
                                      ignore=roofed.element_id),
            on_a_roof=True,
        )
    return Answer(
        halves=_on_the_ground(field_of, centre, ground, horizon, floor, skies),
        on_a_roof=False,
    )
