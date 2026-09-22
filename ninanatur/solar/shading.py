"""Does an obstacle put a point in shadow?

Obstacles are vertical cylinders — a position, a radius and a height. That covers
the walls, hedges, trees and sheds a garden actually contains, and keeps the
question to a line-distance check.

Garden coordinates are metres with x east and y north, matching `position.py`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ninanatur.garden.footprint import covers
from ninanatur.solar.position import SunPosition
from ninanatur.solar.reach import is_convex, near_edge
from ninanatur.solar.sweep import convex_hull, shadow_shape

# Below this the sun is weak and in practice blocked by whatever surrounds the
# garden. It also bounds the shadow: 1/tan(altitude) grows without limit as the
# sun approaches the horizon, and a 4 m wall would otherwise shade half a village.
MIN_ALTITUDE = 5.0


@dataclass(frozen=True)
class Point:
    """A location in the garden, metres, x east and y north."""

    x: float
    y: float


@dataclass(frozen=True)
class Obstacle:
    """Anything that casts a shadow: a footprint on the ground and a height.

    A footprint rather than a radius since Wave 10. A house rarely casts a round
    shadow, and the circle was not a simplification of the geometry so much as a
    claim about it.
    """

    footprint: list[tuple[float, float]]
    height: float
    #: The ground this thing stands on, in the same datum as the terrain. Zero
    #: means the old flat world, and every shadow in this project was computed
    #: on a plane at zero until Wave 17. A house whose base is three metres
    #: above the garden casts as though it were three metres taller.
    base: float = 0.0
    #: What fraction of the sun passes through. Zero for anything built — a wall
    #: is a wall. A crown is not: a broadleaf in leaf passes about a fifth, a
    #: spruce almost nothing, and bare winter branches most of it.
    #:
    #: In leaf, for a crown that has a season. `bare` is what it passes outside
    #: one — None for anything that does not change, which is every built thing
    #: and every conifer.
    transmission: float = 0.0
    bare_transmission: float | None = None
    #: Which drawn element this is, where the caller needs to tell one shadow
    #: from another. Only the roof query does: a building's own footprint is
    #: inside its own shadow at every moment of every day, so asking about a
    #: point *on* that building has to leave it out or the answer is darkness.
    owner: int | None = None

    def transmission_in(self, month: int) -> float:
        """What passes through in this month.

        The one thing about a tree that changes with the calendar, and the
        largest error the old model made: the light season starts on 1 March,
        and a leafless oak was shading a garden exactly as hard as a wall.
        """
        from ninanatur.garden.canopies import FIRST_LEAF_MONTH, LAST_LEAF_MONTH

        if self.bare_transmission is None:
            return self.transmission
        in_leaf = FIRST_LEAF_MONTH <= month <= LAST_LEAF_MONTH
        return self.transmission if in_leaf else self.bare_transmission

    @property
    def top(self) -> float:
        """How high the top of this thing is, absolutely."""
        return self.base + self.height

    @property
    def centre(self) -> tuple[float, float]:
        n = len(self.footprint) or 1
        return (
            sum(p[0] for p in self.footprint) / n,
            sum(p[1] for p in self.footprint) / n,
        )


def shadow_length(height: float, altitude: float) -> float:
    """How far an obstacle's shadow reaches, in metres.

    Returns 0 when the sun is at or below `MIN_ALTITUDE`; the caller treats that
    as no usable sun rather than as an unbounded shadow.
    """
    if altitude <= MIN_ALTITUDE:
        return 0.0
    return height / math.tan(math.radians(altitude))


def shadow_offset(height: float, sun: SunPosition) -> tuple[float, float] | None:
    """How far and which way a thing this tall throws its shadow, in metres,
    x east and y north — None where the sun is too low to count.

    Azimuth is clockwise from north, so the sun lies at (sin A, cos A) and the
    shadow runs the other way.
    """
    length = shadow_length(height, sun.altitude)
    if length <= 0:
        return None
    azimuth = math.radians(sun.azimuth)
    return -math.sin(azimuth) * length, -math.cos(azimuth) * length


def shadow_hull(obstacle: Obstacle, sun: SunPosition) -> list[tuple[float, float]]:
    """A cheap superset of the ground this object shades, at this sun position.

    The convex hull of the footprint and its copy swept along the shadow. For a
    convex outline that is the shadow; for a concave one it covers the open
    ground in an L's inner corner, so it is only ever a first rejection: the
    point tests (`is_shaded`, `field.ShadowAt`) ask the exact question inside
    it, and nothing draws it (doc 116). Until Wave 26 this was
    `shadow_polygon`, and it was drawn.
    """
    offset = shadow_offset(obstacle.height, sun)
    if offset is None:
        return list(obstacle.footprint)
    dx, dy = offset
    swept = [(px + dx, py + dy) for px, py in obstacle.footprint]
    return convex_hull(list(obstacle.footprint) + swept)


def shadow_rings(obstacles: list[Obstacle], sun: SunPosition) -> list[list[tuple[float, float]]]:
    """Every shadow at this moment, as rings to be drawn in one path under the
    non-zero rule (doc 116): outlines anticlockwise, holes clockwise.

    Exact for concave outlines, so what the plan draws is what the light model
    counts; a courtyard the sun still reaches is a hole. Each obstacle's shadow
    is its own shape — two that overlap add up to one filled area in the path,
    and are not merged here, which is what a union of every shadow in the
    garden cost a frame (review, 2026-09-22).
    """
    rings: list[list[tuple[float, float]]] = []
    for obstacle in obstacles:
        offset = shadow_offset(obstacle.height, sun)
        if offset is not None:
            rings.extend(shadow_shape(list(obstacle.footprint), *offset))
    return rings


def is_shaded(
    point: Point,
    obstacle: Obstacle,
    sun: SunPosition,
    height_above_ground: float = 0.0,
) -> bool:
    """Whether the obstacle blocks this sun from this point.

    `height_above_ground` raises the point. A bed 80 cm up stands above a 1.2 m
    fence, and only the obstacle's height *above the bed* casts anything onto it
    — measuring every shadow against the ground shades a raised bed exactly as
    hard as a border, which makes the sunniest beds in a small garden look
    shaded.
    """
    if sun.altitude <= MIN_ALTITUDE:
        # No usable sun to block — treat as shaded so the hour is not counted.
        return True

    effective = obstacle.height - height_above_ground
    if effective <= 0:
        return False

    lifted = Obstacle(footprint=obstacle.footprint, height=effective)
    if not covers(shadow_hull(lifted, sun), (point.x, point.y)):
        return False
    if is_convex(obstacle.footprint):
        return True
    # The hull of a concave outline covers its inner corner, which is open
    # ground: ask whether the ray towards the sun meets the footprint in reach.
    azimuth = math.radians(sun.azimuth)
    sin_a, cos_a = math.sin(azimuth), math.cos(azimuth)
    aligned = tuple((px * cos_a - py * sin_a, px * sin_a + py * cos_a)
                    for px, py in obstacle.footprint)
    near = near_edge(aligned, point.x * cos_a - point.y * sin_a,
                     point.x * sin_a + point.y * cos_a)
    return near is not None and shadow_length(effective, sun.altitude) >= near
