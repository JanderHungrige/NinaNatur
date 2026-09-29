"""A footprint as convex parts — Wave 26, feature 2 (doc 117).

The shadow of a union of prisms of one height is the union of their shadows, so
a concave house casts exactly what its convex parts cast together. Split once,
every shadow test becomes a convex one: a ray against a handful of half-planes,
which is what `raster` can do for thousands of cells at a time.

Split by shapely's constrained Delaunay triangulation, then merged back
(Hertel–Mehlhorn): two neighbouring parts become one wherever the result is
still convex. An L is two rectangles again rather than four triangles, and an
outline of twenty-four corners a handful of parts rather than twenty-two.
"""
from __future__ import annotations

import logging
from functools import lru_cache

import shapely
from shapely.errors import GEOSException
from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry

from ninanatur.solar.reach import is_convex

log = logging.getLogger(__name__)

Ring = tuple[tuple[float, float], ...]

#: Corners closer than this are one corner. A wall drawn as a line bevels a
#: straight joint into two corners that can differ in the last bit, and the
#: edge between them has no direction: its normal was noise, and its
#: half-plane cut half a hedge out of its own shadow (review, 2026-09-22).
SAME_M = 1e-7
#: A part or a triangle with less area than this is no ground at all.
FLAT_M2 = 1e-9
#: How wide a wall is taken to be when its corners enclose nothing — a wall
#: drawn as three corners on one line. The old field cast its shadow; so does
#: a band a centimetre wide.
THIN_M = 0.01


def convex_parts(footprint: list[tuple[float, float]]) -> tuple[Ring, ...]:
    """The footprint's convex parts, each anticlockwise and without its
    closing point. A convex, simple outline is its own single part."""
    return _parts(tuple(_cleaned(footprint)))


def solid_of(ring: list[tuple[float, float]]) -> list[Polygon]:
    """The shapes an outline encloses: itself if it is simple; the shapes it
    encloses if it crosses itself (`make_valid`, never dropped); a band a
    centimetre wide if it encloses nothing at all. The light model's parts
    and the drawn shadow (`sweep.shadow_shape`) both start from this."""
    if len(ring) >= 3:
        drawn = Polygon(ring)
        shape: BaseGeometry = drawn if drawn.is_valid else shapely.make_valid(drawn)
        found = [p for p in _polygons(shape) if p.area > FLAT_M2]
        if found:
            return found
    if len(ring) < 2:
        return []
    return _polygons(LineString([*ring, ring[0]]).buffer(THIN_M / 2))


@lru_cache(maxsize=4096)
def _parts(ring: Ring) -> tuple[Ring, ...]:
    if len(ring) >= 3 and Polygon(ring).is_valid and is_convex(list(ring)) \
            and abs(_area(ring)) > FLAT_M2:
        return (_anticlockwise(ring),)
    parts: list[Ring] = []
    for polygon in solid_of(list(ring)):
        triangles = [_anticlockwise(_open(t)) for t in _triangles(polygon)]
        parts.extend(_merged([t for t in triangles if abs(_area(t)) > FLAT_M2]))
    return tuple(parts)


def _triangles(polygon: Polygon) -> list[Polygon]:
    """The polygon's constrained Delaunay triangles. GEOS can refuse a valid
    polygon ("unable to find a convex corner"); it is asked again snapped to a
    micrometre and then repaired, and only then approximated — logged, never
    left to fail the whole garden's grid."""
    for attempt in (polygon, shapely.set_precision(polygon, 1e-6), polygon.buffer(0)):
        try:
            return _polygons(shapely.constrained_delaunay_triangles(attempt))
        except GEOSException:
            log.warning("triangulating an outline of %d corners failed; trying again",
                        len(polygon.exterior.coords), exc_info=True)
    log.warning("approximating an outline of %d corners by its Delaunay triangles",
                len(polygon.exterior.coords))
    return [t for t in _polygons(shapely.delaunay_triangles(polygon))
            if polygon.contains(t.representative_point())]


