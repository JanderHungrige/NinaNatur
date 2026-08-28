"""Routes for what goes *into* a garden: plantings, suggestions and the bloom year.

Split from `gardens.py`, which owns the garden itself. The two share `_require`
and `_require_bed`, because the rule they enforce — a token names one garden, and
a bed id is not a capability — must be identical in both.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_bed, require_garden, to_out
from ninanatur.api.plants import to_summary
from ninanatur.api.schemas import (
    BedSuggestions,
    ChangeOut,
    GapOut,
    GardenOut,
    ImprovementsOut,
    MonthOut,
    PlantingCreate,
    ScoreOut,
    SpeciesContributionOut,
    TimelineOut,
)
from ninanatur.api.search import SearchFilters, load_candidates, rank_plants
from ninanatur.bloom.improve import Change, garden_improvements
from ninanatur.bloom.score import garden_score
from ninanatur.bloom.timeline import TimelineMode, garden_timeline
from ninanatur.fit.score import SiteVector
from ninanatur.garden.store import add_planting, load_garden, remove_planting

router = APIRouter(prefix="/api/v1/gardens", tags=["planning"])


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
    garden = require_garden(conn, token)
    require_bed(garden, bed_id)
    add_planting(conn, bed_id, taxon_id=payload.taxon_id, quantity=payload.quantity)
    return to_out(load_garden(conn, garden.garden_id))


@router.delete("/{token}/plantings/{planting_id}", response_model=GardenOut)
def delete_planting(
    token: str,
    planting_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> GardenOut:
    """Remove a planting. Reached through its garden, never by a bare id."""
    garden = require_garden(conn, token)
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
    return to_out(load_garden(conn, garden.garden_id))


@router.get("/{token}/beds/{bed_id}/suggestions", response_model=BedSuggestions)
def bed_suggestions(
    token: str,
    bed_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    colour: str | None = None,
    include_trees: bool = False,
    include_introduced: bool = False,
    exclude_planted: bool = True,
) -> BedSuggestions:
    """Species that suit this bed, ranked by fit against its own site vector.

    The bed's derived axes are the query, so the user never types an Ellenberg
    number. Trees and shrubs are excluded by default: a bed is a few square
    metres, and a hemlock that fits the light perfectly is still a useless
    suggestion. Introduced species are excluded for a different reason: the
    product promises native plants, and a third of the catalogue is not.
    """
    garden = require_garden(conn, token)
    bed = require_bed(garden, bed_id)

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
        SearchFilters(
            exclude_woody=not include_trees,
            exclude_introduced=not include_introduced,
            exclude_taxa=planted,
        ),
        colour=colour,
    )
    return BedSuggestions(
        bed_id=bed.bed_id,
        bed_name=bed.name,
        site_axes=axes,
        total=len(scored),
        items=[to_summary(s) for s in scored[:limit]],
    )


@router.get("/{token}/timeline", response_model=TimelineOut)
def timeline(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
    forage: bool = True,
) -> TimelineOut:
    """The garden's bloom year, month by month, with gaps marked.

    `forage=true` (the default) weights each flowering planting by its counted
    German insect partners, so a month of nectarless cultivars is correctly a
    gap. `forage=false` counts every planting equally, for planning by looks.
    """
    garden = require_garden(conn, token)
    mode = TimelineMode.FORAGE if forage else TimelineMode.VISUAL
    result = garden_timeline(conn, garden, mode=mode)
    return TimelineOut(
        mode=result.mode.value,
        months=[
            MonthOut(month=m.month, coverage=m.coverage, species=list(m.species))
            for m in sorted(result.months.values(), key=lambda x: x.month)
        ],
        gaps=[GapOut(months=list(g.months), length=g.length) for g in result.gaps],
        plantings_total=result.plantings_total,
        plantings_without_interaction_data=result.plantings_without_interaction_data,
        is_empty=result.is_empty,
    )


@router.get("/{token}/score", response_model=ScoreOut)
def score(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> ScoreOut:
    """What this planting is worth to insects, with its components."""
    result = garden_score(conn, require_garden(conn, token))
    return ScoreOut(
        score=result.score,
        # JSON object keys are strings; the month order is carried by the value,
        # not by relying on a client to sort numeric-looking keys.
        by_month={str(m): v for m, v in sorted(result.by_month.items())},
        by_species=[
            SpeciesContributionOut(
                taxon_id=c.taxon_id, canonical_name=c.canonical_name,
                german_partners=c.german_partners, origin=c.origin,
                forage=c.forage, months=list(c.months),
            )
            for c in result.by_species
        ],
        by_group=result.by_group,
        plantings_total=result.plantings_total,
        plantings_without_interaction_data=result.plantings_without_interaction_data,
        is_empty=result.is_empty,
    )


def _change_out(change: Change) -> ChangeOut:
    return ChangeOut(
        taxon_id=change.taxon_id,
        canonical_name=change.canonical_name,
        bed_id=change.bed_id,
        bed_name=change.bed_name,
        gain=change.gain,
        resulting_score=change.resulting_score,
        reason=change.reason,
        german_partners=change.german_partners,
        replaces_planting_id=change.replaces_planting_id,
        replaces_name=change.replaces_name,
    )


@router.get("/{token}/improvements", response_model=ImprovementsOut)
def improvements(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> ImprovementsOut:
    """What to plant, and what it would gain.

    Additions come first because they are the safer advice: a swap removes
    something, and the score will recommend removing a valuable plant whose month
    is already saturated. See the known issue in 19-swap-suggestions.
    """
    result = garden_improvements(conn, require_garden(conn, token))
    return ImprovementsOut(
        current_score=result.current_score,
        additions=[_change_out(c) for c in result.additions],
        swaps=[_change_out(c) for c in result.swaps],
    )
