"""Does an obstacle put a point in shadow?

Obstacles are vertical cylinders — a position, a radius and a height. That covers
the walls, hedges, trees and sheds a garden actually contains, and keeps the
question to a line-distance check.

Garden coordinates are metres with x east and y north, matching `position.py`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

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
    """Anything that casts a shadow, modelled as a vertical cylinder."""

    x: float
    y: float
    radius: float
    height: float


def shadow_length(height: float, altitude: float) -> float:
    """How far an obstacle's shadow reaches, in metres.

    Returns 0 when the sun is at or below `MIN_ALTITUDE`; the caller treats that
    as no usable sun rather than as an unbounded shadow.
    """
    if altitude <= MIN_ALTITUDE:
        return 0.0
    return height / math.tan(math.radians(altitude))


def is_shaded(point: Point, obstacle: Obstacle, sun: SunPosition) -> bool:
    """Whether the obstacle blocks this sun from this point.

    The shadow runs opposite the sun's azimuth. A point is inside it when it lies
    ahead of the obstacle along that direction, within the shadow's reach, and no
    further sideways than the obstacle is wide.
    """
    if sun.altitude <= MIN_ALTITUDE:
        # No usable sun to block — treat as shaded so the hour is not counted.
        return True

    length = shadow_length(obstacle.height, sun.altitude)
    if length <= 0:
        return True

    # Shadow direction: opposite the sun. Azimuth is clockwise from north, so the
    # unit vector towards the sun is (sin A, cos A) in (east, north).
    azimuth = math.radians(sun.azimuth)
    shadow_dx, shadow_dy = -math.sin(azimuth), -math.cos(azimuth)

    dx, dy = point.x - obstacle.x, point.y - obstacle.y

    # Directly beneath it. The cast-shadow test below starts at the obstacle's
    # centre and runs away from the sun, so a point under the canopy scored
    # `along == 0` and came out in full sun — a bed under a recorded tree read
    # Ellenberg 8. Ground inside the footprint is shaded whatever the sun does.
    if math.hypot(dx, dy) <= obstacle.radius:
        return True

    along = dx * shadow_dx + dy * shadow_dy
    if along <= 0 or along > length:
        return False

    # Perpendicular offset from the shadow's centre line.
    across = abs(dx * -shadow_dy + dy * shadow_dx)
    return across <= obstacle.radius
