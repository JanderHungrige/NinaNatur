"""Does an obstacle put a point in shadow?

Obstacles are footprints standing to a height: the walls, hedges and sheds a
garden contains. A roof the model knows casts as its planes (doc 120), and a
tree's or shrub's crown as an ellipsoid on its trunk that passes light by the
depth a ray crosses (doc 121).

Garden coordinates are metres with x east and y north, matching `position.py`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ninanatur.garden.footprint import covers
from ninanatur.solar.crown import Crown, chord, outline, standing
from ninanatur.solar.position import SunPosition
from ninanatur.solar.reach import is_convex, near_edge
from ninanatur.solar.sweep import RoofSolid, convex_hull, roof_shadow, shadow_shape

# Below this the sun is weak and in practice blocked by whatever surrounds the
# garden. It also bounds the shadow: 1/tan(altitude) grows without limit as the
# sun approaches the horizon, and a 4 m wall would otherwise shade half a village.
#
# 3° since Wave 26, 5° before: 0.71 h a day of the open season's sun lies between
# 2° and 5° (plan 03, E6), and the horizon ring (Wave 17) now says where hills
# really block it. Below about 3°, refraction and haze make direct sun
# irrelevant to a plant, and shadows run twenty times a thing's height.
MIN_ALTITUDE = 3.0


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
    #: The roof over it (doc 120). None for anything whose top is not a roof
    #: the model knows the planes of: a flat roof, a shape nobody has
    #: identified, a wall, a hedge — or a crown, which has its own field.
    roof: RoofSolid | None = None
    #: The crown it is (doc 121): an ellipsoid on a trunk that passes light by
    #: the depth of the crossing. None for anything that is not a tree's crown.
    crown: Crown | None = None
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
        return passes(self.transmission, self.bare_transmission, month)

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


def passes(transmission: float, bare: float | None, month: int) -> float:
    """What passes through something that casts, in this month: a crown in
    leaf from May to October passes `transmission`, bare outside it `bare`;
    anything without a season — built, or evergreen — the same all year. The
    one rule for it; the raster asks it too (doc 117)."""
    from ninanatur.garden.canopies import FIRST_LEAF_MONTH, LAST_LEAF_MONTH

    if bare is None or FIRST_LEAF_MONTH <= month <= LAST_LEAF_MONTH:
        return transmission
    return bare


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
        per_metre = shadow_offset(1.0, sun)
        if per_metre is None:
            continue
        if obstacle.roof is not None:
            # A roof casts as a roof (doc 120): each corner by its own height.
            rings.extend(roof_shadow(list(obstacle.footprint), obstacle.roof, per_metre))
            continue
        if obstacle.crown is not None:
            # A crown throws the ellipse its ellipsoid does (doc 121).
            rings.append(outline(standing(obstacle.crown, obstacle.base), obstacle.base,
                                 per_metre))
            continue
        rings.extend(shadow_shape(list(obstacle.footprint),
                                  per_metre[0] * obstacle.height,
                                  per_metre[1] * obstacle.height))
    return rings


def _meets_solid(point: Point, obstacle: Obstacle, sun: SunPosition,
                 height_above_ground: float) -> bool:
    """Whether the ray from the point towards the sun meets the solid under a
    roof (doc 120) — the same interval the raster cuts, walked here by hand so
    the slow reference stays an answer of its own (doc 117).

    The ray is taken by horizontal distance t: it is inside a convex piece
    while every one of its walls and every one of the roof's planes allows it,
    and it meets the piece when some t allows them all at once.
    """
    from ninanatur.solar.convex_parts import convex_parts

    assert obstacle.roof is not None
    cot = 1.0 / math.tan(math.radians(sun.altitude))
    azimuth = math.radians(sun.azimuth)
    east, north = math.sin(azimuth), math.cos(azimuth)
    z = obstacle.base + height_above_ground
    planes = [(nx, ny, nz, d + nz * obstacle.base) for nx, ny, nz, d in obstacle.roof.planes]
    for ring in convex_parts(list(obstacle.footprint)):
        walls = [((by - ay), -(bx - ax), ax * (by - ay) - ay * (bx - ax))
                 for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True)]
        bounds = [(nx, ny, 0.0, offset) for nx, ny, offset in walls]
        bounds += [(0.0, 0.0, 1.0, obstacle.top), *planes]
        if _allows(bounds, point.x, point.y, z, east, north, cot):
            return True
    return False


def _allows(bounds: list[tuple[float, float, float, float]], x: float, y: float, z: float,
            east: float, north: float, cot: float) -> bool:
    """Whether any t ≥ 0 satisfies every half-space n·P(t) ≤ d along the ray."""
    low, high = 0.0, math.inf
    for nx, ny, nz, d in bounds:
        along = nx * east + ny * north + nz / cot
        room = d - (nx * x + ny * y + nz * z)
        if abs(along) <= 1e-12:
            if room < 0:
                return False
            continue
        limit = room / along
        if along > 0:
            high = min(high, limit)
        else:
            low = max(low, limit)
    return low <= high


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

    if obstacle.roof is not None:
        return _meets_solid(point, obstacle, sun, height_above_ground)
    if obstacle.crown is not None:
        azimuth = math.radians(sun.azimuth)
        return bool(chord(standing(obstacle.crown, obstacle.base), point.x, point.y,
                          obstacle.base + height_above_ground, math.sin(azimuth),
                          math.cos(azimuth), 1.0 / math.tan(math.radians(sun.altitude))) > 0)

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
