"""Which way a surveyed roof falls, read off its faces (doc 94).

The survey draws every roof as labelled polygons in three dimensions. A face's
normal says which way it falls and how steeply; the roof's highest edge says
where its ridge runs. Both are in the tile Wave 19 already downloads — until
Wave 21 only the faces' lowest point was read, for the eaves.

It matters more than it sounds. Measured against three NRW tiles, the long side
of the footprint — what the model assumed until now — turns the ridge by 45° or
more on 65 % of gables, because a terraced house is deeper than it is wide and
its ridge runs parallel to the street.

A bearing here is the direction a roof *falls*: degrees clockwise from north,
downhill. In the tile's own grid until `bearing_on_garden` turns it onto the
garden's axes.
"""
from __future__ import annotations

import math

from ninanatur.garden.roofs import Roof
from ninanatur.geo.projection import LatLon, to_metres
from ninanatur.geo.utm import to_latlon

Point = tuple[float, float, float]

#: Vertices this close to the highest point are on the ridge. The faces of one
#: ridge meet within centimetres; a chimney or dormer a few decimetres off is
#: not part of it.
TOP_M = 0.3
#: A ridge shorter than this is a point — a pyramid's top — not a direction.
MIN_RIDGE_M = 1.0
#: Faces flatter than this fall nowhere in particular (roofshape's own floor).
MIN_FACE_PITCH_DEG = 5.0
#: How much the faces must agree to say anything: the length of their mean
#: direction, from 0 when they cancel to 1 when they all fall one way.
MIN_AGREEMENT = 0.5
#: A gable's highest edge and its faces this far apart mean the highest edge is
#: not the main ridge — a cross-gable, a tower — and neither reading is used.
AGREE_DEG = 10.0


def fall_of(roof: Roof, faces: list[list[Point]]) -> float | None:
    """The bearing this roof falls towards; None where its faces do not say.

    A gable or a hip falls both ways from its ridge, so its answer is the one of
    the two in [0, 180). A pent's is anywhere in [0, 360). Any other shape has
    no one direction to give.
    """
    if roof is Roof.PENT:
        return _mean_fall(_pitched(faces))
    if roof not in (Roof.GABLE, Roof.HIP):
        return None
    ridge = _highest_edge(faces)
    if ridge is None:
        return None
    fall = (ridge + 90.0) % 180.0
    # A gable's faces are two planes and agree with its ridge or something else
    # stands on it. A hip's four cancel each other out too often to be a check.
    if roof is Roof.GABLE:
        axis = _fall_axis(_pitched(faces))
        if axis is not None and _apart(axis, fall, 180.0) >= AGREE_DEG:
            return None
    return fall


def bearing_on_garden(
    bearing: float, east: float, north: float, zone: int, anchor: LatLon
) -> float:
    """A grid bearing at a point, turned onto the garden's axes (true north).

    Both ends of a ten-metre step along it go through the projection the outline
    goes through, so the two cannot disagree. Grid and true north differ by up
    to 2° in NRW.
    """
    ends = []
    for step in (0.0, 10.0):
        lat, lon = to_latlon(
            east + step * math.sin(math.radians(bearing)),
            north + step * math.cos(math.radians(bearing)),
            zone,
        )
        ends.append(to_metres(LatLon(lat=lat, lon=lon), anchor))
    return math.degrees(math.atan2(ends[1].x - ends[0].x, ends[1].y - ends[0].y)) % 360.0


def _pitched(faces: list[list[Point]]) -> list[tuple[float, float]]:
    """Each face steep enough to fall somewhere: its area and its fall."""
    found: list[tuple[float, float]] = []
    for face in faces:
        nx, ny, nz = _normal(face)
        size = math.sqrt(nx * nx + ny * ny + nz * nz)
        if size == 0.0:
            continue
        if math.degrees(math.atan2(math.hypot(nx, ny), nz)) < MIN_FACE_PITCH_DEG:
            continue
        found.append((size / 2.0, math.degrees(math.atan2(nx, ny)) % 360.0))
    return found


def _normal(face: list[Point]) -> Point:
    """Newell's normal, turned to point up, so its level part points downhill.

    Taken about the face's first corner: UTM coordinates run to millions of
    metres, and products of those lose the centimetres a roof is made of.
    """
    if not face:
        return (0.0, 0.0, 0.0)
    ox, oy, oz = face[0]
    nx = ny = nz = 0.0
    for index, (x, y, z) in enumerate(face):
        x2, y2, z2 = face[(index + 1) % len(face)]
        x, y, z, x2, y2, z2 = x - ox, y - oy, z - oz, x2 - ox, y2 - oy, z2 - oz
        nx += (y - y2) * (z + z2)
        ny += (z - z2) * (x + x2)
        nz += (x - x2) * (y + y2)
    return (nx, ny, nz) if nz >= 0.0 else (-nx, -ny, -nz)


def _mean_fall(pitched: list[tuple[float, float]]) -> float | None:
    """The one way the faces fall, weighted by area, if they agree on one."""
    total = sum(area for area, _ in pitched)
    east = sum(area * math.sin(math.radians(fall)) for area, fall in pitched)
    north = sum(area * math.cos(math.radians(fall)) for area, fall in pitched)
    if total == 0.0 or math.hypot(east, north) / total < MIN_AGREEMENT:
        return None
    return math.degrees(math.atan2(east, north)) % 360.0


def _fall_axis(pitched: list[tuple[float, float]]) -> float | None:
    """The line the faces fall along, in [0, 180).

    Angles doubled, so that a face falling north and one falling south agree on
    a line rather than cancelling out.
    """
    total = sum(area for area, _ in pitched)
    c = sum(area * math.cos(math.radians(2.0 * fall)) for area, fall in pitched)
    s = sum(area * math.sin(math.radians(2.0 * fall)) for area, fall in pitched)
    if total == 0.0 or math.hypot(c, s) / total < MIN_AGREEMENT:
        return None
    return (math.degrees(math.atan2(s, c)) / 2.0) % 180.0


def _highest_edge(faces: list[list[Point]]) -> float | None:
    """The ridge's bearing, in [0, 180): the two vertices near the top that lie
    farthest apart, if they are far enough apart to be a line."""
    points = [point for face in faces for point in face]
    if not points:
        return None
    top = max(z for _x, _y, z in points)
    near = sorted({(round(x, 2), round(y, 2)) for x, y, z in points if top - z <= TOP_M})
    best: tuple[float, tuple[float, float], tuple[float, float]] | None = None
    for index, a in enumerate(near):
        for b in near[index + 1:]:
            gap = math.dist(a, b)
            if best is None or gap > best[0]:
                best = (gap, a, b)
    if best is None or best[0] < MIN_RIDGE_M:
        return None
    (x1, y1), (x2, y2) = best[1], best[2]
    return math.degrees(math.atan2(x2 - x1, y2 - y1)) % 180.0


def _apart(a: float, b: float, period: float) -> float:
    gap = abs(a - b) % period
    return min(gap, period - gap)


__all__ = ["bearing_on_garden", "fall_of"]
