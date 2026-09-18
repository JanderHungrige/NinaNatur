"""How much of one outline another covers.

The rule that decides whether a surveyed building is the one drawn (doc 83):
overlap, not distance between centres, because a garage beside a house has a
nearby centre and covers none of it. Measured by sampling the drawn footprint on
a half-metre grid and counting the points that fall inside the other outline.

Split from `measured.py` in Wave 21.
"""
from __future__ import annotations

#: How finely a footprint is sampled to measure that overlap. Half a metre —
#: fine enough that a garage cannot pass and coarse enough that a house is a
#: hundred points rather than ten thousand.
OVERLAP_STEP_M = 0.5


#: min x, min y, max x, max y.
Box = tuple[float, float, float, float]


def box_of(points: list[tuple[float, float]]) -> Box:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def overlaps(a: Box, b: Box) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def sample(footprint: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Points spread over a footprint, for measuring how much of it is covered."""
    if len(footprint) < 3:
        return []
    xs = [p[0] for p in footprint]
    ys = [p[1] for p in footprint]
    points: list[tuple[float, float]] = []
    y = min(ys)
    while y <= max(ys):
        x = min(xs)
        while x <= max(xs):
            if _inside(footprint, x, y):
                points.append((x, y))
            x += OVERLAP_STEP_M
        y += OVERLAP_STEP_M
    return points


def covered(points: list[tuple[float, float]], outline: list[tuple[float, float]]) -> float:
    """What share of those points falls inside this outline."""
    if not points or len(outline) < 3:
        return 0.0
    return sum(1 for x, y in points if _inside(outline, x, y)) / len(points)


def _inside(polygon: list[tuple[float, float]], x: float, y: float) -> bool:
    inside = False
    n = len(polygon)
    for i in range(n):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % n]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


__all__ = ["OVERLAP_STEP_M", "Box", "box_of", "covered", "overlaps", "sample"]
