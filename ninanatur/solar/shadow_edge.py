"""How far the model's shadow edge lies from where the gardener saw it — doc 122.

The gardener marks a point where the shadow of one standing thing ended, at
one moment. The model's shadow of that thing at that moment is the drawing
the plan already makes (`shading.shadow_rings`, doc 116's rule that the shadow
drawn is the shadow counted), and the reading is the way from the mark to the
nearest point of its edge: how far, whether the model's shadow reaches past
the mark or stops short of it, and how much of the way runs along the sun and
how much across it.

Only an edge on the ground is one a gardener can see end: the drawn shadow
holds the thing's own outline too, and its sunlit walls are not marked (a
mark in a lit courtyard read the courtyard's wall until the review of
2026-09-28). And only an edge a top casts — one facing away from the sun —
says anything about a height; a crown's shadow also has a near end, cast by
where the crown starts, and a side.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from ninanatur.solar.position import SunPosition
from ninanatur.solar.shading import Obstacle, shadow_rings

Ring = list[tuple[float, float]]
#: Which way the nearest edge faces: away from the sun (a top cast it), towards
#: it (where a shadow begins — a crown's base), or along it (its side).
Edge = Literal["far", "near", "side"]
#: How close to the thing's own outline a drawn edge lies and is that outline.
ON_OUTLINE_M = 0.005


@dataclass(frozen=True)
class Reading:
    """The model's shadow edge against one mark."""

    #: The sun at the mark's moment, as the model places it.
    altitude: float
    azimuth: float
    #: Where the model's shadow of the thing lay at the mark's moment: rings,
    #: outlines anticlockwise and holes clockwise, as the plan draws them.
    rings: list[Ring]
    #: The nearest point of that shadow's edge on the ground, and how far it is.
    nearest: tuple[float, float]
    offset_m: float
    #: Which way that edge faces.
    edge: Edge
    #: Whether the mark lies inside the model's shadow: the model's shadow
    #: reaches past where the gardener saw it end.
    model_longer: bool
    #: The way from the mark to the nearest edge point, along the direction
    #: the shadow falls (positive: the model's edge lies further from the sun)
    #: and across it (positive: to its left, looking along the shadow).
    along_m: float
    across_m: float
    #: For a far edge the way runs along: the height it amounts to — δ·tan h,
    #: positive where the model's thing stands as though taller. None otherwise.
    height_m: float | None
    #: For a miss across the sun that is a turn about the thing: the angle,
    #: positive anticlockwise. None otherwise — a miss beside the thing that
    #: points straight away from it is no turn.
    turned_deg: float | None


def read_edge(obstacle: Obstacle, sun: SunPosition, x: float, y: float) -> Reading | None:
    """The model's shadow edge against a mark at (x, y), or None where the
    thing casts no shadow at this moment."""
    rings = [ring for ring in shadow_rings([obstacle], sun) if len(ring) >= 3]
    if not rings:
        return None
    outline = list(obstacle.footprint)
    edges = [edge for edge in _edges(rings) if not _on(outline, edge)] or _edges(rings)
    (a, b), nearest, offset = _nearest(edges, x, y)
    away = math.radians(sun.azimuth)
    # The direction the shadow falls: away from the sun.
    fall_x, fall_y = -math.sin(away), -math.cos(away)
    dx, dy = nearest[0] - x, nearest[1] - y
    along = dx * fall_x + dy * fall_y
    across = fall_x * dy - fall_y * dx
    facing = _facing(a, b, fall_x, fall_y)
    lengthwise = abs(along) >= abs(across)
    return Reading(
        altitude=sun.altitude, azimuth=sun.azimuth, rings=rings, nearest=nearest,
        offset_m=offset, edge=facing, model_longer=_inside(rings, x, y),
        along_m=along, across_m=across,
        height_m=along * math.tan(math.radians(sun.altitude))
        if facing == "far" and lengthwise else None,
        turned_deg=None if lengthwise else _turned(_centre(outline), (x, y), nearest, offset),
    )


Segment = tuple[tuple[float, float], tuple[float, float]]


def _edges(rings: list[Ring]) -> list[Segment]:
    return [(a, b) for ring in rings for a, b in zip(ring, ring[1:] + ring[:1], strict=True)]


def _distance(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    ex, ey = b[0] - a[0], b[1] - a[1]
    span = ex * ex + ey * ey
    t = 0.0 if span == 0 else min(max(((p[0] - a[0]) * ex + (p[1] - a[1]) * ey) / span, 0.0), 1.0)
    return math.hypot(a[0] + t * ex - p[0], a[1] + t * ey - p[1])


def _on(outline: Ring, edge: Segment) -> bool:
    """Whether a drawn edge is the thing's own outline: its ends and its middle
    all on it. A shadow edge that only touches the outline is not."""
    a, b = edge
    middle = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    walls = list(zip(outline, outline[1:] + outline[:1], strict=True))
    return all(min(_distance(p, u, v) for u, v in walls) < ON_OUTLINE_M for p in (a, middle, b))


def _nearest(edges: list[Segment], x: float, y: float,
             ) -> tuple[Segment, tuple[float, float], float]:
    """The edge nearest (x, y), its nearest point, and the distance."""
    best: tuple[Segment, tuple[float, float], float] = (edges[0], edges[0][0], math.inf)
    for a, b in edges:
        ex, ey = b[0] - a[0], b[1] - a[1]
        span = ex * ex + ey * ey
        t = 0.0 if span == 0 else min(max(((x - a[0]) * ex + (y - a[1]) * ey) / span, 0.0), 1.0)
        px, py = a[0] + t * ex, a[1] + t * ey
        d = math.hypot(px - x, py - y)
        if d < best[2]:
            best = ((a, b), (px, py), d)
    return best


def _facing(a: tuple[float, float], b: tuple[float, float], fall_x: float,
            fall_y: float) -> Edge:
    """Which way an edge faces. Outlines run anticlockwise and holes clockwise,
    so the shadow lies on the left of every edge and its outward normal is on
    the right."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    length = math.hypot(ex, ey)
    if length == 0:
        return "side"
    out = (ey * fall_x - ex * fall_y) / length
    return "far" if out > 0.5 else "near" if out < -0.5 else "side"


def _inside(rings: list[Ring], x: float, y: float) -> bool:
    """Under the non-zero rule the rings are drawn with (doc 116)."""
    winding = 0
    for a, b in _edges(rings):
        (ax, ay), (bx, by) = a, b
        side = (bx - ax) * (y - ay) - (x - ax) * (by - ay)
        if ay <= y < by and side > 0:
            winding += 1
        elif by <= y < ay and side < 0:
            winding -= 1
    return winding != 0


def _centre(outline: Ring) -> tuple[float, float]:
    return (sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline))


def _turned(centre: tuple[float, float], mark: tuple[float, float],
            nearest: tuple[float, float], offset: float) -> float | None:
    """The angle from the mark to the nearest edge point, seen from the thing
    — or None where the miss is not a turn: one that runs mostly away from the
    thing rather than round it turns it through far less than its length."""
    ax, ay = mark[0] - centre[0], mark[1] - centre[1]
    bx, by = nearest[0] - centre[0], nearest[1] - centre[1]
    reach = math.hypot(ax, ay)
    if reach == 0:
        return None
    angle = math.atan2(ax * by - ay * bx, ax * bx + ay * by)
    return math.degrees(angle) if abs(angle) >= 0.5 * offset / reach else None


__all__ = ["Edge", "Reading", "read_edge"]
