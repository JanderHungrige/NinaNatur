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
    BloomPalette,
    ChangeOut,
    FilterCountsOut,
    GapOut,
    GardenOut,
    GrowthForm,
    ImprovementsOut,
    MonthOut,
    PlantingCreate,
    PlantingVisibility,
    PlantSummary,
    ScoreOut,
    SightlinesOut,
    SpeciesContributionOut,
    TimelineOut,
    ViewpointIn,
)
from ninanatur.api.search import (
    ScoredPlant,
    SearchFilters,
    is_woody,
    load_candidates,
    rank_plants,
)
from ninanatur.bloom.improve import Change, garden_improvements
from ninanatur.bloom.palette import garden_palette
from ninanatur.bloom.score import garden_score
from ninanatur.bloom.timeline import TimelineMode, garden_timeline
from ninanatur.data.interactions import bird_counts, german_partner_totals
from ninanatur.data.names import resolve_one
from ninanatur.data.traits import resolve_trait
from ninanatur.fit.score import SiteVector
from ninanatur.garden.canopy import polygon_area
from ninanatur.garden.objects import ObjectKind, casts_shadow
from ninanatur.garden.plantings import add_planting, remove_planting
from ninanatur.garden.sightlines import Blocker, Target, Viewpoint, visibility
from ninanatur.garden.store import load_garden

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
        SELECT 1 FROM planting p JOIN element e ON e.element_id = p.element_id
        WHERE p.planting_id = ? AND e.garden_id = ?
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
        load_candidates(conn),
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
    # Split for presentation, not for the model. One ranking put every woody
    # plant below roughly 2,000 perennials — the same invisibility Wave 4 caused
    # by excluding them, and the catalogue's best forage plants are woody:
    # Salix caprea leads the whole database with 1,055 German partners.
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
        site_axes=axes,
        total=len(herbaceous),
        items=summarise(herbaceous[:limit]),
        woody=summarise(woody),
        woody_total=woody_total,
        filters={k: FilterCountsOut(**vars(v)) for k, v in ranked.report.items()},
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


@router.post("/{token}/sightlines", response_model=SightlinesOut)
def sightlines(
    token: str,
    viewpoint: ViewpointIn,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> SightlinesOut:
    """What is visible from a point in the garden.

    The same cylinders the shading model uses, seen from an eye instead of from
    the sun — so a hedge blocks sight exactly as it blocks light, and a raised
    bed stands above both.
    """
    garden = require_garden(conn, token)
    eye = Viewpoint(x=viewpoint.x, y=viewpoint.y, eye_height_m=viewpoint.eye_height_m)
    blockers = [
        Blocker(
            id=o.obstacle_id,
            footprint=o.footprint,
            height_m=o.height,
            estimated=o.height_source != "user",
        )
        # An element nobody has given a height to blocks nothing: a sightline
        # resting on an invented number is exactly what Wave 9 refused to draw.
        for o in garden.obstacles
        if o.height is not None
        # A lawn does not stand between you and anything.
        if casts_shadow(ObjectKind(o.kind))
    ]

    rows: list[PlantingVisibility] = []
    estimated = 0
    for bed in garden.beds:
        centre = _bed_centre(bed.polygon)
        for planting in bed.plantings:
            height = _plant_height(conn, planting.taxon_id)
            if height is None:
                # Unknown stays unknown, at this layer as at every other.
                rows.append(
                    PlantingVisibility(
                        planting_id=planting.planting_id,
                        name=planting.display_name,
                        bed_id=bed.bed_id,
                        height_m=None,
                        visible=None,
                        visible_from_m=None,
                        hidden_by=None,
                        estimated=False,
                    )
                )
                continue
            seen = visibility(
                eye,
                Target(x=centre[0], y=centre[1], base_m=bed.height_above_ground, height_m=height),
                blockers,
            )
            estimated += 1 if seen.estimated else 0
            rows.append(
                PlantingVisibility(
                    planting_id=planting.planting_id,
                    name=planting.display_name,
                    bed_id=bed.bed_id,
                    height_m=height,
                    visible=seen.visible,
                    visible_from_m=seen.visible_from_m,
                    hidden_by=seen.hidden_by,
                    estimated=seen.estimated,
                )
            )
    return SightlinesOut(plantings=rows, estimated_count=estimated)


def _bed_centre(polygon: list[list[float]]) -> tuple[float, float]:
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _plant_height(conn: sqlite3.Connection, taxon_id: int | None) -> float | None:
    if taxon_id is None:
        return None
    trait = resolve_trait(conn, taxon_id, "height_max_m")
    return None if trait is None else trait.value_num
