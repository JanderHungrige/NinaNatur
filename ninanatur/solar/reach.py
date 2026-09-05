"""How far a shadow has to travel to arrive at a point.

Wave 16 could answer "is this point in that shadow" with a polygon, because
every point stood at the same height and so every shadow had one length. Wave 17
gives each point its own height, and a shadow's length is then
`(top - z) / tan(altitude)` — different for every point.

Rather than build a polygon per point, the question is turned around: the swept
hull of a footprint is that footprint plus a segment, so a point lies inside it
exactly when the ray back towards the sun meets the footprint within the
shadow's length. In the frame where the shadow runs along -y that is a single
interval comparison.
"""
from __future__ import annotations


def near_edge(
    aligned: tuple[tuple[float, float], ...], x: float, y: float
) -> float | None:
    """How far the shadow must reach from the footprint to arrive at (x, y).

    Both coordinates are in the aligned frame, where the shadow runs along -y,
    so the footprint's near edge above the point is the distance the shadow has
    to cover. Returns None when the line through the point misses the footprint
    entirely, or when the point is beyond its far edge — sunward of the thing
    casting, where no shadow of it ever falls.
    """
    lo: float | None = None
    hi: float | None = None
    n = len(aligned)
    for i in range(n):
        ax, ay = aligned[i]
        bx, by = aligned[(i + 1) % n]
        if (ax > x) == (bx > x):
            continue
        cut = ay + (by - ay) * (x - ax) / (bx - ax)
        lo = cut if lo is None or cut < lo else lo
        hi = cut if hi is None or cut > hi else hi
    if lo is None or hi is None or y > hi:
        return None
    return lo - y


__all__ = ["near_edge"]
