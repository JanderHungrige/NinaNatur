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
(`_hours_at`).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ninanatur.data.traits import resolve_trait
from ninanatur.fit.light_fit import light_mismatch_at
from ninanatur.garden.lightgrid import LightGrid
from ninanatur.garden.models import Element, Garden
from ninanatur.solar.light import ellenberg_from_sun_hours


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
            hours = None if wanted is None else _hours_at(grid, bed, planting, own)
            if wanted is None or hours is None:
                continue
            wants, width = wanted
            gets = ellenberg_from_sun_hours(hours)
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


def _bed_light(grid: LightGrid, bed: Element) -> tuple[float | None, bool]:
    """The bed's own light, and whether it is one value for the whole bed.

    Its cells' mean, as `lighting.recompute_light` stores it — the value the
    list ranks the bed by — read from this grid over the bed as it stands, so
    a bed drawn or moved since the last press is judged where it is and not
    where it was (review, 2026-09-21). A raised bed, or one narrower than a
    cell, was measured at one point: its stored value, for the whole bed.
    """
    mean = None if bed.height_above_ground > 0 else grid.mean_over(bed.polygon)
    return (bed.sun_hours, True) if mean is None else (round(mean, 2), False)


def _hours_at(
    grid: LightGrid, bed: Element, planting: object, own: tuple[float | None, bool]
) -> float | None:
    """The sun a cluster gets: its own cell's, where it has one.

    Otherwise its bed's own light (`_bed_light`):
    - for a cluster nobody has placed — it stands nowhere in particular, and it
      is what the list has just planted; read at the bed's middle, a species the
      list had just offered was warned about the moment it was added;
    - in a raised bed, whose light is sampled at its height, over whatever
      darkens the ground grid beside it;
    - in a bed narrower than a cell: no cell centre lies inside it, so a
      cluster's cell is always centred outside — in the wall or hedge it
      borders, or behind it — and warned a plant the list had just offered as
      too dark. Its shaded end goes unsaid until the grid is finer than it;
    - in a cell under a roof or outside the grid.
    """
    value, whole = own
    at = None if whole else _placed_at(bed, planting)
    here = None if at is None else grid.at(*at)
    return value if here is None else here


def _placed_at(bed: object, planting: object) -> tuple[float, float] | None:
    """Where the gardener put the cluster, in garden metres; None if nowhere."""
    x = getattr(planting, "x", None)
    y = getattr(planting, "y", None)
    if x is None or y is None:
        return None
    return (float(getattr(bed, "x", 0.0)) + x, float(getattr(bed, "y", 0.0)) + y)