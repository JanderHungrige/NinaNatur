"""Plant search and detail routes.

Parameters in, schema out. The decision about what matches lives in
`ninanatur.api.search`; the ranking is not re-derived here or anywhere else.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ninanatur.api.deps import get_connection
from ninanatur.api.schemas import (
    AxisFitOut,
    FilterCountsOut,
    FitOut,
    GrowthForm,
    PartnersOut,
    PlantDetail,
    PlantSearchResponse,
    PlantSummary,
    SpeciesInfoOut,
    TraitOut,
)
from ninanatur.api.search import (
    AXIS_PARAMS,
    ScoredPlant,
    SearchFilters,
    load_candidates,
    rank_plants,
)
from ninanatur.data.interactions import german_partner_counts
from ninanatur.data.species_info import species_info
from ninanatur.data.traits import resolve_traits_for
from ninanatur.fit.score import SiteVector

router = APIRouter(prefix="/api/v1", tags=["plants"])

MAX_LIMIT = 200


def to_summary(scored: ScoredPlant) -> PlantSummary:
    plant = scored.plant
    start = plant.number("flowering_start_month")
    end = plant.number("flowering_end_month")
    return PlantSummary(
        taxon_id=plant.taxon_id,
        canonical_name=plant.canonical_name,
        family=plant.family,
        height_max_m=plant.number("height_max_m"),
        flowering_start_month=int(start) if start is not None else None,
        flowering_end_month=int(end) if end is not None else None,
        flower_colour=plant.text("flower_colour"),
        colour_known=plant.text("flower_colour") is not None,
        fit=FitOut(
            score=round(scored.score, 4),
            axes={
                axis: AxisFitOut(
                    band=fit.band.value,
                    score=round(fit.score, 4),
                    half_widths_away=round(fit.half_widths_away, 3),
                    species_value=round(fit.value, 3),
                    niche_width=round(fit.width, 3),
                    width_estimated=fit.width_estimated,
                )
                for axis, fit in scored.fit.explanation.items()
            },
        ),
    )


@router.get("/plants", response_model=PlantSearchResponse)
def search_plants(
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
    light: Annotated[float | None, Query(ge=0, le=10)] = None,
    moisture: Annotated[float | None, Query(ge=0, le=10)] = None,
    nutrients: Annotated[float | None, Query(ge=0, le=10)] = None,
    reaction: Annotated[float | None, Query(ge=0, le=10)] = None,
    temperature: Annotated[float | None, Query(ge=0, le=10)] = None,
    height_min: Annotated[float | None, Query(ge=0)] = None,
    height_max: Annotated[float | None, Query(ge=0)] = None,
    flowering_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    growth_form: GrowthForm | None = None,
    include_unknown: bool = False,
    colour: str | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PlantSearchResponse:
    """Species ranked by how well they fit the given site conditions."""
    axes = {
        AXIS_PARAMS[name]: value
        for name, value in (
            ("light", light), ("moisture", moisture), ("nutrients", nutrients),
            ("reaction", reaction), ("temperature", temperature),
        )
        if value is not None
    }
    if not axes:
        # Without an axis there is nothing to rank by. A 200 here would be a
        # confidently arbitrary answer rather than an empty one.
        raise ValueError(
            "at least one site axis is required "
            "(light, moisture, nutrients, reaction, temperature)"
        )

    ranked = rank_plants(
        load_candidates(conn),
        SiteVector(values=axes),
        SearchFilters(
            height_min=height_min,
            height_max=height_max,
            flowering_month=flowering_month,
            growth_form=growth_form,
            include_unknown=include_unknown,
        ),
        colour=colour,
    )
    page = ranked.items[offset : offset + limit]
    return PlantSearchResponse(
        total=len(ranked.items),
        limit=limit,
        offset=offset,
        items=[to_summary(s) for s in page],
        filters={k: FilterCountsOut(**vars(v)) for k, v in ranked.report.items()},
    )


@router.get("/plants/{taxon_id}", response_model=PlantDetail)
def plant_detail(
    taxon_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> PlantDetail:
    """One species, every trait with the source behind it."""
    row = conn.execute(
        "SELECT taxon_id, canonical_name, scientific_name, family FROM taxon WHERE taxon_id = ?",
        (taxon_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"no such taxon: {taxon_id}")

    traits = {
        key: TraitOut(
            value=t.value_num if t.value_num is not None else t.value_text,
            unit=t.unit,
            source=t.source,
            license=t.license,
            alternatives=[
                {
                    "value": a.value_num if a.value_num is not None else a.value_text,
                    "source": a.source,
                }
                for a in t.alternatives
            ],
        )
        for key, t in resolve_traits_for(conn, taxon_id).items()
    }
    counts = german_partner_counts(conn, taxon_id)
    return PlantDetail(
        taxon_id=taxon_id,
        canonical_name=row["canonical_name"],
        scientific_name=row["scientific_name"],
        family=row["family"],
        traits=traits,
        partners=None
        if counts is None
        else PartnersOut(
            german=counts.german,
            global_total=counts.global_total,
            unmatched=counts.unmatched,
            match_rate=round(counts.match_rate, 4),
            by_kind=counts.by_kind,
        ),
    )


@router.get("/plants/{taxon_id}/info", response_model=SpeciesInfoOut)
def plant_info(
    taxon_id: int,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> SpeciesInfoOut:
    """A description and photograph, from Wikipedia, cached on this deployment.

    404 when no article exists in either language — an honest absence rather than
    an empty panel that looks like a loading failure.
    """
    info = species_info(conn, taxon_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"no article for taxon {taxon_id}")
    return SpeciesInfoOut(
        title=info.title,
        extract=info.extract,
        thumbnail_url=info.thumbnail_url,
        page_url=info.page_url,
        language=info.language,
        licence=info.licence,
    )
