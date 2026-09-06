"""Trees the surface model found, offered rather than added.

Its own router rather than more of `light.py`, which reached its length limit —
and the seam is real: the sun map is about where the light falls, this is about
what somebody agrees is standing there.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_garden, to_out
from ninanatur.api.schemas import GardenOut
from ninanatur.garden.canopies_found import dismiss, mark_accepted, open_suggestions
from ninanatur.garden.elements import insert_element
from ninanatur.garden.store import load_garden

router = APIRouter(prefix="/api/v1/gardens", tags=["canopies"])


class CanopyOut(BaseModel):
    """A tree the surface model found and nobody has drawn.

    A suggestion, never an object. A crown, a hedge, a marquee and a
    badly-mapped building all read as "tall, and not ground" to a laser — so the
    gardener decides, with the same standing as Wave 16's misplacement warning.
    """

    suggestion_id: int
    x: float
    y: float
    radius_m: float
    height_m: float



@router.get("/{token}/canopies", response_model=list[CanopyOut])
def canopies(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> list[CanopyOut]:
    """Trees found near this garden that nobody has answered for yet."""
    garden = require_garden(conn, token)
    return [
        CanopyOut(suggestion_id=s.suggestion_id, x=s.x, y=s.y,
                  radius_m=s.radius_m, height_m=s.height_m)
        for s in open_suggestions(conn, garden.garden_id)
    ]


@router.post("/{token}/canopies/{suggestion_id}", response_model=GardenOut)
def accept_canopy(
    token: str,
    suggestion_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Turn a suggestion into a tree on the plan.

    Its height is marked `measured`, which is what it is — and its species is
    nobody's guess, so the canopy model treats it as a broadleaf in leaf, the
    same default every unidentified woody planting already gets.
    """
    garden = require_garden(conn, token)
    for found in open_suggestions(conn, garden.garden_id):
        if found.suggestion_id != suggestion_id:
            continue
        element_id = insert_element(
            conn, garden.garden_id, kind="tree", shape="circle",
            x=found.x, y=found.y, width=found.radius_m * 2, height=found.height_m,
            name="Baum (gemessen)",
        )
        conn.execute(
            "UPDATE element SET height_source = 'measured' WHERE element_id = ?",
            (element_id,),
        )
        mark_accepted(conn, garden.garden_id, suggestion_id, element_id)
        break
    else:
        raise HTTPException(status_code=404, detail="no such suggestion")
    return to_out(load_garden(conn, garden.garden_id))


@router.delete("/{token}/canopies/{suggestion_id}", status_code=204)
def dismiss_canopy(
    token: str,
    suggestion_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> None:
    """Refuse one, for good.

    Remembered rather than deleted: the next recomputation finds the same tree
    again, and re-proposing something somebody rejected is how a suggestion
    becomes a nuisance.
    """
    garden = require_garden(conn, token)
    if not dismiss(conn, garden.garden_id, suggestion_id):
        raise HTTPException(status_code=404, detail="no such suggestion")


