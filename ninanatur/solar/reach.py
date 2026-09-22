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

    Both coordinates are in the aligned frame, where the shadow runs along -y
    and the sun lies towards +y, so the distance to cover is from the point up
    to the footprint's next edge above it — 0 for a point under the footprint.
    Returns None when the line through the point misses the footprint above it:
    sunward of the thing casting, where no shadow of it ever falls.

    The line can cross a concave outline more than once. Until 2026-09-22 only
    its lowest and highest crossings were read, which put the open ground in an
    L-shaped house's inner corner under the house (review).
    """
    cuts: list[float] = []
    n = len(aligned)
    for i in range(n):
        ax, ay = aligned[i]
        bx, by = aligned[(i + 1) % n]
        if (ax > x) == (bx > x):
            continue
        cuts.append(ay + (by - ay) * (x - ax) / (bx - ax))
    cuts.sort()
    for start, end in zip(cuts[::2], cuts[1::2], strict=False):
        if y <= end:
            return max(0.0, start - y)
    return None


def is_convex(outline: list[tuple[float, float]] | tuple[tuple[float, float], ...]) -> bool:
    """Whether an outline turns the same way at every corner. A straight run
    (a node on a wall) does not count as a turn, and a point repeated back to
    back — OpenStreetMap closes every way on its first node — is one point: at a
    repeated point the turn was never measured, and an L closed at its inner
    corner passed as convex (review, 2026-09-22). An edge that doubles straight
    back is not convex."""
    ring = [p for i, p in enumerate(outline) if p != outline[i - 1]] or list(outline[:1])
    n = len(ring)
    turns = set()
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = ring[i], ring[(i + 1) % n], ring[(i + 2) % n]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) > 1e-9:
            turns.add(cross > 0)
        elif (bx - ax) * (cx - bx) + (by - ay) * (cy - by) < 0:
            # Straight back the way it came: a spur. A wall drawn as a line
            # has one at the inside of every corner (`polyline.band_of`), and
            # read as no turn at all it made every turning wall convex — its
            # hull then shaded the corner it turns round (review, 2026-09-22).
            return False
    return len(turns) <= 1


__all__ = ["is_convex", "near_edge"]
