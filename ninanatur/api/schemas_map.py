"""The map: addresses, a selection, the heights an import could and could not
find, the imagery a licence allows, and what can be seen from where.

Split from `schemas.py` in Wave 21, which re-exports every name here.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from ninanatur.api.schemas_garden_in import FINITE, MAX_CORNERS, MAX_OUTLINE_EDGE_M


class PlaceOut(BaseModel):
    name: str
    lat: float
    lon: float


class PlaceSearchOut(BaseModel):
    places: list[PlaceOut]


class LatLonIn(BaseModel):
    model_config = FINITE

    # Germany, roughly. The catalogue is German: a garden in Ohio would get
    # suggestions for plants that do not grow there.
    lat: float = Field(ge=47.0, le=55.2)
    lon: float = Field(ge=5.5, le=15.2)


class MapSelection(BaseModel):
    model_config = FINITE

    name: str = Field(min_length=1, max_length=120)
    outline: list[LatLonIn] = Field(min_length=3, max_length=MAX_CORNERS)
    # One question per garden, standing in for the 75-88% of German suburban
    # buildings that carry no height in OSM at all.
    neighbourhood: str = "detached"

    @model_validator(mode="after")
    def _a_plot_not_a_region(self) -> MapSelection:
        """Refused here, before the map import asks Overpass anything.

        A bound on each point is not enough: every corner of a triangle across
        Germany is individually a valid German coordinate.
        """
        import math

        lats = [p.lat for p in self.outline]
        lons = [p.lon for p in self.outline]
        north_south = (max(lats) - min(lats)) * 111_320
        east_west = (max(lons) - min(lons)) * 111_320 * math.cos(
            math.radians(sum(lats) / len(lats))
        )
        if max(north_south, east_west) > MAX_OUTLINE_EDGE_M:
            raise ValueError(
                f"Garten zu groß: der Umriss ist {max(north_south, east_west):.0f} m "
                f"lang, höchstens {MAX_OUTLINE_EDGE_M:.0f} m sind möglich"
            )
        return self


class HeightReport(BaseModel):
    """Where the heights around this garden came from.

    Reported because an assumed height presented as a measured one is the same
    lie as a filter that hides what it dropped.
    """

    measured: int
    estimated: int
    assumed: int


class ImageryOut(BaseModel):
    """The aerial imagery available at a place, if any.

    `attribution` is a condition of the licence, not a caption — DL-DE/BY-2.0
    and CC-BY-4.0 both require the named credit, so imagery shown without it is
    imagery used outside its terms.
    """

    available: bool
    state: str | None = None
    url: str | None = None
    layer: str | None = None
    licence: str | None = None
    attribution: str | None = None


class ViewpointIn(BaseModel):
    """Where somebody is standing, in garden metres."""

    x: float = Field(ge=-500, le=500)
    y: float = Field(ge=-500, le=500)
    # A person, not a drone. Anything outside this is a different question.
    eye_height_m: float = Field(default=1.6, ge=0.3, le=3.0)


class PlantingVisibility(BaseModel):
    planting_id: int
    name: str
    bed_id: int
    #: None when the catalogue has no height for the species — recorded for 44%
    #: of it, and assuming one would put a confident answer on top of nothing.
    height_m: float | None
    visible: bool | None
    visible_from_m: float | None
    hidden_by: int | None
    #: True when the answer rests on a height nobody measured.
    estimated: bool


class SightlinesOut(BaseModel):
    plantings: list[PlantingVisibility]
    #: How many answers rest on an assumed height, so the UI can say so once
    #: rather than per row.
    estimated_count: int
