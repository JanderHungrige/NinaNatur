"""The things drawn inside a garden: beds and obstacles, added, changed, removed.

Split from `gardens.py`, which had grown past the 300-line limit carrying two
concerns: the garden as a whole (made, read, recomputed, claimed, deleted) and
the elements inside it. Every route here still opens its garden by share token
through `require_garden`, and every element is checked to belong to that garden
before anything touches it — a token for one garden must not reach the beds of
another by guessing an id.

None of these redo the light. On a garden of forty houses that cost 2.5 s a
call; the map says `stale` instead, and `POST /recompute` is what clears it.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_bed, require_garden, to_out
from ninanatur.api.schemas import (
    BedCreate,
    BedUpdate,
    GardenOut,
    ObstacleCreate,
    ObstacleUpdate,
)
from ninanatur.garden.elements import delete_element
from ninanatur.garden.models import BedInput, ObstacleInput
from ninanatur.garden.objects import (
    ObjectKind,
    default_height,
    default_shape,
    default_size,
)
from ninanatur.garden.store import (
    add_bed,
    add_obstacle,
    load_garden,
    update_bed,
    update_obstacle,
)

router = APIRouter(prefix="/api/v1/gardens", tags=["gardens"])


@router.post("/{token}/beds", response_model=GardenOut, status_code=status.HTTP_201_CREATED)
def create_bed(
    token: str,
    payload: BedCreate,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Add a bed and compute its light immediately.

    PolygonError, SoilTypeError and MoistureError all subclass ValueError, so they
    surface as 422 with their reason rather than as a 500.

    `add_bed` computes the light itself, so the invariant does not depend on which
    entry point created the bed — it used to live here, and a bed made through the
    store had no light at all.
    """
    garden = require_garden(conn, token)
    add_bed(conn, garden.garden_id, BedInput(
        name=payload.name, polygon=payload.polygon,
        soil_type=payload.soil_type, moisture=payload.moisture,
    ))
    return to_out(load_garden(conn, garden.garden_id))


@router.post("/{token}/obstacles", response_model=GardenOut, status_code=status.HTTP_201_CREATED)
def create_obstacle(
    token: str,
    payload: ObstacleCreate,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Add an obstacle. The light is *not* redone here.

    It used to be, so the plan could never disagree with its own obstacles. On
    a garden of forty houses that cost 2.5 s a call, which is the whole of why
    drawing anything felt slow. The map says `stale` instead, and the button in
    the shade panel is what clears it.
    """
    garden = require_garden(conn, token)
    kind = ObjectKind(payload.kind)
    # Omitted shape and size mean "whatever this kind usually is" — choosing
    # "Hecke" should answer questions rather than ask them.
    shape = payload.shape or default_shape(kind)
    width, depth = default_size(kind)
    add_obstacle(conn, garden.garden_id, ObstacleInput(
        kind=str(kind), x=payload.x, y=payload.y,
        shape=str(shape),
        width=payload.width if payload.width is not None else width,
        depth=payload.depth if payload.depth is not None else depth,
        rotation=payload.rotation,
        points=payload.points,
        # `or 0.0` turned the vocabulary's "this kind has no height" into a
        # measurement nobody took. A street is not something zero metres tall;
        # it is something with no height, which is what keeps it out of the
        # light model rather than in it at zero.
        height=payload.height if payload.height is not None else default_height(kind),
        label=payload.label,
    ))
    return to_out(load_garden(conn, garden.garden_id))


@router.patch("/{token}/beds/{bed_id}", response_model=GardenOut)
def edit_bed(
    token: str,
    bed_id: int,
    payload: BedUpdate,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Change what a bed is.

    Raising it changes its light, and the stored light does not follow: the map
    goes `stale` and says so, rather than costing 2.5 s on a garden of forty
    houses every time somebody renames a bed. See `garden.lighting`.
    """
    garden = require_garden(conn, token)
    require_bed(garden, bed_id)
    update_bed(conn, bed_id, **payload.model_dump(exclude_unset=True))
    return to_out(load_garden(conn, garden.garden_id))


@router.patch("/{token}/obstacles/{obstacle_id}", response_model=GardenOut)
def edit_obstacle(
    token: str,
    obstacle_id: int,
    payload: ObstacleUpdate,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Change what an obstacle is, and redo every bed's light."""
    garden = require_garden(conn, token)
    # Every element, not `garden.obstacles`: since Wave 11 that is a *view*
    # excluding planting sites, so an element that had just been made a bed was
    # unreachable through the only endpoint that edits a kind. A bed could be
    # created and never changed back.
    if not any(e.element_id == obstacle_id for e in garden.elements):
        raise HTTPException(status_code=404, detail=f"no such element: {obstacle_id}")
    changes = payload.model_dump(exclude_unset=True)
    if "kind" in changes and changes["kind"] is not None:
        changes["kind"] = str(changes["kind"])
    # Typing a height is the user's word on it. Without this, correcting a
    # building the map guessed at would leave every sightline through it
    # marked as an assumption.
    if changes.get("height") is not None:
        changes.setdefault("height_source", "user")
    update_obstacle(conn, obstacle_id, **changes)
    return to_out(load_garden(conn, garden.garden_id))


@router.delete("/{token}/obstacles/{obstacle_id}", response_model=GardenOut)
def remove_element(
    token: str,
    obstacle_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Remove an element from the plan.

    Nothing could be removed until now: a shape drawn by mistake stayed. The
    garden comes back rather than a 204, because deleting a bed changes what
    every other bed shows and the caller needs the result, not a second request
    to find it. The *light* is not redone — the map goes stale and says so.
    """
    garden = require_garden(conn, token)
    if not any(e.element_id == obstacle_id for e in garden.elements):
        raise HTTPException(status_code=404, detail=f"no such element: {obstacle_id}")
    delete_element(conn, obstacle_id)
    conn.commit()
    return to_out(load_garden(conn, garden.garden_id))
