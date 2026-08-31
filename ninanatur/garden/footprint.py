"""The ground an object covers, as one polygon.

One function, deliberately. The data-flow analysis before this wave found
occlusion already computed twice — once in `solar/shading.py` and once in
`garden/sightlines.py` — agreeing only because both sides assumed a cylinder.
Three answers to "what ground does this cover" is how they drift.

Objects store *what shape they are* rather than a bag of points, because that is
what a resize handle edits: a rectangle is two numbers and an angle. Four stored
corners would have to be re-derived on every drag, and two of them would
eventually disagree with the other two.
"""
from __future__ import annotations

import math
from enum import StrEnum

from ninanatur.garden.polyline import band_of

Point = tuple[float, float]

#: Segments in a circle's polygon. Enough that its shadow does not look like a
#: stop sign, few enough that the light sampler is not walking 64 edges.
CIRCLE_SEGMENTS = 16


class Shape(StrEnum):
    CIRCLE = "circle"
    RECT = "rect"
    POLYGON = "polygon"
    #: A centreline and a band width: paths, walls, fences, hedges. Two numbers
    #: per corner where the equivalent outline would need twenty — and a wall
    #: that turns a corner is one element rather than two.
    LINE = "line"


def _rotate(px: float, py: float, degrees: float) -> Point:
    """Clockwise from north — the compass convention on the plan, and the one
    the solar azimuth already uses. A second angular convention in the same
    drawing is a bug waiting for its first rotated house."""
    a = math.radians(degrees)
    cos, sin = math.cos(a), math.sin(a)
    return (px * cos + py * sin, -px * sin + py * cos)


def footprint_of(
    *,
    shape: Shape,
    x: float,
    y: float,
    width: float | None,
    depth: float | None,
    rotation: float,
    points: list[list[float]] | None,
) -> list[Point]:
    """The polygon this object covers, in garden metres."""
    if shape is Shape.LINE:
        if points is None or len(points) < 2:
            raise ValueError("a line footprint needs a centreline of two points or more")
        if width is None or width <= 0:
            raise ValueError(f"a line footprint needs a positive width, got {width}")
        return band_of(
            [(x + float(p[0]), y + float(p[1])) for p in points], width=width
        )

    if shape is Shape.POLYGON:
        if points is None or len(points) < 3:
            raise ValueError("a polygon footprint needs at least three points")
        return [(x + float(p[0]), y + float(p[1])) for p in points]

    if shape is Shape.CIRCLE:
        radius = (width or 0.0) / 2
        # Rotation is meaningless for a circle and is ignored rather than
        # applied to no effect.
        return [
            (
                x + radius * math.sin(2 * math.pi * i / CIRCLE_SEGMENTS),
                y + radius * math.cos(2 * math.pi * i / CIRCLE_SEGMENTS),
            )
            for i in range(CIRCLE_SEGMENTS)
        ]

    half_w = (width or 0.0) / 2
    half_d = (depth or width or 0.0) / 2
    corners = ((-half_w, -half_d), (half_w, -half_d), (half_w, half_d), (-half_w, half_d))
    return [
        (x + rx, y + ry) for rx, ry in (_rotate(cx, cy, rotation) for cx, cy in corners)
    ]


def covers(polygon: list[Point], point: Point) -> bool:
    """Whether the point lies inside the polygon, edges included.

    Edges count as inside: a bed exactly against a wall is touching it, not
    floating beside it, and a strict test would make that depend on floating
    point noise.
    """
    px, py = point
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    for i in range(n):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % n]
        if _on_segment(ax, ay, bx, by, px, py):
            return True
        if (ay > py) != (by > py):
            crossing = ax + (py - ay) * (bx - ax) / (by - ay)
            if crossing > px:
                inside = not inside
    return inside


def _on_segment(ax: float, ay: float, bx: float, by: float, px: float, py: float) -> bool:
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    if abs(cross) > 1e-9:
        return False
    return (
        min(ax, bx) - 1e-9 <= px <= max(ax, bx) + 1e-9
        and min(ay, by) - 1e-9 <= py <= max(ay, by) + 1e-9
    )


def bounding_radius(polygon: list[Point], centre: Point = (0.0, 0.0)) -> float:
    """The radius that contains the whole shape.

    A cheap first test before the expensive one: an object whose bounding circle
    cannot reach a point does not need its edges walked.
    """
    return max((math.hypot(px - centre[0], py - centre[1]) for px, py in polygon), default=0.0)
