"""Rings from OpenStreetMap's multipolygons, joined from their ways.

Shared by the land around a garden (doc 114) and the buildings the map import
places (doc 31). A multipolygon's outline is usually several ways, each a
stretch of it, in no particular order or direction.
"""
from __future__ import annotations

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


def holes_within(outer: list[LatLon], inners: list[list[LatLon]]) -> list[list[LatLon]]:
    """The inner rings that lie in this outer ring: a courtyard, a light well.
    One corner strictly inside is enough — an inner ring may touch the outer
    at a node, and a corner on the wall says nothing."""
    return [hole for hole in inners if any(_inside(p, outer) for p in hole)]


def in_any(point: LatLon, rings: list[list[LatLon]]) -> bool:
    """Whether the point lies in one of the rings."""
    return any(_inside(point, ring) for ring in rings)


def _inside(point: LatLon, ring: list[LatLon]) -> bool:
    odd = False
    for p, q in zip(ring, ring[1:] + ring[:1], strict=True):
        if (p.lat > point.lat) != (q.lat > point.lat) and point.lon < (
            p.lon + (point.lat - p.lat) * (q.lon - p.lon) / (q.lat - p.lat)
        ):
            odd = not odd
    return odd


__all__ = ["assemble", "holes_within", "in_any"]
