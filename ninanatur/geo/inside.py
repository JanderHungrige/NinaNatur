"""Which laser points stand inside a surveyed building (docs 105, 107).

What stands inside a footprint is a roof. The classification cannot say so —
Nordrhein-Westfalen's tile has no building code at all — and the building model
does, by a ray cast along +x, as everywhere else here.

The ray cast went over every point for every edge of every outline at first.
The building model covers its whole survey tile rather than the window, so in
Köln-Ehrenfeld 721,422 points met 4,359 outlines with 34,776 edges, and the
first analysis spent 381 of its 384 laser seconds here: the long wait behind
the owner's report of 2026-09-28, measured in the image. A point outside an
outline's box cannot be inside the outline, so each outline now meets only the
points in its box, found by one sort and two binary searches. The answer is
the same; the points in a box meet exactly the arithmetic they met before.
"""
from __future__ import annotations

import numpy as np

Outline = list[tuple[float, float]]


def inside_any(x: np.ndarray, y: np.ndarray, footprints: list[Outline]) -> np.ndarray:
    """Which of the points stand inside any of the outlines."""
    inside = np.zeros(len(x), dtype=bool)
    if len(x) == 0:
        return inside
    order = np.argsort(x, kind="stable")
    by_x = x[order]
    for outline in footprints:
        if len(outline) < 3:
            continue
        near = _in_box(order, by_x, y, outline)
        if len(near):
            inside[near] |= _crossings(x[near], y[near], outline)
    return inside


def _in_box(order: np.ndarray, by_x: np.ndarray, y: np.ndarray, outline: Outline) -> np.ndarray:
    """The points within the outline's box, its edges included, by index."""
    xs = [px for px, _ in outline]
    ys = [py for _, py in outline]
    first = int(np.searchsorted(by_x, min(xs), side="left"))
    last = int(np.searchsorted(by_x, max(xs), side="right"))
    candidates = order[first:last]
    height = y[candidates]
    picked: np.ndarray = candidates[(height >= min(ys)) & (height <= max(ys))]
    return picked


def _crossings(x: np.ndarray, y: np.ndarray, outline: Outline) -> np.ndarray:
    """A ray cast along +x from each point: an odd count of crossings is inside."""
    crossings = np.zeros(len(x), dtype=bool)
    for (ax, ay), (bx, by) in zip(outline, [*outline[1:], outline[0]], strict=True):
        straddles = (ay > y) != (by > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            at = ax + (y - ay) * (bx - ax) / np.where(by == ay, np.nan, by - ay)
        crossings ^= straddles & (x < at)
    return crossings


__all__ = ["Outline", "inside_any"]
