"""Plants standing somewhere they will not thank you for.

The suggestions rank by fit, light included, so what goes *into* a bed is
already chosen against the site. Nothing looked at what is **already there** —
and until Wave 16 nothing could, because the light was one number per bed and a
cluster had no position to compare it against.

For what is already planted: a warning, never a refusal. A gardener may know
something the model does not: a cultivar bred for shade, a wall that throws
light back, or simply that they want it there. What is *offered* is stricter:
by the owner's decisions of 2026-09-21 the suggestions leave out a species
whose light is unsuitable either way (`api.filters.light_verdict`) — the best
fit for the shade as much as for the sun.

Both ask the same question, so both use one rule (`fit.light_fit`): the
species' own niche width, *unsuitable* past 1.5 half-widths. Until 2026-09-21
this warning used a fixed distance of two rungs instead, and warned about
plants the list had just offered. What still differs is only *where* the light
is read: the list ranks by the bed's average, the warning by the cell a cluster
stands in — a corner darker than its bed is what this is for. Where a cluster
has no cell of its own, it is judged by the value the list ranks its bed by
(`_light_at`). The value is the list's rule too: the hours, floored by the sky
in leaf (`solar.light.light_value`, doc 118).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ninanatur.data.traits import resolve_trait
from ninanatur.fit.light_fit import light_mismatch_at
from ninanatur.garden.footprint import covers
from ninanatur.garden.lightgrid import LightGrid
from ninanatur.garden.models import Element, Garden
from ninanatur.solar.light import light_value


@dataclass(frozen=True)
class Misplaced:
    """One planting, and what is wrong with where it stands."""

    planting_id: int
    bed_id: int
    taxon_id: int
    name: str
    #: What the plant wants, on the Ellenberg light scale.
    wants: float
    #: What it gets there, on the same scale.
    gets: float
    sun_hours: float
    #: 'too_dark' when it wants more light than the spot has, 'too_bright' when
    #: it wants less. Both happen, and the second is the one people forget.
    problem: str
    #: The share of the sky the spot sees in leaf, which may be what darkens it
    #: (doc 118); None on a map from before the sky counted.
    sky_view: float | None = None


def misplaced_plantings(
    conn: sqlite3.Connection, garden: Garden, grid: LightGrid | None
) -> list[Misplaced]:
    """Every planting standing in light it did not ask for.

    Empty without a grid: a bed's single average could only ever say the bed is
    wrong, never the corner, and "this bed is too dark" for a bed whose far end
    is in full sun is the kind of advice that teaches people to ignore advice.
    """
    if grid is None:
        return []

    found: list[Misplaced] = []
    for bed in garden.beds:
        own = _bed_light(grid, bed)
        for planting in bed.plantings:
            if planting.taxon_id is None:
                continue
            wanted = _wanted_light(conn, planting.taxon_id)
            if wanted is None:
                continue
            hours, sky = _light_at(grid, bed, planting, own)
            if hours is None:
                continue
            wants, width = wanted
            # The rule the list ranks by (`solar.light.light_value`).
            gets = light_value(hours, sky)
            problem = light_mismatch_at(gets, wants, width)
            if problem is None:
                continue
            found.append(
                Misplaced(
                    planting_id=planting.planting_id,
                    bed_id=bed.bed_id,
                    taxon_id=planting.taxon_id,
                    name=planting.display_name,
                    wants=wants,
                    gets=gets,
                    sun_hours=round(hours, 1),
                    problem=problem,
                    sky_view=None if sky is None else round(sky, 2),
                )
            )
    return found


def _wanted_light(conn: sqlite3.Connection, taxon_id: int) -> tuple[float, float | None] | None:
    """The species' Ellenberg L and its niche width, or None where nothing
    recorded an L.

    None is common and is not a failure: EIVE covers a good part of the flora
    and not all of it, and a plant nobody has an indicator value for cannot be
    said to be in the wrong light. A missing width takes EIVE's median.
    """
    trait = resolve_trait(conn, taxon_id, "ellenberg_l")
    if trait is None or trait.value_num is None:
        return None
    width = resolve_trait(conn, taxon_id, "ellenberg_l_nw")
    return float(trait.value_num), None if width is None else width.value_num


#: A spot's sun hours and the share of the sky it sees; either may be unknown.
Light = tuple[float | None, float | None]


def _bed_light(grid: LightGrid, bed: Element) -> Light:
    """The bed's own light: its cells' mean hours and sky, as
    `lighting.recompute_light` stores them — what the list ranks the bed by —
    read from this grid over the bed as it stands, so a bed drawn or moved
    since the last press is judged where it is (review, 2026-09-21). A raised
    bed, or one with no cell centre inside it, was measured at one point: its
    stored values, which stay where they were measured until the next press."""
    mean = None if bed.height_above_ground > 0 else grid.mean_over(bed.polygon)
    if mean is None:
        return bed.sun_hours, bed.sky_view
    sky = grid.mean_over(bed.polygon, grid.sky)
    return round(mean, 2), None if sky is None else round(sky, 3)


def _light_at(grid: LightGrid, bed: Element, planting: object, own: Light) -> Light:
    """The light a cluster gets: its own cell's hours and sky, where that cell
    is part of its bed — the rule the bed's own mean is taken by
    (`LightGrid.mean_over`): its centre inside the bed, and not a roof.

    Otherwise its bed's own light (`_bed_light`):
    - for a cluster nobody has placed — it stands nowhere in particular, and it
      is what the list has just planted; read at the bed's middle, a species the
      list had just offered was warned about the moment it was added;
    - in a raised bed, whose light is sampled at its height, over whatever
      darkens the ground grid beside it;
    - where the cluster's cell is centred outside its bed — always, in a bed
      narrower than a cell, and along the edge of any other: that centre can
      lie in the wall or hedge the bed borders, and a plant the list had just
      offered was warned as too dark at 0 h. A shaded end finer than the grid
      goes unsaid;
    - in a cell under a roof or outside the grid.
    """
    at = None if bed.height_above_ground > 0 else _placed_at(bed, planting)
    centre = None if at is None else grid.centre_at(*at)
    if at is None or centre is None or not covers(_ring(bed.polygon), centre):
        return own
    here = grid.at(*at)
    return own if here is None else (here, grid.at(*at, grid.sky))


def _ring(polygon: list[list[float]]) -> list[tuple[float, float]]:
    return [(float(p[0]), float(p[1])) for p in polygon]


def _placed_at(bed: object, planting: object) -> tuple[float, float] | None:
    """Where the gardener put the cluster, in garden metres — as the plan drags
    and draws it; None if nowhere. It was read as an offset from the bed's
    centre, and every placed cluster in a bed away from the garden's origin
    was judged somewhere else (review, 2026-09-22)."""
    x = getattr(planting, "x", None)
    y = getattr(planting, "y", None)
    return None if x is None or y is None else (float(x), float(y))