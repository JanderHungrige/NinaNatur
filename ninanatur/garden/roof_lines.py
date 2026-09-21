"""The lines that draw a roof, kept inside the house they belong to (doc 98).

The roof model (`roofshape`) works over one rectangle per house: along the
surveyed ridge, or the smallest one round the footprint. On a rectangular house
that rectangle *is* the house. On any other — a trapezoid on a street corner,
an oblique end wall, an L, a notch cut out — its corners lie outside the walls,
and the hips drawn to them ran out across the garden, the ridge past the
shorter wall (the owner, 2026-09-21: "vor allem beim Walmdach … aber auch").

So the drawing keeps to the house: a hip runs to the house's own corner nearest
the rectangle's, a pent's upper edge is the wall it rises to, and every line is
cut to the outline. On a rectangle none of it changes anything. The roof's
light is still the model's, over its rectangle; this is the drawing of it.
"""
from __future__ import annotations

import math

from ninanatur.garden.roofs import Roof
from ninanatur.garden.roofshape import Line, box_for, surface_of

Point = tuple[float, float]

#: A piece of a line shorter than this, left over where a line grazes a corner,
#: is a speck and not drawn.
MIN_PIECE_M = 0.05

#: How close to an edge a point counts as on it. Footprints are in metres, and a
#: pent roof's line lies on its wall.
ON_EDGE_M = 1e-6


def roof_lines(
    footprint: list[Point],
    roof: Roof,
    height_m: float | None,
    eaves_m: float | None = None,
    fall_deg: float | None = None,
) -> list[Line]:
    """The lines that draw the roof the model knows, in garden metres.

    The ridge; a hip roof's hips besides, from each end of its ridge towards the
    two corners at that end; a pent roof's upper edge, on the walls it rises to
    (`uphill_walls`). Nothing for a roof it treats as a plane — flat, unidentified,
    unsurveyed, or too shallow to matter: the drawing says what the model
    knows, and no more. Nothing outside the outline, either.
    """
    surface = surface_of(footprint, roof, height_m, eaves_m, fall_deg)
    if surface is None or not surface.pitched:
        return []
    if roof is Roof.PENT and fall_deg is not None:
        return uphill_walls(footprint, fall_deg)
    start, end = surface.ridge
    lines: list[Line] = [] if math.dist(start, end) < 1e-9 else [surface.ridge]
    box = box_for(footprint, True, fall_deg)
    if roof is Roof.HIP and box is not None:
        (cx, cy), (ux, uy), long_half, short_half = box
        for tip, way in ((start, -1.0), (end, 1.0)):
            for side in (-1.0, 1.0):
                corner = (cx + way * ux * long_half - side * uy * short_half,
                          cy + way * uy * long_half + side * ux * short_half)
                lines.append((tip, _nearest_corner(footprint, corner)))
    return [piece for line in lines for piece in inside_parts(line, footprint)]


#: A wall faces uphill when its outward side is within 45° of straight uphill.
FACING_UPHILL = math.cos(math.radians(45.0))


def uphill_walls(footprint: list[Point], fall_deg: float) -> list[Line]:
    """A pent's upper edge, on the house: its walls that face uphill, in its
    upper half.

    The model's upper edge is its rectangle's, laid across the surveyed fall.
    A surveyed fall is a mean over roof faces and never exactly square to a wall,
    so that edge touches a real house at one corner only — cut to the outline,
    nothing was left of it, nor of the arrow drawn from it (review, 2026-09-21).
    The wall the roof rises to is the one to draw.
    """
    down = (math.sin(math.radians(fall_deg)), math.cos(math.radians(fall_deg)))
    ring = footprint if _twice_area(footprint) > 0 else footprint[::-1]
    heights = [-(x * down[0] + y * down[1]) for x, y in ring]
    middle = (max(heights) + min(heights)) / 2
    facing: list[tuple[float, Line]] = []
    for index, a in enumerate(ring):
        b = ring[(index + 1) % len(ring)]
        length = math.dist(a, b)
        if length < MIN_PIECE_M:
            continue
        # Anticlockwise, a wall's outward side is on its right.
        outward = ((b[1] - a[1]) / length, -(b[0] - a[0]) / length)
        uphill = -(outward[0] * down[0] + outward[1] * down[1])
        if (heights[index] + heights[(index + 1) % len(ring)]) / 2 > middle:
            facing.append((uphill, (a, b)))
    walls = [wall for uphill, wall in facing if uphill >= FACING_UPHILL]
    if walls or not facing:
        return walls
    return [max(facing)[1]]


def _twice_area(ring: list[Point]) -> float:
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))


def _nearest_corner(footprint: list[Point], point: Point) -> Point:
    """The footprint's own corner nearest to a corner of its rectangle."""
    return min(footprint, key=lambda corner: math.dist(corner, point))


def inside_parts(line: Line, polygon: list[Point]) -> list[Line]:
    """The pieces of a line that lie inside a polygon or on its edge.

    Cut wherever the line crosses an edge; a piece is kept when its middle is
    inside. An outline need not be convex: a ridge across an L's notch comes
    back as two pieces.
    """
    (x0, y0), (x1, y1) = line
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < MIN_PIECE_M:
        return []
    cuts = sorted({0.0, 1.0, *_crossings(line, polygon)})
    kept: list[tuple[float, float]] = []
    for a, b in zip(cuts, cuts[1:], strict=False):
        middle = (a + b) / 2
        if not _inside_or_on((x0 + dx * middle, y0 + dy * middle), polygon):
            continue
        if kept and kept[-1][1] == a:
            kept[-1] = (kept[-1][0], b)
        else:
            kept.append((a, b))
    return [((x0 + dx * a, y0 + dy * a), (x0 + dx * b, y0 + dy * b))
            for a, b in kept if (b - a) * length >= MIN_PIECE_M]


def _crossings(line: Line, polygon: list[Point]) -> list[float]:
    """Where along the line (0–1) it meets an edge. Edges parallel to it add
    nothing: the midpoint test decides a piece that runs along one."""
    (x0, y0), (x1, y1) = line
    dx, dy = x1 - x0, y1 - y0
    found: list[float] = []
    for index, (ax, ay) in enumerate(polygon):
        bx, by = polygon[(index + 1) % len(polygon)]
        ex, ey = bx - ax, by - ay
        denominator = dx * ey - dy * ex
        if abs(denominator) < 1e-12:
            continue
        t = ((ax - x0) * ey - (ay - y0) * ex) / denominator
        u = ((ax - x0) * dy - (ay - y0) * dx) / denominator
        if 0.0 < t < 1.0 and -1e-9 <= u <= 1.0 + 1e-9:
            found.append(t)
    return found


def _inside_or_on(point: Point, polygon: list[Point]) -> bool:
    """Inside by the even-odd rule, or on an edge."""
    x, y = point
    inside = False
    for index, (ax, ay) in enumerate(polygon):
        bx, by = polygon[(index + 1) % len(polygon)]
        if _distance_to_edge(point, (ax, ay), (bx, by)) <= ON_EDGE_M:
            return True
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            inside = not inside
    return inside


def _distance_to_edge(point: Point, a: Point, b: Point) -> float:
    ex, ey = b[0] - a[0], b[1] - a[1]
    length_sq = ex * ex + ey * ey
    t = 0.0 if length_sq < 1e-18 else ((point[0] - a[0]) * ex + (point[1] - a[1]) * ey) / length_sq
    t = max(0.0, min(1.0, t))
    return math.dist(point, (a[0] + t * ex, a[1] + t * ey))


__all__ = ["MIN_PIECE_M", "inside_parts", "roof_lines", "uphill_walls"]
