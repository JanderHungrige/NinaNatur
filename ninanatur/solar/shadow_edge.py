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
    #: For a far edge the way runs along: the height it amounts to, positive
    #: where the model's thing stands as though taller. None otherwise. Here
    #: δ·tan h, a block's; `garden.shadow_marks` asks what a metre of the thing
    #: actually moves this edge, which for eaves may be nothing (doc 122).
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
    tied, nearest, offset = _nearest(edges, x, y)
    away = math.radians(sun.azimuth)
    # The direction the shadow falls: away from the sun.
    fall_x, fall_y = -math.sin(away), -math.cos(away)
    dx, dy = nearest[0] - x, nearest[1] - y
    along = dx * fall_x + dy * fall_y
    across = fall_x * dy - fall_y * dx
    lengthwise = abs(along) >= abs(across)
    # At a corner two edges are equally near; the way the miss runs says which
    # it is about — ring order said it for a miss mostly along the sun
    # (review of stage 3, 2026-09-28).
    facings = [_facing(a, b, fall_x, fall_y) for a, b in tied]
    wanted = [f for f in facings if (f != "side") == lengthwise]
    facing = (wanted or facings)[0]
    return Reading(
        altitude=sun.altitude, azimuth=sun.azimuth, rings=rings, nearest=nearest,
        offset_m=offset, edge=facing, model_longer=_inside(rings, x, y),
        along_m=along, across_m=across,
        height_m=along * math.tan(math.radians(sun.altitude))
        if facing == "far" and lengthwise else None,
        turned_deg=None if lengthwise else _turned(_centre(outline), (x, y), nearest, offset),
    )


def reach_past(obstacle: Obstacle, sun: SunPosition, point: tuple[float, float], *,
               back: bool = False) -> float:
    """How far past `point`, straight away from the sun, the obstacle's shadow
    ends: the nearest edge facing away from the sun that the way crosses. 0
    where the shadow ends at the point, or before it. `back`: the same, the
    other way — how far towards the sun from `point` the shadow ends.

    What a change to the thing moves one point of an edge by: the way from a
    point on the old edge to the new one, measured along the shadow — which a
    fresh nearest point is not, once the new shadow covers the mark it was
    measured from. Taller, the new edge lies ahead; lower, behind."""
    away = math.radians(sun.azimuth)
    fall_x, fall_y = -math.sin(away), -math.cos(away)
    way = (-fall_x, -fall_y) if back else (fall_x, fall_y)
    rings = [ring for ring in shadow_rings([obstacle], sun) if len(ring) >= 3]
    found = [t for a, b in _edges(rings)
             if _outward(a, b, fall_x, fall_y) > 0
             and (t := _crossing(point, way, a, b)) is not None]
    return max(0.0, min(found, default=0.0))


def _crossing(p: tuple[float, float], d: tuple[float, float], a: tuple[float, float],
              b: tuple[float, float]) -> float | None:
    """Where the way from p along d crosses the segment a–b, as a distance
    along d — or None where it does not, or runs along it. A crossing a hair
    behind p counts: p lies on an edge the change left where it was."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    denominator = d[0] * ey - d[1] * ex
    if abs(denominator) < 1e-12:
        return None
    wx, wy = a[0] - p[0], a[1] - p[1]
    t = (wx * ey - wy * ex) / denominator
    u = (wx * d[1] - wy * d[0]) / denominator
    return t if t >= -TIE_M and -TIE_M <= u <= 1 + TIE_M else None


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


#: How close two edges' nearest points must be to be the same point: a corner.
TIE_M = 1e-6


def _nearest(edges: list[Segment], x: float, y: float,
             ) -> tuple[list[Segment], tuple[float, float], float]:
    """The edges nearest (x, y) — two where the nearest point is a corner —
    the nearest point, and the distance."""
    found: list[tuple[float, Segment, tuple[float, float]]] = []
    for a, b in edges:
        ex, ey = b[0] - a[0], b[1] - a[1]
        span = ex * ex + ey * ey
        t = 0.0 if span == 0 else min(max(((x - a[0]) * ex + (y - a[1]) * ey) / span, 0.0), 1.0)
        px, py = a[0] + t * ex, a[1] + t * ey
        found.append((math.hypot(px - x, py - y), (a, b), (px, py)))
    distance, _edge, point = min(found, key=lambda f: f[0])
    tied = [edge for d, edge, _p in found if d - distance <= TIE_M]
    return tied, point, distance


def _facing(a: tuple[float, float], b: tuple[float, float], fall_x: float,
            fall_y: float) -> Edge:
    """Which way an edge faces. Outlines run anticlockwise and holes clockwise,
    so the shadow lies on the left of every edge and its outward normal is on
    the right."""
    out = _outward(a, b, fall_x, fall_y)
    return "far" if out > 0.5 else "near" if out < -0.5 else "side"


def _outward(a: tuple[float, float], b: tuple[float, float], fall_x: float,
             fall_y: float) -> float:
    """How far an edge's outward normal points along the fall, -1 to 1."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    length = math.hypot(ex, ey)
    return 0.0 if length == 0 else (ey * fall_x - ex * fall_y) / length


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


__all__ = ["Edge", "Reading", "reach_past", "read_edge"]
