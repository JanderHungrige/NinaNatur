"""A line with a width, and the ground it covers.

A path, a wall, a fence and a hedge are all a centreline and a band width. That
is two numbers per corner instead of twenty for the equivalent outline — and it
is why a wall that turns a corner is one element here rather than two.

Everything downstream only ever sees the polygon this module produces, which is
what makes the whole representation affordable: `footprint_of` hands the band to
the same shading and sightline code that a house goes through.
"""
from __future__ import annotations

import math

Point = tuple[float, float]

#: Below this a segment has no direction to offset along. A clicked line can
#: easily carry the same point twice.
_MIN_SEGMENT_M = 1e-9


def _drop_repeats(points: list[Point]) -> list[Point]:
    kept: list[Point] = []
    for p in points:
        if not kept or math.hypot(p[0] - kept[-1][0], p[1] - kept[-1][1]) > _MIN_SEGMENT_M:
            kept.append(p)
    return kept


#: How far a mitre may run out from the corner, in half-widths. A mitre goes to
#: infinity as the angle closes, and a garden path can turn back on itself.
_MITRE_LIMIT = 4.0


def _normal(a: Point, b: Point, half: float) -> Point:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    return (-dy / length * half, dx / length * half)


def _intersect(p1: Point, d1: Point, p2: Point, d2: Point) -> Point | None:
    """Where two offset edges meet, or None when they are parallel."""
    cross = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(cross) < 1e-12:
        return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / cross
    return (p1[0] + d1[0] * t, p1[1] + d1[1] * t)


def _offset_side(points: list[Point], half: float) -> list[Point]:
    """One side of the band.

    At a corner the two offset edges are intersected, because offsetting each
    segment on its own leaves a wedge of unpaved ground on the outside of every
    bend — nobody lays a path like that. The mitre is limited: as the angle
    closes it runs away to infinity, so past the limit the corner is bevelled
    with both edge ends instead.
    """
    out: list[Point] = []
    last = len(points) - 2
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        na = _normal(a, b, half)
        out.append((a[0] + na[0], a[1] + na[1]))
        if i == last:
            out.append((b[0] + na[0], b[1] + na[1]))
            continue
        c = points[i + 2]
        nb = _normal(b, c, half)
        corner = _intersect(
            (a[0] + na[0], a[1] + na[1]), (b[0] - a[0], b[1] - a[1]),
            (b[0] + nb[0], b[1] + nb[1]), (c[0] - b[0], c[1] - b[1]),
        )
        if corner is not None and math.hypot(
            corner[0] - b[0], corner[1] - b[1]
        ) <= _MITRE_LIMIT * abs(half):
            out.append(corner)
        else:
            out.append((b[0] + na[0], b[1] + na[1]))
            out.append((b[0] + nb[0], b[1] + nb[1]))
    return out


def band_of(centreline: list[Point], *, width: float) -> list[Point]:
    """The polygon a line of this width covers.

    Returned counter-clockwise-ish: one side out, the other side back, which
    closes the ring without repeating an endpoint.
    """
    if width <= 0:
        raise ValueError(f"a band needs a positive width, got {width}")
    points = _drop_repeats([(float(x), float(y)) for x, y in centreline])
    if len(points) < 2:
        raise ValueError("a band needs at least two points")

    half = width / 2
    left = _offset_side(points, half)
    right = _offset_side(points, -half)
    # Round caps would be truer to a real path, but a square end is what a
    # gardener lays and it keeps the point count down.
    return left + list(reversed(right))
