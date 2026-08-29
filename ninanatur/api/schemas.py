"""Response shapes — the contract Waves 3 and 4 consume unchanged.

Unknown is transported as `null`, never as an omitted field and never as zero.
A client must be able to tell "no data" from "zero", and most of this catalogue
is partly unknown.
"""
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from ninanatur.garden.objects import ObjectKind


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
    # German bird species recorded as partners, or None when GloBI holds no
    # relations at all. Zero and "never recorded" are different facts.
    bird_partners: int | None
    # Estimated mature footprint in m², derived from height — the catalogue
    # records no crown width. None when the height was never recorded.
    space_m2: float | None
    # Whether that fits the bed it was suggested for. None when either number is
    # missing; False marks a plant shown anyway, with what it would take.
    fits_bed: bool | None
    fit: FitOut


class GrowthForm(StrEnum):
    """The growth forms the catalogue actually records.

    A closed set rather than a free string. The value never reaches SQL, but an
    unbounded parameter that silently matches nothing is its own kind of lie —
    the user cannot tell a typo from an empty catalogue.
    """

    forb = "forb"
    herb = "herb"
    graminoid = "graminoid"
    shrub = "shrub"
    subshrub = "subshrub"
    tree = "tree"


class FilterCountsOut(BaseModel):
    """How one active filter divided the candidate set.

    Reported so the UI can say what was left out. `unknown` is not a rounding
    error: height is recorded for 44% of German species and colour for 6.6%, and
    a filter that hides that is indistinguishable from one that is broken.
    """

    matched: int
    unknown: int
    excluded: int


class PlantSearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[PlantSummary]
    filters: dict[str, FilterCountsOut] = {}


class BedSuggestions(BaseModel):
    """Suggestions for one bed, with the site vector they were ranked against —
    so the UI can say what it matched on rather than showing a bare list."""

    bed_id: int
    bed_name: str
    site_axes: dict[str, float]
    total: int
    items: list[PlantSummary]
    # Woody species, listed apart rather than mixed in or hidden.
    #
    # A bed is a marked area and a tree in it is a fact about the planting, not
    # a different kind of bed — so this is a presentation split, not a second
    # data model. Mixed into one ranking, every woody plant sorted below ~2,000
    # perennials, which is the same invisibility Wave 4 caused by excluding
    # them outright, only better argued.
    woody: list[PlantSummary] = []
    woody_total: int = 0
    filters: dict[str, FilterCountsOut] = {}


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


class SpeciesContributionOut(BaseModel):
    taxon_id: int
    canonical_name: str
    german_partners: int | None
    origin: str
    forage: float
    months: list[int]


class ScoreOut(BaseModel):
    """The score with everything needed to argue about it — a score a user cannot
    interrogate is decoration, and this one will be trusted more than it deserves."""

    score: float
    by_month: dict[str, float]
    by_species: list[SpeciesContributionOut]
    by_group: dict[str, int]
    plantings_total: int
    plantings_without_interaction_data: int
    is_empty: bool


class ChangeOut(BaseModel):
    taxon_id: int
    canonical_name: str
    bed_id: int
    bed_name: str
    gain: float
    resulting_score: float
    reason: str
    german_partners: int | None
    replaces_planting_id: int | None
    replaces_name: str | None


class ImprovementsOut(BaseModel):
    current_score: float
    additions: list[ChangeOut]
    swaps: list[ChangeOut]


class PartnersOut(BaseModel):
    german: int
    global_total: int
    unmatched: int
    match_rate: float
    by_kind: dict[str, int]
    # German bird species recorded as partners. Reported next to `german`, never
    # inside it: this product's number is called Insektenwert, and folding birds
    # in would change every score already shown without explaining why.
    birds: int = 0


class SpeciesInfoOut(BaseModel):
    """A description and photo. `licence` and `page_url` are conditions of use,
    not decoration — the UI may not show the extract without them."""

    title: str
    extract: str
    thumbnail_url: str | None
    page_url: str
    language: str
    licence: str


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
    # A closed set, validated before it reaches any query. A free string means
    # the shading table silently misses a value and nobody finds out.
    kind: ObjectKind
    x: float
    y: float
    radius: float = Field(gt=0, le=500)
    height: float = Field(gt=0, le=200)
    label: str | None = Field(default=None, max_length=200)


class ObstacleUpdate(BaseModel):
    """Every field optional: an edit says what changed, not what everything is."""

    kind: ObjectKind | None = None
    x: float | None = None
    y: float | None = None
    radius: float | None = Field(default=None, gt=0, le=500)
    height: float | None = Field(default=None, gt=0, le=200)
    label: str | None = Field(default=None, max_length=200)


class BedUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    soil_type: str | None = None
    moisture: str | None = None
    # A bed cannot be below the ground it stands on, and 20 m is a roof garden.
    height_above_ground: float | None = Field(default=None, ge=0, le=20)
    label: str | None = Field(default=None, max_length=200)


class PlantingCreate(BaseModel):
    """Either a species from the catalogue, or the words the user typed.

    Both are ordinary. The catalogue holds 8,939 German species and no cultivars,
    so a name it cannot match is an answer rather than a mistake.
    """

    taxon_id: int | None = Field(default=None, gt=0)
    raw_name: str | None = Field(default=None, max_length=200)
    quantity: int = Field(default=1, ge=1, le=10000)

    @model_validator(mode="after")
    def one_or_the_other(self) -> PlantingCreate:
        if self.taxon_id is None and not (self.raw_name or "").strip():
            raise ValueError("either taxon_id or raw_name is required")
        return self


class PlantingOut(BaseModel):
    planting_id: int
    # None when the catalogue could not name it — `raw_name` is then the plant.
    taxon_id: int | None
    canonical_name: str | None
    raw_name: str | None
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
    # Required, not defaulted: the response always carries both, and a default
    # here makes them optional in the generated client for no reason.
    height_above_ground: float
    label: str | None
    plantings: list[PlantingOut]


class ObstacleOut(BaseModel):
    obstacle_id: int
    kind: str
    label: str | None
    x: float
    y: float
    radius: float
    height: float


class BedMonthColours(BaseModel):
    month: int
    colours: list[str]
    # A count, never a colour. Flower colour is recorded for 6.6% of the
    # catalogue, and a bed filled in for "we do not know" is an answer the data
    # does not support.
    unknown: int
    flowering: int


class BedPalette(BaseModel):
    bed_id: int
    months: list[BedMonthColours]


class BloomPalette(BaseModel):
    beds: list[BedPalette]


class SourceOut(BaseModel):
    name: str
    licence: str
    url: str
    contributes: str


class StatsOut(BaseModel):
    """What the catalogue actually holds, counted rather than typed.

    Wave 1's landing page wrote "3.087 Arten" into its HTML by hand, and it was
    wrong the first time the catalogue was rebuilt. A page that states a number
    is making a claim.
    """

    species: int
    species_with_full_site_profile: int
    # Recorded relationships between the plants here and animals recorded in
    # Germany. Counted from the summaries the runtime actually serves — the
    # 600k raw GloBI rows are ingest-time data and are not in the shipped
    # catalogue at all, so claiming them would be claiming data we do not ship.
    animal_partnerships: int
    german_animals: int
    german_names: int
    sources: list[SourceOut]


class GardenOut(BaseModel):
    # Reported, never inferred from an empty list: a score computed over 4 of 7
    # plantings has to be able to say so.
    unidentified_plantings: int = 0
    share_token: str
    name: str
    latitude: float
    longitude: float
    created_at: str
    updated_at: str
    beds: list[BedOut]
    obstacles: list[ObstacleOut]
