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

from ninanatur.garden.roofs import eaves_from_levels
from ninanatur.geo.projection import LatLon, Metres, to_metres

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
    #: What OSM says the roof is, mapped onto the shapes this model knows.
    #: 'unknown' where it says nothing, which is most buildings.
    roof: str = "unknown"
    #: Eaves height from `building:levels`, where that exists. The one measured
    #: input in the roof model.
    eaves_m: float | None = None
    #: The footprint OSM drew, as offsets from this building's own x and y.
    #: Empty when Overpass answered without geometry. Relative rather than
    #: absolute because `footprint_of` adds the element's position to every
    #: point — absolute points would place the building twice as far out.
    outline: list[tuple[float, float]] = field(default_factory=list)


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


#: OSM's `roof:shape` vocabulary is long; these are the shapes this model has a
#: ratio for. Anything else stays unknown rather than being forced into the
#: nearest one — a wrong shape is a wrong height, silently.
OSM_ROOFS: dict[str, str] = {
    "flat": "flat",
    "gabled": "gable",
    "hipped": "hip",
    "half-hipped": "hip",
    "skillion": "pent",
    "pitched": "gable",
}


def _roof_of(tags: dict[str, str]) -> str:
    return OSM_ROOFS.get((tags.get("roof:shape") or "").strip().lower(), "unknown")


def _levels(tags: dict[str, str]) -> float | None:
    """`building:levels`, as a number or not at all.

    OSM permits "2;3" and "2.5" and worse. Anything that is not a plain number
    is refused rather than guessed at — the same rule `_osm_height` follows, and
    for the same reason.
    """
    raw = (tags.get("building:levels") or "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _polygon_area(points: list[Metres]) -> float:
    """Shoelace, in square metres."""
    total = 0.0
    for index, a in enumerate(points):
        b = points[(index + 1) % len(points)]
        total += a.x * b.y - b.x * a.y
    return abs(total) / 2


def _radius_of(building: OsmBuilding, anchor: LatLon) -> float:
    """The circle that stands in for the footprint.

    Obstacles are cylinders in the shading model, so a footprint still has to
    become one number. The circle of **equal area**, not half the bounding box's
    diagonal: for a 30 x 8 m barn the diagonal gives 15.5 m, a circle of 755 m²
    standing in for 240. On live data that made every drawn building 2.1 to 2.8
    times its real size, which is what set them overlapping.
    """
    if len(building.outline) < 3:
        return 5.0
    area = _polygon_area([to_metres(p, anchor) for p in building.outline])
    return max(2.0, math.sqrt(area / math.pi)) if area > 0 else 5.0


def _distance_to_plot(here: Metres, plot: list[Metres]) -> float:
    """From a point to the nearest part of the garden, in metres.

    The garden is a plot, not a pin. Measuring to its centroid is the same thing
    only while the plot is small: on a 60 m one the centroid is 30 m from the
    hedge, which is the difference between a neighbour's shadow arriving and
    being thrown away before anybody sees it.
    """
    if not plot:
        return math.hypot(here.x, here.y)
    best = math.inf
    for index, corner in enumerate(plot):
        nxt = plot[(index + 1) % len(plot)]
        best = min(best, _to_segment(here, corner, nxt))
    return best


def _to_segment(point: Metres, a: Metres, b: Metres) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    length = dx * dx + dy * dy
    if length == 0:
        return math.hypot(point.x - a.x, point.y - a.y)
    t = max(0.0, min(1.0, ((point.x - a.x) * dx + (point.y - a.y) * dy) / length))
    return math.hypot(point.x - (a.x + t * dx), point.y - (a.y + t * dy))


def surroundings_from(
    anchor: LatLon,
    buildings: list[OsmBuilding],
    neighbourhood: NeighbourhoodKind = NeighbourhoodKind.DETACHED,
    outline: list[LatLon] | None = None,
) -> Surroundings:
    """Turn OSM buildings into shading objects around a garden.

    `outline` is the plot. Without it the anchor stands in for the whole garden,
    which is right for a point and was wrong for everything else: a farmyard
    with five buildings arrived in the plan as one, because the other four had
    centres more than 50 m from the middle of a plot whose own hedge they nearly
    touched.
    """
    plot = [to_metres(p, anchor) for p in (outline or [])]
    kept: list[Surrounding] = []
    counts = {HeightSource.OSM_HEIGHT: 0, HeightSource.OSM_LEVELS: 0,
              HeightSource.NEIGHBOURHOOD: 0}

    for building in buildings:
        here = to_metres(building.centre, anchor)
        height, source = _height_of(building.tags, neighbourhood)
        radius = _radius_of(building, anchor)
        # To the nearest part of the building from the nearest part of the
        # garden. Both halves matter: a long barn is measured by its wall, and a
        # deep plot by the corner the shadow actually falls on.
        distance = max(0.0, _distance_to_plot(here, plot) - radius)
        # The margin, now measured from the boundary. The box this replaces was
        # drawn around the centroid, so a large plot lost its own neighbours.
        if distance > MARGIN_M:
            continue
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
                roof=_roof_of(building.tags),
                eaves_m=eaves_from_levels(_levels(building.tags)),
                label=building.tags.get("name"),
                outline=[
                    (round(p.x - here.x, 2), round(p.y - here.y, 2))
                    for p in (to_metres(c, anchor) for c in building.outline)
                ],
            )
        )

    return Surroundings(
        objects=kept,
        measured=counts[HeightSource.OSM_HEIGHT],
        estimated=counts[HeightSource.OSM_LEVELS],
        assumed=counts[HeightSource.NEIGHBOURHOOD],
    )
