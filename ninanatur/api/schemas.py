"""Response shapes — the contract Waves 3 and 4 consume unchanged.

Unknown is transported as `null`, never as an omitted field and never as zero.
A client must be able to tell "no data" from "zero", and most of this catalogue
is partly unknown.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class AxisFitOut(BaseModel):
    """Why one axis scored what it did — Wave 4 renders the band, not the number."""

    band: str
    score: float
    half_widths_away: float
    species_value: float
    niche_width: float
    width_estimated: bool


class FitOut(BaseModel):
    score: float
    axes: dict[str, AxisFitOut]


class TraitOut(BaseModel):
    value: float | str | None
    unit: str | None = None
    source: str
    license: str
    alternatives: list[dict[str, object]] = Field(default_factory=list)


class PlantSummary(BaseModel):
    taxon_id: int
    canonical_name: str
    family: str | None
    height_max_m: float | None
    flowering_start_month: int | None
    flowering_end_month: int | None
    flower_colour: str | None
    colour_known: bool
    fit: FitOut


class PlantSearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PlantSummary]


class PartnersOut(BaseModel):
    german: int
    global_total: int
    unmatched: int
    match_rate: float
    by_kind: dict[str, int]


class PlantDetail(BaseModel):
    taxon_id: int
    canonical_name: str
    scientific_name: str | None
    family: str | None
    traits: dict[str, TraitOut]
    partners: PartnersOut | None
