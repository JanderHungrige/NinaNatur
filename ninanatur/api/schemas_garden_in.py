"""What a caller may send about a garden, and the limits on it.

Every input refuses NaN and Infinity (`FINITE`) and keeps its coordinates
inside `COORD_LIMIT_M` (`Metres`). Split from `schemas.py` in Wave 21, which
re-exports every name here.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ninanatur.garden.footprint import Shape
from ninanatur.garden.objects import ObjectKind

#: How far from its anchor anything in a garden may be drawn, in metres.
#:
#: A garden is not four kilometres across, and without this the API accepted an
#: obstacle at x = 1e9 — after which the light grid spanned a billion metres and
#: `POST /light` stopped answering. The largest legitimate plan is a plot plus the
#: neighbours the map import brings in, well inside one kilometre either way.
COORD_LIMIT_M = 2000.0


#: The most corners one outline may have. The freehand tool already capped
#: `points` at this; a bed polygon took two hundred thousand.
MAX_CORNERS = 500


#: The longest edge of a map selection's bounding box. A three-point outline
#: across the country sent Overpass a query over half the republic and held the
#: server for 41 seconds; a garden plot is never a kilometre long.
MAX_OUTLINE_EDGE_M = 1000.0


#: Every input model refuses NaN and Infinity. pydantic allows both by default;
#: NaN then broke the response's JSON and surfaced as a 500, and Infinity was
#: stored and poisoned every extent and shadow computed after it.
FINITE = ConfigDict(allow_inf_nan=False)


Metres = Annotated[float, Field(ge=-COORD_LIMIT_M, le=COORD_LIMIT_M, allow_inf_nan=False)]


#: One corner: x and y, in metres from the anchor.
Corner = Annotated[list[Metres], Field(min_length=2, max_length=2)]


class GardenCreate(BaseModel):
    """Creating a garden. Latitude and longitude are range-checked here, before
    they reach solar code that would happily compute a sun path for latitude 500."""

    model_config = FINITE

    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class BedCreate(BaseModel):
    model_config = FINITE

    name: str = Field(min_length=1, max_length=200)
    # An upper bound only. "At least three corners" stays with the domain check
    # behind this, which says so in words; pydantic would answer the same thing
    # as a structured list the page does not read.
    polygon: list[Corner] = Field(max_length=MAX_CORNERS)
    soil_type: str | None = None
    moisture: str | None = None


class ObstacleCreate(BaseModel):
    model_config = FINITE

    # A closed set, validated before it reaches any query. A free string means
    # the shading table silently misses a value and nobody finds out.
    kind: ObjectKind
    x: Metres
    y: Metres
    #: `circle` | `rect` | `polygon`. Omitted means the kind's own default.
    shape: Shape | None = None
    #: Metres. For a circle this is the diameter.
    width: float | None = Field(default=None, gt=0, le=500)
    depth: float | None = Field(default=None, gt=0, le=500)
    rotation: float = Field(default=0.0, ge=-360, le=360)
    #: Freehand outlines only. Bounded in count and extent before storage.
    points: list[Corner] | None = Field(default=None, max_length=MAX_CORNERS)
    height: float | None = Field(default=None, gt=0, le=200)
    label: str | None = Field(default=None, max_length=200)


class RoofShape(StrEnum):
    """Mirrors `garden.roofs.Roof`; a pytest guard keeps the two in step."""

    FLAT = "flat"
    GABLE = "gable"
    HIP = "hip"
    PENT = "pent"
    MIX = "mix"
    OTHER = "other"
    UNKNOWN = "unknown"


class ObstacleUpdate(BaseModel):
    """Every field optional: an edit says what changed, not what everything is."""

    model_config = FINITE

    kind: ObjectKind | None = None
    x: Metres | None = None
    y: Metres | None = None
    shape: Shape | None = None
    width: float | None = Field(default=None, gt=0, le=500)
    depth: float | None = Field(default=None, gt=0, le=500)
    rotation: float | None = Field(default=None, ge=-360, le=360)
    points: list[Corner] | None = Field(default=None, max_length=MAX_CORNERS)
    #: Set to null when a vertex is dragged out of true: the geometry does not
    #: change, but the promise that the corners stay square ends.
    constraint_hint: str | None = None
    #: What shape the roof is. OSM's `height` is the ridge, so a building with
    #: no answer here is modelled as solid to it — which is what every building
    #: was before this existed.
    roof: RoofShape | None = None
    #: Where the roof starts, in metres. With the ridge it gives the pitch, and
    #: the pitch is what makes a north face darker than a south one — so it is
    #: worth being able to say, rather than living on the 75 %-of-the-ridge
    #: assumption that stands in when nobody has. `building:levels` fills it at
    #: import wherever OSM carries it.
    eaves_m: float | None = Field(default=None, ge=0, le=200)
    #: A bed may differ from its garden — bought soil, a watered corner.
    soil_type: str | None = None
    moisture: str | None = None
    height: float | None = Field(default=None, gt=0, le=200)
    label: str | None = Field(default=None, max_length=200)
    # Correcting a height makes it the user's word on it; otherwise every
    # sightline would go on marking it as an assumption.
    height_source: str | None = None


class GardenSoil(BaseModel):
    """What the ground is, asked once for the whole garden."""

    soil_type: str
    moisture: str


class ColourObservation(BaseModel):
    """A flower colour the gardener recorded. `null` takes it back."""

    colour: str | None = None


class BedUpdate(BaseModel):
    model_config = FINITE

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

    model_config = FINITE

    taxon_id: int | None = Field(default=None, gt=0)
    raw_name: str | None = Field(default=None, max_length=200)
    quantity: int = Field(default=1, ge=1, le=10000)

    @model_validator(mode="after")
    def one_or_the_other(self) -> PlantingCreate:
        if self.taxon_id is None and not (self.raw_name or "").strip():
            raise ValueError("either taxon_id or raw_name is required")
        return self


class PlantingPlacement(BaseModel):
    """Where a cluster was dragged to."""

    model_config = FINITE

    x: Metres
    y: Metres


class PlantingColours(BaseModel):
    """One cluster's colour and season.

    The per-bed palette answers "which colours are in this bed this month",
    which is everything a colour band needed and not enough for a dot per
    cluster: that has to know which cluster is which.
    """

    planting_id: int
    taxon_id: int | None
    #: Null where the catalogue records no flower colour, which is most of it.
    colour: str | None
    months: list[int]
    #: Ground one plant wants, in m², estimated from height. Null for most of
    #: the catalogue — the plan sizes a cluster from it and never prints it.
    space_m2: float | None
