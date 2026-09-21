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
stands in — a corner darker than its bed is what this is for. Where there is no
such cell, a cluster is judged by the value the list ranks its bed by: in a
raised bed (its light is sampled at its height), in a bed narrower than a cell
(sampled at its middle), and in a cell under a roof.
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
        # Where `lighting.recompute_light` sampled a point instead of averaging
        # the bed's own cells, there are no cells to judge a cluster by.
        sampled = bed.height_above_ground > 0 or grid.mean_over(bed.polygon) is None
        for planting in bed.plantings:
            if planting.taxon_id is None:
                continue
            wanted = _wanted_light(conn, planting.taxon_id)
            hours = None if wanted is None else _hours_at(grid, bed, planting, sampled)
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


def _hours_at(grid: LightGrid, bed: Element, planting: object, sampled: bool) -> float | None:
    """The sun a cluster gets: its own cell's, or else its bed's stored hours —
    the value the list ranks the bed by."""
    here = None if sampled else grid.at(*_where(bed, planting))
    return bed.sun_hours if here is None else here


def _where(bed: object, planting: object) -> tuple[float, float]:
    """Where the cluster stands, in garden metres.

    The gardener's position when there is one, the bed's middle otherwise — the
    same fallback the shading model uses, and for the same reason.
    """
    x = getattr(planting, "x", None)
    y = getattr(planting, "y", None)
    if x is not None and y is not None:
        return (float(getattr(bed, "x", 0.0)) + x, float(getattr(bed, "y", 0.0)) + y)
    outline = getattr(bed, "polygon", [])
    if not outline:
        return (0.0, 0.0)
    return (
        sum(p[0] for p in outline) / len(outline),
        sum(p[1] for p in outline) / len(outline),
    )
