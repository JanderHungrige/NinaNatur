"""What can be seen from a point in the garden.

Split from `planning.py` on 2026-09-11, when that file had reached 470 lines. The
geometry is `garden/sightlines.py`; this route gathers what stands in the way
and what is planted, and asks it.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_garden
from ninanatur.api.schemas import PlantingVisibility, SightlinesOut, ViewpointIn
from ninanatur.data.traits import resolve_trait
from ninanatur.garden.models import Element, Garden, Planting
from ninanatur.garden.objects import ObjectKind, casts_shadow
from ninanatur.garden.sightlines import Blocker, Target, Viewpoint, visibility

router = APIRouter(prefix="/api/v1/gardens", tags=["planning"])


@router.post("/{token}/sightlines", response_model=SightlinesOut)
def sightlines(
    token: str,
    viewpoint: ViewpointIn,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> SightlinesOut:
    """What is visible from a point in the garden.

    The same cylinders the shading model uses, seen from an eye instead of from
    the sun — so a hedge blocks sight exactly as it blocks light, and a raised
    bed stands above both.
    """
    garden = require_garden(conn, token)
    eye = Viewpoint(x=viewpoint.x, y=viewpoint.y, eye_height_m=viewpoint.eye_height_m)
    blockers = _blockers(garden)
    rows = [
        _seen(conn, eye, bed, planting, blockers)
        for bed in garden.beds
        for planting in bed.plantings
    ]
    return SightlinesOut(plantings=rows, estimated_count=sum(1 for r in rows if r.estimated))


def _blockers(garden: Garden) -> list[Blocker]:
    """What can stand between an eye and a plant."""
    return [
        Blocker(
            id=o.obstacle_id,
            footprint=o.footprint,
            height_m=o.height,
            estimated=o.height_source != "user",
        )
        # An element nobody has given a height to blocks nothing: a sightline
        # resting on an invented number is exactly what Wave 9 refused to draw.
        for o in garden.obstacles
        if o.height is not None
        # A lawn does not stand between you and anything.
        if casts_shadow(ObjectKind(o.kind))
    ]


def _seen(
    conn: sqlite3.Connection,
    eye: Viewpoint,
    bed: Element,
    planting: Planting,
    blockers: list[Blocker],
) -> PlantingVisibility:
    """Whether one planting can be seen from the eye, and from how far."""
    height = _plant_height(conn, planting.taxon_id)
    if height is None:
        # Unknown stays unknown, at this layer as at every other.
        return PlantingVisibility(
            planting_id=planting.planting_id,
            name=planting.display_name,
            bed_id=bed.bed_id,
            height_m=None,
            visible=None,
            visible_from_m=None,
            hidden_by=None,
            estimated=False,
        )
    centre = _bed_centre(bed.polygon)
    seen = visibility(
        eye,
        Target(x=centre[0], y=centre[1], base_m=bed.height_above_ground, height_m=height),
        blockers,
    )
    return PlantingVisibility(
        planting_id=planting.planting_id,
        name=planting.display_name,
        bed_id=bed.bed_id,
        height_m=height,
        visible=seen.visible,
        visible_from_m=seen.visible_from_m,
        hidden_by=seen.hidden_by,
        estimated=seen.estimated,
    )


def _bed_centre(polygon: list[list[float]]) -> tuple[float, float]:
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _plant_height(conn: sqlite3.Connection, taxon_id: int | None) -> float | None:
    if taxon_id is None:
        return None
    trait = resolve_trait(conn, taxon_id, "height_max_m")
    return None if trait is None else trait.value_num
