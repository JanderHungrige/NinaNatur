"""Garden plans, addressed by share token.

The numeric garden id never appears in a URL. An id is enumerable; the token is
the capability, and exposing the id would give away by incrementing exactly what
the token exists to protect.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ninanatur.api.deps import get_connection
from ninanatur.api.plants import to_summary
from ninanatur.api.schemas import (
    BedCreate,
    BedOut,
    BedSuggestions,
    GardenCreate,
    GardenCreated,
    GardenOut,
    ObstacleCreate,
    ObstacleOut,
    PlantingCreate,
    PlantingOut,
)
from ninanatur.api.search import SearchFilters, load_candidates, rank_plants
from ninanatur.fit.score import SiteVector
from ninanatur.garden.models import Bed, BedInput, Garden, ObstacleInput
from ninanatur.garden.store import (
    add_bed,
    add_obstacle,
    add_planting,
    create_garden,
    delete_garden,
    garden_by_token,
    load_garden,
    recompute_light,
    remove_planting,
)

router = APIRouter(prefix="/api/v1/gardens", tags=["gardens"])


def _require(conn: sqlite3.Connection, token: str) -> Garden:
    """Resolve a token or 404.

    Never 403: telling a caller that a token exists but is not theirs is the one
    piece of information the token is meant to hide.
    """
    garden = garden_by_token(conn, token)
    if garden is None:
        raise HTTPException(status_code=404, detail="no such garden")
    return garden


def _to_out(garden: Garden) -> GardenOut:
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
            ObstacleOut(obstacle_id=o.obstacle_id, kind=o.kind, x=o.x, y=o.y,
                        radius=o.radius, height=o.height)
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
    return _to_out(_require(conn, token))


@router.post("/{token}/beds", response_model=GardenOut, status_code=status.HTTP_201_CREATED)
def create_bed(
    token: str,
    payload: BedCreate,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Add a bed. PolygonError, SoilTypeError and MoistureError all subclass
    ValueError, so they surface as 422 with their reason rather than as a 500."""
    garden = _require(conn, token)
    add_bed(conn, garden.garden_id, BedInput(
        name=payload.name, polygon=payload.polygon,
        soil_type=payload.soil_type, moisture=payload.moisture,
    ))
    return _to_out(load_garden(conn, garden.garden_id))


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
    garden = _require(conn, token)
    add_obstacle(conn, garden.garden_id, ObstacleInput(
        kind=payload.kind, x=payload.x, y=payload.y,
        radius=payload.radius, height=payload.height,
    ))
    recompute_light(conn, garden.garden_id)
    return _to_out(load_garden(conn, garden.garden_id))


@router.post("/{token}/recompute", response_model=GardenOut)
def recompute(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    garden = _require(conn, token)
    recompute_light(conn, garden.garden_id)
    return _to_out(load_garden(conn, garden.garden_id))


@router.delete("/{token}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> Response:
    delete_garden(conn, _require(conn, token).garden_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _require_bed(garden: Garden, bed_id: int) -> Bed:
    """A bed must belong to the garden the token opened.

    Without this, a valid token for one garden would let its holder reach any bed
    in the database by guessing an id — the capability would leak past the thing
    it names.
    """
    for bed in garden.beds:
        if bed.bed_id == bed_id:
            return bed
    raise HTTPException(status_code=404, detail=f"no such bed in this garden: {bed_id}")


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
    """Put a species in a bed. An unknown taxon raises ValueError -> 422."""
    garden = _require(conn, token)
    _require_bed(garden, bed_id)
    add_planting(conn, bed_id, taxon_id=payload.taxon_id, quantity=payload.quantity)
    return _to_out(load_garden(conn, garden.garden_id))


@router.delete("/{token}/plantings/{planting_id}", response_model=GardenOut)
def delete_planting(
    token: str,
    planting_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Remove a planting. Reached through its garden, never by a bare id."""
    garden = _require(conn, token)
    owned = conn.execute(
        """
        SELECT 1 FROM planting p JOIN bed b ON b.bed_id = p.bed_id
        WHERE p.planting_id = ? AND b.garden_id = ?
        """,
        (planting_id, garden.garden_id),
    ).fetchone()
    if owned is None:
        raise HTTPException(status_code=404, detail=f"no such planting: {planting_id}")
    remove_planting(conn, planting_id)
    return _to_out(load_garden(conn, garden.garden_id))


@router.get("/{token}/beds/{bed_id}/suggestions", response_model=BedSuggestions)
def bed_suggestions(
    token: str,
    bed_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    colour: str | None = None,
    include_trees: bool = False,
    exclude_planted: bool = True,
) -> BedSuggestions:
    """Species that suit this bed, ranked by fit against its own site vector.

    The bed's derived axes are the query, so the user never types an Ellenberg
    number. Trees and shrubs are excluded by default: a bed is a few square
    metres, and a hemlock that fits the light perfectly is still a useless
    suggestion.
    """
    garden = _require(conn, token)
    bed = _require_bed(garden, bed_id)

    axes = bed.site_axes
    if not axes:
        raise ValueError(
            f"bed {bed_id} has no site conditions yet — set soil and moisture, "
            "or recompute light, before asking for suggestions"
        )

    planted = frozenset(p.taxon_id for p in bed.plantings) if exclude_planted else frozenset()
    scored = rank_plants(
        load_candidates(conn),
        SiteVector(values=axes),
        SearchFilters(exclude_woody=not include_trees, exclude_taxa=planted),
        colour=colour,
    )
    return BedSuggestions(
        bed_id=bed.bed_id,
        bed_name=bed.name,
        site_axes=axes,
        total=len(scored),
        items=[to_summary(s) for s in scored[:limit]],
    )
