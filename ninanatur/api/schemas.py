"""Response shapes — the contract Waves 3 and 4 consume unchanged.

Unknown is transported as `null`, never as an omitted field and never as zero.
A client must be able to tell "no data" from "zero", and most of this catalogue
is partly unknown.

The garden's own answers live here. The rest was split by concern in Wave 21:
`schemas_plants` (the catalogue), `schemas_garden_in` (what a caller sends),
`schemas_map` and `schemas_accounts`.
"""
from __future__ import annotations

from pydantic import BaseModel

from ninanatur.api.schemas_garden_in import PlantingColours
from ninanatur.api.schemas_map import HeightReport


class GardenCreated(BaseModel):
    """The token is returned; the numeric id deliberately is not."""

    share_token: str
    name: str


class PlantingOut(BaseModel):
    planting_id: int
    # None when the catalogue could not name it — `raw_name` is then the plant.
    taxon_id: int | None
    canonical_name: str | None
    raw_name: str | None
    quantity: int
    added_at: str
    #: Where this cluster sits, in metres from the bed's origin. Null until
    #: somebody moves it; the plan derives a position from the id until then.
    x: float | None
    y: float | None


class BedOut(BaseModel):
    bed_id: int
    name: str
    polygon: list[list[float]]
    # The geometry, same as an obstacle carries it. `polygon` is the outline in
    # absolute metres and cannot be edited — handles are built from an origin
    # and the points around it, so a bed without these silently stopped being
    # reshapeable the moment somebody labelled a shape "Blumenbeet".
    kind: str
    shape: str
    x: float
    y: float
    points: list[list[float]] | None
    #: A circle's diameter or a band's width. A circle has no points at all, so
    #: without this a round bed has nothing to size its handles from.
    width: float | None
    constraint_hint: str | None
    soil_type: str | None
    moisture: str | None
    ellenberg_l: float | None
    ellenberg_m: float | None
    ellenberg_n: float | None
    ellenberg_r: float | None
    sun_hours: float | None
    #: Named, never scored. See `slopes.py` for why: at this latitude a slope
    #: barely moves the hours and moves the energy a great deal.
    slope_deg: float | None
    aspect_deg: float | None
    light_computed_at: str | None
    # Required, not defaulted: the response always carries both, and a default
    # here makes them optional in the generated client for no reason.
    height_above_ground: float
    label: str | None
    plantings: list[PlantingOut]


class ObstacleOut(BaseModel):
    obstacle_id: int
    kind: str
    #: 'flat' | 'gable' | 'hip' | 'pent' | 'unknown'. OSM's height is the ridge,
    #: so this says how much of the top is solid.
    roof: str
    #: Where the roof starts. Null is "nobody has said", and the model then puts
    #: the eaves three quarters of the way up. Sent so the edit form can show
    #: what is actually stored rather than an empty box over a real value.
    eaves_m: float | None
    label: str | None
    # Where the height came from. Shown, because a sightline resting on a
    # guessed building height must not look surveyed.
    height_source: str
    x: float
    y: float
    #: 'polygon' | 'circle' | 'line'.
    shape: str
    #: A circle's diameter or a line's band width; absent for a polygon.
    width: float | None
    #: The outline for a polygon, the centreline for a line.
    points: list[list[float]] | None
    #: 'rect' when the corners are meant to stay square. Wave 11 stores points
    #: rather than a width and an angle, so this is a promise about how the
    #: handles behave rather than a second geometry.
    constraint_hint: str | None
    #: None on a surface: Wave 8's rule that an unrecorded height is not a zero.
    height: float | None
    #: The polygon this covers, so the drawing does not re-derive it. One
    #: answer to "what ground does this cover", not three.
    footprint: list[list[float]]


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
    plantings: list[PlantingColours]


class BloomPalette(BaseModel):
    beds: list[BedPalette]


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
    #: What the ground is, asked once. Null until somebody has been asked —
    #: which is what the interface uses to know it still has to.
    soil_type: str | None
    moisture: str | None
    #: Flower colours this garden recorded itself, by taxon id. Only what was
    #: noted, so it stays small — and it is what lets the interface say which
    #: colour is the gardener's own rather than the catalogue's.
    observed_colours: dict[int, str]
    beds: list[BedOut]
    obstacles: list[ObstacleOut]


class MapGardenOut(BaseModel):
    """A garden created from the map, and what the map could and could not say."""

    garden: GardenOut
    heights: HeightReport
