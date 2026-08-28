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


class BedSuggestions(BaseModel):
    """Suggestions for one bed, with the site vector they were ranked against —
    so the UI can say what it matched on rather than showing a bare list."""

    bed_id: int
    bed_name: str
    site_axes: dict[str, float]
    total: int
    items: list[PlantSummary]


class MonthOut(BaseModel):
    month: int
    coverage: float
    species: list[str]


class GapOut(BaseModel):
    months: list[int]
    length: int


class TimelineOut(BaseModel):
    """The bloom year. `plantings_without_interaction_data` is reported so a
    timeline built mostly on unknowns is visible rather than merely optimistic."""

    mode: str
    months: list[MonthOut]
    gaps: list[GapOut]
    plantings_total: int
    plantings_without_interaction_data: int
    is_empty: bool


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


# --- gardens ---------------------------------------------------------------


class GardenCreate(BaseModel):
    """Creating a garden. Latitude and longitude are range-checked here, before
    they reach solar code that would happily compute a sun path for latitude 500."""

    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class GardenCreated(BaseModel):
    """The token is returned; the numeric id deliberately is not."""

    share_token: str
    name: str


class BedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    polygon: list[list[float]]
    soil_type: str | None = None
    moisture: str | None = None


class ObstacleCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=50)
    x: float
    y: float
    radius: float = Field(gt=0, le=500)
    height: float = Field(gt=0, le=200)


class PlantingCreate(BaseModel):
    taxon_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=10000)


class PlantingOut(BaseModel):
    planting_id: int
    taxon_id: int
    canonical_name: str
    quantity: int
    added_at: str


class BedOut(BaseModel):
    bed_id: int
    name: str
    polygon: list[list[float]]
    soil_type: str | None
    moisture: str | None
    ellenberg_l: float | None
    ellenberg_m: float | None
    ellenberg_n: float | None
    ellenberg_r: float | None
    sun_hours: float | None
    light_computed_at: str | None
    plantings: list[PlantingOut]


class ObstacleOut(BaseModel):
    obstacle_id: int
    kind: str
    x: float
    y: float
    radius: float
    height: float


class GardenOut(BaseModel):
    share_token: str
    name: str
    latitude: float
    longitude: float
    created_at: str
    updated_at: str
    beds: list[BedOut]
    obstacles: list[ObstacleOut]
