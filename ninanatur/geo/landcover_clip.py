"""OpenStreetMap's areas in garden metres, cut to the plan (doc 114).

A forest arrives with its whole outline, kilometres of it, for the corner of it
that lies beside a garden. Everything outside a box around the plot is cut away
here, on the server, so the page is sent the part it can show and nothing else.

Cut with Sutherland–Hodgman against the box. The box is a rectangle in the
plan's own axes, and a convex clip region is exactly what the algorithm needs;
a general polygon library would be a dependency for four half-planes.
"""
from __future__ import annotations

from dataclasses import dataclass

from ninanatur.geo.osm_landcover import OsmArea
from ninanatur.geo.projection import LatLon, Metres, to_latlon, to_metres

Point = tuple[float, float]

#: How far past the plot the surroundings reach. The plan opens on 40 m and
#: zooms out to a kilometre, and the houses and streets around a garden reach
#: 50 m: this is enough to put them in their neighbourhood.
LANDCOVER_MARGIN_M = 150.0

#: Decimetres. A plan of a garden has no use for OpenStreetMap's centimetres,
#: and rounding is what lets repeated points fall together and be dropped.
DECIMALS = 1

#: A piece smaller than this is a sliver the cut left along the box's edge, or
#: a mapping error, and no colour anybody could see.
MIN_AREA_M2 = 2.0


@dataclass(frozen=True)
class Box:
    """A rectangle in garden metres, x east and y north."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float


@dataclass(frozen=True)
class LandArea:
    """One area as the plan draws it: its class and its rings in garden metres.

    Outer rings run anticlockwise and holes clockwise, so the page can fill
    with the nonzero rule: two lawns that overlap stay one lawn, where the
    even-odd rule would cut their overlap out as if it were a hole.
    """

    kind: str
    rings: list[list[Point]]


def box_around(points: list[Point], margin_m: float = LANDCOVER_MARGIN_M) -> Box:
    """The plot's extent in metres, and the margin around it."""
    if not points:
        raise ValueError("a box needs at least one point")
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return Box(min(xs) - margin_m, min(ys) - margin_m, max(xs) + margin_m, max(ys) + margin_m)


def degrees_of(box: Box, anchor: LatLon) -> tuple[float, float, float, float]:
    """(south, west, north, east) of the box, for the query."""
    south_west = to_latlon(Metres(box.min_x, box.min_y), anchor)
    north_east = to_latlon(Metres(box.max_x, box.max_y), anchor)
    return (south_west.lat, south_west.lon, north_east.lat, north_east.lon)


def in_garden(areas: list[OsmArea], anchor: LatLon, box: Box,
              shift: Point = (0.0, 0.0)) -> list[LandArea]:
    """Each area in garden metres, cut to the box; an area with nothing in it is left out.

    `shift` is subtracted from every point: how far the anchor these areas were
    placed from sits from the one the garden was drawn around (doc 114).
    """
    found: list[LandArea] = []
    for area in areas:
        outers = _rings(area.outers, anchor, box, shift, outer=True)
        if not outers:
            continue
        found.append(LandArea(kind=area.kind,
                              rings=outers + _rings(area.inners, anchor, box, shift, outer=False)))
    return found


def _rings(rings: list[list[LatLon]], anchor: LatLon, box: Box, shift: Point,
           *, outer: bool) -> list[list[Point]]:
    found = []
    for ring in rings:
        metres = [(m.x - shift[0], m.y - shift[1]) for m in (to_metres(p, anchor) for p in ring)]
        cut = _without_repeats([(round(x, DECIMALS), round(y, DECIMALS))
                                for x, y in clip_to_box(metres, box)])
        area = signed_area(cut)
        if len(cut) < 3 or abs(area) < MIN_AREA_M2:
            continue
        # Anticlockwise has a positive area with y north.
        found.append(cut if (area > 0) == outer else cut[::-1])
    return found


def clip_to_box(ring: list[Point], box: Box) -> list[Point]:
    """The part of a ring inside the box (Sutherland–Hodgman).

    A ring that leaves the box and comes back is joined along the box's edge; a
    concave one can leave a line of no width there, which covers nothing and is
    never seen.
    """
    for axis, bound, keep_above in ((0, box.min_x, True), (0, box.max_x, False),
                                    (1, box.min_y, True), (1, box.max_y, False)):
        ring = _clip_edge(ring, axis, bound, keep_above)
        if not ring:
            break
    return ring


def _clip_edge(ring: list[Point], axis: int, bound: float, keep_above: bool) -> list[Point]:
    def inside(p: Point) -> bool:
        return p[axis] >= bound if keep_above else p[axis] <= bound

    def crossing(a: Point, b: Point) -> Point:
        # Never a division by zero: one end is inside and the other is not, so
        # they differ along this axis.
        t = (bound - a[axis]) / (b[axis] - a[axis])
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))

    kept: list[Point] = []
    for index, current in enumerate(ring):
        previous = ring[index - 1]
        if inside(current):
            if not inside(previous):
                kept.append(crossing(previous, current))
            kept.append(current)
        elif inside(previous):
            kept.append(crossing(previous, current))
    return kept


def _without_repeats(ring: list[Point]) -> list[Point]:
    """Consecutive equal points once, the wrap from last to first included."""
    kept = [p for i, p in enumerate(ring) if i == 0 or p != ring[i - 1]]
    while len(kept) > 1 and kept[0] == kept[-1]:
        kept.pop()
    return kept


def signed_area(ring: list[Point]) -> float:
    """Positive when the ring runs anticlockwise (shoelace)."""
    following = ring[1:] + ring[:1]
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, following, strict=True)) / 2


__all__ = ["LANDCOVER_MARGIN_M", "Box", "LandArea", "box_around", "clip_to_box",
           "degrees_of", "in_garden", "signed_area"]
