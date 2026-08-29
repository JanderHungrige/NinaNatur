"""What the map can tell a garden about the things that shade it.

Wave 8's re-planning measured what OSM actually holds around a garden, and the
answer shapes this whole module: across 4,912 buildings in three German suburbs,
**zero** carried a `height` tag and 75-88% carried nothing at all. Central
Berlin, where the first draft was sampled, has 66% `building:levels`; a garden
suburb has 12-25%.

So an assumed height is the normal case here, not the fallback — and every one
of them says so.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import StrEnum

from ninanatur.geo.projection import LatLon, bounding_box, to_metres

# How far past the garden the map is read. A 12 m house casts 45 m of shadow at
# a 15 degree sun, so a 25 m margin loses the morning and evening shade of
# ordinary houses — which is most of what a garden feels.
MARGIN_M = 50.0

# The sun altitude the reach filter is generous to. Below this the shadows are
# long enough to come from another postcode and the light model already treats
# the hour as barely usable.
REACH_ALTITUDE_DEG = 15.0

# German residential storey height, floor to floor. A rounded number standing in
# for a range; it decides only the `building:levels` rung of the ladder.
STOREY_M = 3.0


class HeightSource(StrEnum):
    """Where a height came from. Shown, never hidden — a model that presented an
    assumed height as a measured one would be the same lie as a filter that hides
    what it dropped."""

    USER = "user"
    OSM_HEIGHT = "osm_height"
    OSM_LEVELS = "osm_levels"
    NEIGHBOURHOOD = "neighbourhood"


class NeighbourhoodKind(StrEnum):
    """The one question a garden is asked about its surroundings.

    One question per garden rather than one per building: the measured example
    has 13 buildings with no recorded height, and thirteen confirmations before
    the first plant suggestion is a wall at the moment somebody arrives.
    """

    DETACHED = "detached"
    TERRACE = "terrace"
    APARTMENT = "apartment"

    @property
    def height_m(self) -> float:
        return {"detached": 7.0, "terrace": 9.0, "apartment": 14.0}[self.value]


@dataclass(frozen=True)
class OsmBuilding:
    osm_id: int
    centre: LatLon
    outline: list[LatLon]
    tags: dict[str, str]


@dataclass(frozen=True)
class Surrounding:
    """A building placed in garden metres, with a height and its provenance."""

    osm_id: int
    x: float
    y: float
    radius_m: float
    height_m: float
    height_source: HeightSource
    label: str | None = None


@dataclass(frozen=True)
class Surroundings:
    objects: list[Surrounding] = field(default_factory=list)
    measured: int = 0
    estimated: int = 0
    assumed: int = 0


def reaches(height_m: float, distance_m: float) -> bool:
    """Whether an object that tall could cast a shadow that far.

    The filter that lets the margin be generous without flooding the user: a
    12 m house counts at 45 m, a 2 m fence only at 7.
    """
    return height_m >= distance_m * math.tan(math.radians(REACH_ALTITUDE_DEG))


def _osm_height(tags: dict[str, str]) -> float | None:
    """A plain number of metres, or nothing.

    OSM permits units, and `30'` read as 30 metres is a ten-storey shadow over
    somebody's vegetable patch. Anything that is not a bare number is refused
    rather than guessed at.
    """
    raw = tags.get("height", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", raw):
        return None
    value = float(raw)
    return value if 0 < value <= 200 else None


def _osm_levels(tags: dict[str, str]) -> float | None:
    raw = tags.get("building:levels", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", raw):
        return None
    levels = float(raw)
    return levels * STOREY_M if 0 < levels <= 60 else None


def _height_of(
    tags: dict[str, str], neighbourhood: NeighbourhoodKind
) -> tuple[float, HeightSource]:
    measured = _osm_height(tags)
    if measured is not None:
        return measured, HeightSource.OSM_HEIGHT
    from_levels = _osm_levels(tags)
    if from_levels is not None:
        return from_levels, HeightSource.OSM_LEVELS
    return neighbourhood.height_m, HeightSource.NEIGHBOURHOOD


def _radius_of(building: OsmBuilding, anchor: LatLon) -> float:
    """The circle that stands in for the footprint.

    Obstacles are cylinders in the shading model, so a footprint has to become a
    radius. Half the outline's diagonal, or a default when the outline was not
    fetched — it overstates a long building's shade at the ends, which is
    recorded as a known issue rather than pretended away.
    """
    if len(building.outline) < 3:
        return 5.0
    points = [to_metres(p, anchor) for p in building.outline]
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return max(2.0, math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2)


def surroundings_from(
    anchor: LatLon,
    buildings: list[OsmBuilding],
    neighbourhood: NeighbourhoodKind = NeighbourhoodKind.DETACHED,
) -> Surroundings:
    """Turn OSM buildings into shading objects around a garden."""
    south, west, north, east = bounding_box(anchor, MARGIN_M)
    kept: list[Surrounding] = []
    counts = {HeightSource.OSM_HEIGHT: 0, HeightSource.OSM_LEVELS: 0,
              HeightSource.NEIGHBOURHOOD: 0}

    for building in buildings:
        if not (south <= building.centre.lat <= north and west <= building.centre.lon <= east):
            continue
        here = to_metres(building.centre, anchor)
        height, source = _height_of(building.tags, neighbourhood)
        radius = _radius_of(building, anchor)
        # Distance to the nearest part of the building, not to its centre: a
        # large building's edge is what stands next to the garden.
        distance = max(0.0, math.hypot(here.x, here.y) - radius)
        if not reaches(height, distance):
            continue
        counts[source] += 1
        kept.append(
            Surrounding(
                osm_id=building.osm_id,
                x=round(here.x, 2),
                y=round(here.y, 2),
                radius_m=round(radius, 2),
                height_m=height,
                height_source=source,
                label=building.tags.get("name"),
            )
        )

    return Surroundings(
        objects=kept,
        measured=counts[HeightSource.OSM_HEIGHT],
        estimated=counts[HeightSource.OSM_LEVELS],
        assumed=counts[HeightSource.NEIGHBOURHOOD],
    )
