"""Plants standing somewhere they will not thank you for.

The suggestions rank by fit, light included, so what goes *into* a bed is
already chosen against the site. Nothing looked at what is **already there** —
and until Wave 16 nothing could, because the light was one number per bed and a
cluster had no position to compare it against.

A warning, never a refusal. A gardener may know something the model does not: a
cultivar bred for shade, a wall that throws light back, or simply that they want
it there.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ninanatur.data.traits import resolve_trait
from ninanatur.garden.lightgrid import LightGrid
from ninanatur.garden.models import Garden
from ninanatur.solar.light import ellenberg_from_sun_hours

#: How far apart the plant's Ellenberg L and the spot's have to be before it is
#: worth saying anything.
#:
#: Two whole rungs. One is inside the noise of a model whose building heights
#: are mostly assumed, and a warning nobody can act on is a warning people learn
#: to scroll past.
TOLERANCE = 2.0


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
        for planting in bed.plantings:
            if planting.taxon_id is None:
                continue
            wants = _wanted_light(conn, planting.taxon_id)
            if wants is None:
                continue
            at = _where(bed, planting)
            hours = grid.at(*at)
            if hours is None:
                continue
            gets = ellenberg_from_sun_hours(hours)
            if abs(wants - gets) < TOLERANCE:
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
                    problem="too_dark" if wants > gets else "too_bright",
                )
            )
    return found


def _wanted_light(conn: sqlite3.Connection, taxon_id: int) -> float | None:
    """The species' Ellenberg L, or None where nothing recorded one.

    None is common and is not a failure: EIVE covers a good part of the flora
    and not all of it, and a plant nobody has an indicator value for cannot be
    said to be in the wrong light.
    """
    trait = resolve_trait(conn, taxon_id, "ellenberg_l")
    return None if trait is None or trait.value_num is None else float(trait.value_num)


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
