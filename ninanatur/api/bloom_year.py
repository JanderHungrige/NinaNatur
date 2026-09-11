"""What a garden's planting adds up to: its bloom year, its worth to insects,
what would raise that, and the colours each bed carries month by month.

Split from `planning.py` on 2026-09-11, when that file had reached 470 lines.
Every route here reads a garden and changes nothing.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_garden
from ninanatur.api.schemas import (
    BloomPalette,
    ChangeOut,
    GapOut,
    ImprovementsOut,
    MonthOut,
    ScoreOut,
    SpeciesContributionOut,
    TimelineOut,
)
from ninanatur.bloom.improve import Change, garden_improvements
from ninanatur.bloom.palette import garden_palette
from ninanatur.bloom.score import garden_score
from ninanatur.bloom.timeline import TimelineMode, garden_timeline

router = APIRouter(prefix="/api/v1/gardens", tags=["planning"])


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


@router.get("/{token}/bloom", response_model=BloomPalette)
def bloom(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> BloomPalette:
    """Which colours each bed carries in each month.

    Server-side because the frontend has a bed's plantings but neither their
    flowering windows nor their colours, and sending those per planting would
    ship the catalogue to the browser to render a swatch.
    """
    garden = require_garden(conn, token)
    return BloomPalette(**garden_palette(conn, garden.garden_id))
