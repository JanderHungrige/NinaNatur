"""Rings from OpenStreetMap's multipolygons: joined from their ways, holes kept.

Shared by the land around a garden (doc 114) and the buildings the map import
places (doc 31). A multipolygon's outline is usually several ways, each a
stretch of it, in no particular order or direction.
"""
from __future__ import annotations

import math

from ninanatur.geo.projection import LatLon


def assemble(pieces: list[list[LatLon] | None]) -> list[list[LatLon]]:
    """Join ways end to end into closed rings, the last point not repeated.

    Drawn one by one they are open lines, and a filled open line closes itself
    with a straight edge — a wedge across the plan. So a chain that cannot be
    closed is dropped, never drawn.
    """
    rings: list[list[LatLon]] = []
    loose: list[list[LatLon]] = []
    for piece in pieces:
        if piece is None or len(piece) < 2:
            continue
        (rings if piece[0] == piece[-1] else loose).append(list(piece))
    while loose:
        ring = loose.pop()
        while ring[0] != ring[-1]:
            joined = _next_piece(ring[-1], loose)
            if joined is None:
                break
            ring.extend(joined[1:])
        if ring[0] == ring[-1]:
            rings.append(ring)
    return [ring[:-1] for ring in rings if len(ring) >= 4]


def _next_piece(end: LatLon, loose: list[list[LatLon]]) -> list[LatLon] | None:
    """The piece that continues from `end`, taken out of `loose` and turned to
    run on from it; None if no piece touches it."""
    for index, piece in enumerate(loose):
        if piece[0] == end:
            return loose.pop(index)
        if piece[-1] == end:
            return list(reversed(loose.pop(index)))
    return None


def with_holes(outer: list[LatLon], holes: list[list[LatLon]]) -> list[LatLon]:
    """One outline for a ring with holes in it: each hole inside the ring is
    joined to it by a slit, there and back, at the pair of corners closest
    together. The slit has no width, so the courtyard stays open ground — for
    the shadow model (`solar.reach`), for a bed drawn in it, and on the plan,
    where the hole runs the other way round and is not filled."""
    ring = list(outer)
    turn = _turn(ring)
    for hole in holes:
        if len(hole) < 3 or not _inside(hole[0], ring):
            continue
        loop = list(hole) if _turn(hole) != turn else list(reversed(hole))
        i, j = min(((a, b) for a in range(len(ring)) for b in range(len(loop))),
                   key=lambda pair: _apart(ring[pair[0]], loop[pair[1]]))
        ring = ring[:i + 1] + loop[j:] + loop[:j + 1] + ring[i:]
    return ring


def _apart(a: LatLon, b: LatLon) -> float:
    """Squared distance, the longitude scaled to the latitude: good enough to
    choose the nearest pair of corners on one building."""
    scale = math.cos(math.radians(a.lat))
    return ((a.lon - b.lon) * scale) ** 2 + (a.lat - b.lat) ** 2


def _turn(ring: list[LatLon]) -> bool:
    """True for a ring that runs anticlockwise (east as x, north as y)."""
    pairs = zip(ring, ring[1:] + ring[:1], strict=True)
    return sum(p.lon * q.lat - q.lon * p.lat for p, q in pairs) > 0


def _inside(point: LatLon, ring: list[LatLon]) -> bool:
    odd = False
    for p, q in zip(ring, ring[1:] + ring[:1], strict=True):
        if (p.lat > point.lat) != (q.lat > point.lat) and point.lon < (
            p.lon + (point.lat - p.lat) * (q.lon - p.lon) / (q.lat - p.lat)
        ):
            odd = not odd
    return odd


__all__ = ["assemble", "with_holes"]
