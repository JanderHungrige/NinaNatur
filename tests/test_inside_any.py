"""Which laser points are roofs — the same answer, in seconds (docs 105, 107).

The owner's report of 2026-09-28 was a first analysis that ran for minutes. In
the image, a garden in Köln-Ehrenfeld spent 381 of its 384 laser seconds
casting 721,422 points against every edge of 4,359 outlines, most of them
nowhere near the window. Each outline now meets only the points in its box;
these tests hold it to the answer of the cast over every point, and to the
work it does.
"""
from __future__ import annotations

import numpy as np
import pytest

from ninanatur.geo import inside
from ninanatur.geo.inside import Outline, inside_any


def _every_point_against_every_edge(x: np.ndarray, y: np.ndarray,
                                    footprints: list[Outline]) -> np.ndarray:
    """The cast as it was, over every point for every outline: the reference."""
    found = np.zeros(len(x), dtype=bool)
    for outline in footprints:
        if len(outline) < 3:
            continue
        crossings = np.zeros(len(x), dtype=bool)
        for (ax, ay), (bx, by) in zip(outline, [*outline[1:], outline[0]], strict=True):
            straddles = (ay > y) != (by > y)
            with np.errstate(divide="ignore", invalid="ignore"):
                at = ax + (y - ay) * (bx - ax) / np.where(by == ay, np.nan, by - ay)
            crossings ^= straddles & (x < at)
        found |= crossings
    return found


def _star(rng: np.random.Generator, spread: float, grid: bool) -> Outline:
    """A concave outline somewhere in a 1 km tile — a building model's reach."""
    cx, cy = rng.uniform(-spread, spread, 2)
    corners = int(rng.integers(3, 14))
    angles = np.sort(rng.uniform(0, 2 * np.pi, corners))
    radii = rng.uniform(2, 25, corners)
    points = [(cx + r * np.cos(a), cy + r * np.sin(a)) for a, r in zip(angles, radii, strict=True)]
    if grid:
        points = [(float(round(px)), float(round(py))) for px, py in points]
    return points


def _points(rng: np.random.Generator, count: int, grid: bool) -> tuple[np.ndarray, np.ndarray]:
    x, y = rng.uniform(-150, 150, count), rng.uniform(-150, 150, count)
    if grid:
        # On whole metres the points land on corners and along edges, exactly
        # where a box that is a hair too small would change the answer.
        x, y = np.round(x), np.round(y)
    return x, y


@pytest.mark.parametrize("seed", range(12))
@pytest.mark.parametrize("grid", [False, True])
def test_the_answer_is_the_cast_over_every_point(seed: int, grid: bool) -> None:
    rng = np.random.default_rng(seed)
    x, y = _points(rng, 20_000, grid)
    footprints = [_star(rng, 500.0, grid) for _ in range(150)]
    # A flat edge, a sliver of two corners, and the window's own edge.
    footprints += [[(-20.0, 5.0), (20.0, 5.0), (20.0, 5.0), (0.0, 30.0)],
                   [(1.0, 1.0), (2.0, 2.0)],
                   [(-150.0, -150.0), (150.0, -150.0), (150.0, -140.0), (-150.0, -140.0)]]

    found = inside_any(x, y, footprints)

    assert np.array_equal(found, _every_point_against_every_edge(x, y, footprints))
    assert found.any() and not found.all()


def test_each_outline_meets_only_the_points_in_its_box(monkeypatch: pytest.MonkeyPatch) -> None:
    """The work, not only the answer: an outline beyond the window meets no
    point, and one inside it meets the points in its box and no others."""
    rng = np.random.default_rng(7)
    x, y = _points(rng, 20_000, grid=False)
    footprints = [_star(rng, 500.0, grid=False) for _ in range(300)]
    met: list[int] = []
    real = inside._crossings

    def counting(px: np.ndarray, py: np.ndarray, outline: Outline) -> np.ndarray:
        met.append(len(px))
        return real(px, py, outline)

    monkeypatch.setattr(inside, "_crossings", counting)
    inside_any(x, y, footprints)

    in_boxes = []
    for outline in footprints:
        xs, ys = [p[0] for p in outline], [p[1] for p in outline]
        count = int(((x >= min(xs)) & (x <= max(xs)) & (y >= min(ys)) & (y <= max(ys))).sum())
        if count:
            in_boxes.append(count)
    assert met == in_boxes
    assert sum(met) < len(x) * len(footprints) / 100


def test_no_points_are_no_roofs() -> None:
    empty = np.array([], dtype=float)
    assert inside_any(empty, empty, [[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]]).shape == (0,)
