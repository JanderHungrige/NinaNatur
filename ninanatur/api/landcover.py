"""The land around a garden, as the plan colours it (doc 114).

Its own router rather than more of `light.py`: the sun map is about where the
light falls, this is about what the neighbourhood is. It reads a stored row and
nothing else — the areas are fetched when a garden is made from the map, or on
the shade rebuild (`garden/landcover_sync.py`), never on a page load.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_garden
from ninanatur.garden.credits import OSM_ATTRIBUTION, OSM_LICENCE
from ninanatur.geo.landcover_store import load_landcover

router = APIRouter(prefix="/api/v1/gardens", tags=["landcover"])

#: The classes the plan draws (`osm_landcover.LANDCOVER`'s values). Named here
#: so the page's types know every one; a test holds the two lists together.
LandKind = Literal["allotments", "built", "field", "grass", "paved", "residential", "water",
                   "wood"]


class LandAreaOut(BaseModel):
    """One mapped area: what it is, and its rings in garden metres, y north.

    Outer rings run anticlockwise and holes clockwise, for the nonzero rule.
    """

    kind: LandKind
    rings: list[list[list[float]]]


class LandcoverOut(BaseModel):
    """What the ground around the garden is. Empty where nothing is mapped or
    nothing has been fetched yet; the credit is OpenStreetMap's either way."""

    areas: list[LandAreaOut]
    attribution: str
    licence: str


@router.get("/{token}/landcover", response_model=LandcoverOut)
def landcover(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> LandcoverOut:
    """The garden's surroundings, from the stored row; never a request of its own."""
    garden = require_garden(conn, token)
    stored = load_landcover(conn, garden.garden_id) or []
    return LandcoverOut(
        areas=[LandAreaOut.model_validate(
            {"kind": area.kind, "rings": [[list(p) for p in ring] for ring in area.rings]})
            for area in stored],
        attribution=OSM_ATTRIBUTION,
        licence=OSM_LICENCE,
    )


__all__ = ["LandAreaOut", "LandKind", "LandcoverOut", "router"]
