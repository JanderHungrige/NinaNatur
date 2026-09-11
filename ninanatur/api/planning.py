"""Routes for what goes *into* a garden: plantings, and the colours noted for them.

Split from `gardens.py`, which owns the garden itself. The two share `_require`
and `_require_bed`, because the rule they enforce — a token names one garden, and
a bed id is not a capability — must be identical in both.

What a garden then *says* moved out on 2026-09-11, when this file had reached 470
lines against a limit of 300: a bed's suggestions to `suggestions.py`; the bloom
year, the score and what would raise it to `bloom_year.py`; what can be seen from
where to `sightlines.py`.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_bed, require_garden, to_out
from ninanatur.api.schemas import (
    ColourObservation,
    GardenOut,
    PlantingCreate,
    PlantingPlacement,
)
from ninanatur.data.names import resolve_one
from ninanatur.garden.observations import record_colour
from ninanatur.garden.plantings import add_planting, place_planting, remove_planting
from ninanatur.garden.store import load_garden

router = APIRouter(prefix="/api/v1/gardens", tags=["planning"])


@router.put("/{token}/colours/{taxon_id}", response_model=GardenOut)
def note_colour(
    token: str,
    taxon_id: int,
    payload: ColourObservation,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Record what this species flowers in.

    It goes into the shared catalogue as a `manual` trait row, which is what was
    asked for: one general database, the entry marked as a hand entry, and any
    published source allowed to override it. It is reached through a garden
    because that is where somebody is standing when they answer — the value
    itself belongs to no garden in particular.
    """
    garden = require_garden(conn, token)
    try:
        record_colour(conn, taxon_id=taxon_id, colour=payload.colour)
    except ValueError as undrawable:
        raise HTTPException(status_code=422, detail=str(undrawable)) from undrawable
    return to_out(load_garden(conn, garden.garden_id))


@router.post(
    "/{token}/beds/{bed_id}/plantings",
    response_model=GardenOut,
    status_code=status.HTTP_201_CREATED,
)
def create_planting(
    token: str,
    bed_id: int,
    payload: PlantingCreate,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Put a plant in a bed, named by id or by the words the user typed.

    A name that resolves to exactly one species is stored with that species and
    counts like any other planting. One that does not is stored anyway, marked
    unidentified: discarding it would tell someone their garden is wrong because
    our catalogue is incomplete.
    """
    garden = require_garden(conn, token)
    require_bed(garden, bed_id)
    taxon_id = payload.taxon_id
    if taxon_id is None and payload.raw_name is not None:
        taxon_id = resolve_one(conn, payload.raw_name)
    add_planting(
        conn,
        bed_id,
        taxon_id=taxon_id,
        quantity=payload.quantity,
        raw_name=payload.raw_name,
    )
    return to_out(load_garden(conn, garden.garden_id))


@router.patch("/{token}/plantings/{planting_id}", response_model=GardenOut)
def place_cluster(
    token: str,
    planting_id: int,
    payload: PlantingPlacement,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Put a cluster somewhere in its bed. Reached through its garden, never by
    a bare id: a planting id is enumerable and the token is the whole of a
    garden's access control.

    A position outside the bed is accepted. The plan clamps a drag to the
    outline, but a bed can be reshaped afterwards and a position that was inside
    can end up outside — refusing it here would mean a bed could not be made
    smaller without first moving everything in it.
    """
    garden = require_garden(conn, token)
    _owned_planting(conn, planting_id, garden.garden_id)
    place_planting(conn, planting_id, payload.x, payload.y)
    return to_out(load_garden(conn, garden.garden_id))


@router.delete("/{token}/plantings/{planting_id}", response_model=GardenOut)
def delete_planting(
    token: str,
    planting_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Remove a planting. Reached through its garden, never by a bare id."""
    garden = require_garden(conn, token)
    _owned_planting(conn, planting_id, garden.garden_id)
    remove_planting(conn, planting_id)
    return to_out(load_garden(conn, garden.garden_id))


def _owned_planting(conn: sqlite3.Connection, planting_id: int, garden_id: int) -> None:
    """404 unless this planting is in this garden.

    404 rather than 403: telling a caller that a planting exists but belongs to
    someone else is the one thing a capability URL must not do.
    """
    owned = conn.execute(
        """
        SELECT 1 FROM planting p JOIN element e ON e.element_id = p.element_id
        WHERE p.planting_id = ? AND e.garden_id = ?
        """,
        (planting_id, garden_id),
    ).fetchone()
    if owned is None:
        raise HTTPException(status_code=404, detail=f"no such planting: {planting_id}")
