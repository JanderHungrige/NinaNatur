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


def shadow_polygon(obstacle: Obstacle, sun: SunPosition) -> list[tuple[float, float]]:
    """The ground this object shades, at this sun position.

    The footprint swept along the anti-solar direction by
    `height / tan(altitude)`, and the convex hull of the original and the swept
    copy. For the shapes a garden contains — rectangles, circles, sketched
    outlines — the hull is the shadow; for a genuinely concave outline it is
    slightly generous, which is stated rather than pretended away.
    """
    length = shadow_length(obstacle.height, sun.altitude)
    if length <= 0:
        return list(obstacle.footprint)

    # Azimuth is clockwise from north, so the sun lies at (sin A, cos A) and the
    # shadow runs the other way.
    azimuth = math.radians(sun.azimuth)
    dx, dy = -math.sin(azimuth) * length, -math.cos(azimuth) * length
    swept = [(px + dx, py + dy) for px, py in obstacle.footprint]
    return _convex_hull(list(obstacle.footprint) + swept)


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Andrew's monotone chain. Small inputs — a rectangle's shadow is eight
    points before the hull and four to six after."""
    unique = sorted(set(points))
    if len(unique) < 3:
        return unique

    def half(source: list[tuple[float, float]]) -> list[tuple[float, float]]:
        chain: list[tuple[float, float]] = []
        for p in source:
            while len(chain) >= 2 and _cross(chain[-2], chain[-1], p) <= 0:
                chain.pop()
            chain.append(p)
        return chain[:-1]

    return half(unique) + half(unique[::-1])


def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


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
    return covers(shadow_polygon(lifted, sun), (point.x, point.y))