def _merged(pieces: list[Ring]) -> list[Ring]:
    """Neighbours joined wherever the join stays convex, until none can be.

    A shared edge is looked up by its corners, not searched for: a search of
    every pair from the start after every join grew with the cube of the
    corners, and a 500-corner outline took 18 s to split — in the serving
    process too, once roofs cast through their parts (review of stage 3,
    2026-09-28)."""
    alive = dict(enumerate(pieces))
    owner: dict[tuple[Key, Key], int] = {}
    for index, ring in alive.items():
        _own(owner, ring, index)
    waiting = sorted(alive, reverse=True)
    while waiting:
        index = waiting.pop()
        part = alive.get(index)
        if part is None:
            continue
        for k in range(len(part)):
            p, q = part[k], part[(k + 1) % len(part)]
            other = owner.get((_key(q), _key(p)))
            if other is None or other == index:
                continue
            both = _join(part, k, alive[other])
            if both is None:
                continue
            _own(owner, part, None)
            _own(owner, alive.pop(other), None)
            alive[index] = both
            _own(owner, both, index)
            waiting.append(index)
            break
    return list(alive.values())


Key = tuple[float, float]


def _key(point: tuple[float, float]) -> Key:
    """A corner as the index knows it: to the nanometre `_same` compares at."""
    return (round(point[0], 9), round(point[1], 9))


def _own(owner: dict[tuple[Key, Key], int], ring: Ring, index: int | None) -> None:
    """Enter a part's edges in the index — or, with None, take them out."""
    for k in range(len(ring)):
        edge = (_key(ring[k]), _key(ring[(k + 1) % len(ring)]))
        if index is None:
            owner.pop(edge, None)
        else:
            owner[edge] = index


def _join(a: Ring, i: int, b: Ring) -> Ring | None:
    """The two parts as one across a's edge i, which b shares the other way
    round, if the result is convex."""
    p, q = a[i], a[(i + 1) % len(a)]
    for j in range(len(b)):
        if _same(b[j], q) and _same(b[(j + 1) % len(b)], p):
            # Walk a from q round to p, then b from p round to q.
            ring = [a[(i + 1 + k) % len(a)] for k in range(len(a))]
            ring += [b[(j + 2 + k) % len(b)] for k in range(len(b) - 2)]
            merged = tuple(_without_straight(ring))
            return merged if is_convex(list(merged)) else None
    return None


def _without_straight(ring: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Without the corners a merge leaves on a straight line."""
    kept = []
    n = len(ring)
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = ring[i - 1], ring[i], ring[(i + 1) % n]
        if abs((bx - ax) * (cy - by) - (by - ay) * (cx - bx)) > 1e-12:
            kept.append(ring[i])
    return kept


def _cleaned(ring: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Without corners that are one corner (`SAME_M`), the closing point, and
    spurs — the tip where an outline runs straight back the way it came, as a
    wall drawn as a line does at the inside of every corner."""
    kept: list[tuple[float, float]] = []
    for p in ring:
        if not kept or not _same(p, kept[-1], SAME_M):
            kept.append(p)
    if len(kept) > 1 and _same(kept[0], kept[-1], SAME_M):
        kept.pop()
    spur = _spur_at(kept)
    while spur is not None and len(kept) > 3:
        del kept[spur]
        spur = _spur_at(kept)
    return kept


def _spur_at(ring: list[tuple[float, float]]) -> int | None:
    n = len(ring)
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = ring[i - 1], ring[i], ring[(i + 1) % n]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) <= 1e-9 and (bx - ax) * (cx - bx) + (by - ay) * (cy - by) < 0:
            return i
    return None


def _area(ring: Ring) -> float:
    return sum(ax * by - bx * ay
               for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True)) / 2


def _anticlockwise(ring: Ring) -> Ring:
    return ring if _area(ring) > 0 else tuple(reversed(ring))


def _open(polygon: Polygon) -> Ring:
    return tuple((float(x), float(y)) for x, y in polygon.exterior.coords[:-1])


def _polygons(shape: BaseGeometry) -> list[Polygon]:
    if isinstance(shape, Polygon):
        return [] if shape.is_empty else [shape]
    parts = getattr(shape, "geoms", ())
    return [p for part in parts for p in _polygons(part)]


def _same(a: tuple[float, float], b: tuple[float, float], tolerance: float = 1e-9) -> bool:
    return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance


__all__ = ["convex_parts", "solid_of"]
