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
from ninanatur.api.schemas_plants import BedSuggestions, FilterCountsOut, GrowthForm, PlantSummary
from ninanatur.api.search import (
    RankedResult,
    ScoredPlant,
    SearchFilters,
    is_woody,
    rank_plants,
    with_observed,
)
from ninanatur.data.interactions import bird_counts
from ninanatur.fit.light_fit import light_mismatch
from ninanatur.fit.score import SiteVector
from ninanatur.garden.canopy import polygon_area
from ninanatur.garden.light_state import LightState, light_state
from ninanatur.garden.models import Element
from ninanatur.garden.observations import manual_colours

router = APIRouter(prefix="/api/v1/gardens", tags=["planning"])

# A shortlist, not a second catalogue. Woody plants are a small set of large
# decisions; twenty of them is a list nobody reads.
WOODY_LIMIT = 8


def _woody_order(woody: list[ScoredPlant]) -> list[ScoredPlant]:
    """The woody shortlist in the main list's order — growing conditions, then
    insect value (`fit.rank`) — but with room left out of it.

    Ordered by animal partners alone, it gave a full-sun bed, a semi-shade bed
    and a bed with no light the same eight willows; ordered by fit alone, it
    put mistletoe and Ruscus at the top of every list and Salix caprea, the
    catalogue's most visited plant, below the cut. The combined order keeps
    both lessons: among the shrubs that grow well here, the one insects visit
    most leads. Birds are shown on the row and no longer added to the order —
    what a bird is worth against an insect is a judgement this product has not
    made (doc 25), and the owner asked for the Insektenwert.

    Room is deliberately not part of the order: the plant that is worth the most
    is worth seeing even when it does not fit, with what it would take beside it.
    The light is: what it does not suit, shown on request, still comes last.
    """
    return sorted(woody, key=lambda s: (light_mismatch(s.fit) is not None, -s.rank, -s.score))


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
    include_light_unsuitable: bool = False,
) -> BedSuggestions:
    """Species that suit this bed, in the order `fit.rank` describes (doc 13).

    Woody plants get a shortlist of their own. Introduced species are left out,
    and unless asked for so are those the light does not suit (`light_verdict`).
    `light_state` says whether there was a light value to judge by.
    """
    garden = require_garden(conn, token)
    bed = require_bed(garden, bed_id)
    site = _site_of(bed)
    planted = frozenset(p.taxon_id for p in bed.plantings if p.taxon_id is not None)
    area = polygon_area(bed.polygon)
    ranked = rank_plants(
        # Which colours were entered by hand, so the list can say so. Not which
        # colour is shown: `load_candidates` already resolved a hand entry — a
        # trait row now — against every other source.
        with_observed(candidate_set(conn), manual_colours(conn)),
        site,
        SearchFilters(
            height_min=height_min,
            height_max=height_max,
            flowering_month=flowering_month,
            growth_form=growth_form.value if growth_form is not None else None,
            bed_area_m2=area,
            include_unknown=include_unknown,
            exclude_woody=not include_trees,
            exclude_introduced=not include_introduced,
            exclude_taxa=planted if exclude_planted else frozenset(),
            exclude_light_unsuitable=not include_light_unsuitable,
            light_misfits_last=include_light_unsuitable,
        ),
        colour=colour,
    )
    light = light_state(conn, garden, bed)
    return _presented(conn, bed, ranked, limit=limit, area=area, light=light)


def _site_of(bed: Element) -> SiteVector:
    """The bed's derived axes as the query, so the user never types an Ellenberg
    number — or a 422 while it has none at all."""
    axes = bed.site_axes
    if not axes:
        raise ValueError(
            f"bed {bed.bed_id} has no site conditions yet — set soil and moisture, "
            "or recompute light, before asking for suggestions"
        )
    return SiteVector(values=axes)


def _presented(
    conn: sqlite3.Connection, bed: Element, ranked: RankedResult, *, limit: int, area: float,
    light: LightState,
) -> BedSuggestions:
    """The ranking as the list a gardener reads, herbaceous and woody apart.

    Split for presentation, not for the model. One ranking put every woody
    plant below roughly 2,000 perennials — the same invisibility Wave 4 caused
    by excluding them, and the catalogue's best forage plants are woody:
    Salix caprea leads the whole database with 1,055 German partners.
    """
    herbaceous = [s for s in ranked.items if not is_woody(s.plant)]
    candidates = [s for s in ranked.items if is_woody(s.plant)]
    woody_total = len(candidates)
    woody = _woody_order(candidates)[:WOODY_LIMIT]
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
        light_state=light,
    )
