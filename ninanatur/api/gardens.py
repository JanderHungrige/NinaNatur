"""Garden plans, addressed by share token.

The numeric garden id never appears in a URL. An id is enumerable; the token is
the capability, and exposing the id would give away by incrementing exactly what
the token exists to protect.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ninanatur.api.deps import get_connection
from ninanatur.api.schemas import (
    BedCreate,
    BedOut,
    BedUpdate,
    GardenCreate,
    GardenCreated,
    GardenOut,
    ObstacleCreate,
    ObstacleOut,
    ObstacleUpdate,
    PlantingOut,
)
from ninanatur.garden.models import Bed, BedInput, Garden, ObstacleInput
from ninanatur.garden.store import (
    add_bed,
    add_obstacle,
    create_garden,
    delete_garden,
    garden_by_token,
    load_garden,
    recompute_light,
    update_bed,
    update_obstacle,
)

router = APIRouter(prefix="/api/v1/gardens", tags=["gardens"])


def require_garden(conn: sqlite3.Connection, token: str) -> Garden:
    """Resolve a token or 404.

    Never 403: telling a caller that a token exists but is not theirs is the one
    piece of information the token is meant to hide.
    """
    garden = garden_by_token(conn, token)
    if garden is None:
        raise HTTPException(status_code=404, detail="no such garden")
    return garden


def to_out(garden: Garden) -> GardenOut:
    return GardenOut(
        share_token=garden.share_token,
        name=garden.name,
        latitude=garden.latitude,
        longitude=garden.longitude,
        created_at=garden.created_at,
        updated_at=garden.updated_at,
        beds=[
            BedOut(
                bed_id=b.bed_id, name=b.name, polygon=b.polygon,
                soil_type=b.soil_type, moisture=b.moisture,
                ellenberg_l=b.ellenberg_l, ellenberg_m=b.ellenberg_m,
                ellenberg_n=b.ellenberg_n, ellenberg_r=b.ellenberg_r,
                sun_hours=b.sun_hours, light_computed_at=b.light_computed_at,
                height_above_ground=b.height_above_ground, label=b.label,
                plantings=[
                    PlantingOut(
                        planting_id=p.planting_id, taxon_id=p.taxon_id,
                        canonical_name=p.canonical_name, quantity=p.quantity,
                        added_at=p.added_at,
                    )
                    for p in b.plantings
                ],
            )
            for b in garden.beds
        ],
        obstacles=[
            ObstacleOut(obstacle_id=o.obstacle_id, kind=o.kind, label=o.label,
                        x=o.x, y=o.y, radius=o.radius, height=o.height)
            for o in garden.obstacles
        ],
    )


@router.post("", response_model=GardenCreated, status_code=status.HTTP_201_CREATED)
def create(
    payload: GardenCreate,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenCreated:
    """Create a garden. The token comes back here and is the only way back in."""
    garden_id = create_garden(
        conn, name=payload.name, latitude=payload.latitude, longitude=payload.longitude
    )
    garden = load_garden(conn, garden_id)
    return GardenCreated(share_token=garden.share_token, name=garden.name)


@router.get("/{token}", response_model=GardenOut)
def read(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    return to_out(require_garden(conn, token))


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
    """Add an obstacle and recompute in the same call.

    Requiring a second request would leave the plan showing light values that no
    longer match its own obstacles — and nothing would make that visible.
    """
    garden = require_garden(conn, token)
    add_obstacle(conn, garden.garden_id, ObstacleInput(
        kind=payload.kind, x=payload.x, y=payload.y,
        radius=payload.radius, height=payload.height,
    ))
    recompute_light(conn, garden.garden_id)
    return to_out(load_garden(conn, garden.garden_id))


@router.post("/{token}/recompute", response_model=GardenOut)
def recompute(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    garden = require_garden(conn, token)
    recompute_light(conn, garden.garden_id)
    return to_out(load_garden(conn, garden.garden_id))


@router.delete("/{token}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> Response:
    delete_garden(conn, require_garden(conn, token).garden_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def require_bed(garden: Garden, bed_id: int) -> Bed:
    """A bed must belong to the garden the token opened.

    Without this, a valid token for one garden would let its holder reach any bed
    in the database by guessing an id — the capability would leak past the thing
    it names.
    """
    for bed in garden.beds:
        if bed.bed_id == bed_id:
            return bed
    raise HTTPException(status_code=404, detail=f"no such bed in this garden: {bed_id}")


@router.patch("/{token}/beds/{bed_id}", response_model=GardenOut)
def edit_bed(
    token: str,
    bed_id: int,
    payload: BedUpdate,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Change what a bed is. Raising it changes its light, so the light is redone.

    Leaving the stored number alone would leave the screen describing a bed that
    no longer exists — the same reason adding an obstacle recomputes.
    """
    garden = require_garden(conn, token)
    require_bed(garden, bed_id)
    update_bed(conn, bed_id, **payload.model_dump(exclude_unset=True))
    recompute_light(conn, garden.garden_id)
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
    if not any(o.obstacle_id == obstacle_id for o in garden.obstacles):
        raise HTTPException(status_code=404, detail=f"no such obstacle: {obstacle_id}")
    changes = payload.model_dump(exclude_unset=True)
    if "kind" in changes and changes["kind"] is not None:
        changes["kind"] = str(changes["kind"])
    update_obstacle(conn, obstacle_id, **changes)
    recompute_light(conn, garden.garden_id)
    return to_out(load_garden(conn, garden.garden_id))
