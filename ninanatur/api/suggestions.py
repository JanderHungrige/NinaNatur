"""A bed's suggestions: the species that suit it, ranked against its own site.

Split from `planning.py` on 2026-09-11, when that file had reached 470 lines. The
ranking lives in `api/search.py`; this is the route that turns a bed into a
query, and a ranking into the list a gardener reads.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ninanatur.api.candidate_cache import candidate_set
from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_bed, require_garden
from ninanatur.api.plants import to_summary
from ninanatur.api.schemas import BedSuggestions, FilterCountsOut, GrowthForm, PlantSummary
from ninanatur.api.search import (
    RankedResult,
    ScoredPlant,
    SearchFilters,
    is_woody,
    rank_plants,
    with_observed,
)
from ninanatur.data.interactions import bird_counts, german_partner_totals
from ninanatur.fit.score import SiteVector
from ninanatur.garden.canopy import polygon_area
from ninanatur.garden.models import Element
from ninanatur.garden.observations import manual_colours

router = APIRouter(prefix="/api/v1/gardens", tags=["planning"])

# A shortlist, not a second catalogue. Woody plants are a small set of large
# decisions; twenty of them is a list nobody reads.
WOODY_LIMIT = 8


def _by_value(conn: sqlite3.Connection, woody: list[ScoredPlant]) -> list[ScoredPlant]:
    """Order a woody shortlist by what it is worth to animals, not by site fit.

    Site fit already decided which of these are candidates at all. Ordering the
    survivors by fit again put mistletoe and Ruscus at the top of every list and
    left Salix caprea — 1,055 German insect partners, the highest count in the
    catalogue — below the cut, which is the invisibility this whole feature
    exists to end. A shrub is planted for what visits it.

    Room is deliberately not part of the order: the plant that is worth the most
    is worth seeing even when it does not fit, with what it would take beside it.
    """
    ids = [s.plant.taxon_id for s in woody]
    insects = german_partner_totals(conn, ids)
    birds_by_taxon = bird_counts(conn, ids)
    return sorted(
        woody,
        key=lambda s: (
            -(insects.get(s.plant.taxon_id, 0) + birds_by_taxon.get(s.plant.taxon_id, 0)),
            -s.score,
        ),
    )


@router.get("/{token}/beds/{bed_id}/suggestions", response_model=BedSuggestions)
def bed_suggestions(
    token: str,
    bed_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    colour: str | None = None,
    height_min: Annotated[float | None, Query(ge=0)] = None,
    height_max: Annotated[float | None, Query(ge=0)] = None,
    flowering_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    growth_form: GrowthForm | None = None,
    include_unknown: bool = False,
    include_trees: bool = True,
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

    planted = (
        frozenset(p.taxon_id for p in bed.plantings if p.taxon_id is not None)
        if exclude_planted
        else frozenset()
    )
    area = polygon_area(bed.polygon)
    ranked = rank_plants(
        # Which colours were entered by hand, so the list can say so. It no
        # longer changes *which* colour is shown: a hand entry is a trait row
        # now, and `load_candidates` already resolved it against every other
        # source before the set was held.
        with_observed(candidate_set(conn), manual_colours(conn)),
        SiteVector(values=axes),
        SearchFilters(
            height_min=height_min,
            height_max=height_max,
            flowering_month=flowering_month,
            growth_form=growth_form.value if growth_form is not None else None,
            bed_area_m2=area,
            include_unknown=include_unknown,
            exclude_woody=not include_trees,
            exclude_introduced=not include_introduced,
            exclude_taxa=planted,
        ),
        colour=colour,
    )
    return _presented(conn, bed, ranked, limit=limit, area=area)


def _presented(
    conn: sqlite3.Connection, bed: Element, ranked: RankedResult, *, limit: int, area: float,
) -> BedSuggestions:
    """The ranking as the list a gardener reads, herbaceous and woody apart.

    Split for presentation, not for the model. One ranking put every woody
    plant below roughly 2,000 perennials — the same invisibility Wave 4 caused
    by excluding them, and the catalogue's best forage plants are woody:
    Salix caprea leads the whole database with 1,055 German partners.
    """
    herbaceous = [s for s in ranked.items if not is_woody(s.plant)]
    woody_total = sum(1 for s in ranked.items if is_woody(s.plant))
    woody = _by_value(conn, [s for s in ranked.items if is_woody(s.plant)])[:WOODY_LIMIT]
    page = herbaceous[:limit] + woody
    birds = bird_counts(conn, [s.plant.taxon_id for s in page])

    def summarise(items: list[ScoredPlant]) -> list[PlantSummary]:
        return [to_summary(s, birds.get(s.plant.taxon_id), area) for s in items]

    return BedSuggestions(
        bed_id=bed.bed_id,
        bed_name=bed.name or "",
        site_axes=bed.site_axes,
        total=len(herbaceous),
        items=summarise(herbaceous[:limit]),
        woody=summarise(woody),
        woody_total=woody_total,
        filters={k: FilterCountsOut(**vars(v)) for k, v in ranked.report.items()},
    )
