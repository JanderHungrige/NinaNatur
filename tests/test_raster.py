"""The raster answers what the field answered, cell for cell (doc 117).

`field.ShadowField` is the slow, obviously right path: every moment, every
obstacle, every cell, in Python. The raster asks the same question of all the
cells at once. At the same sampling the two must agree on every cell — with
houses of any outline, crowns that pass light and lose their leaves, ground
that rises under cells and houses, skies of their own, and roofs that leave
their own building out of their shadows.
"""
from __future__ import annotations

import math
import random
from typing import Any

import numpy as np
import pytest
from concave_shapes import scene

from ninanatur.solar import raster_grid
from ninanatur.solar.field import shadow_field
from ninanatur.solar.light import MINUTE_STEP
from ninanatur.solar.position import Location
from ninanatur.solar.raster import moments_for, parts_of, point_hours
from ninanatur.solar.raster_grid import Cells, grid_hours
from ninanatur.solar.shading import Obstacle

BERLIN = Location(52.52, 13.40)
CELL = 2.0


def _garden(rng: random.Random) -> list[Obstacle]:
    """Houses of any outline, on ground of their own, and two crowns."""
    houses = [Obstacle(footprint=o, height=rng.uniform(3, 12), base=rng.uniform(0, 1.5),
                       owner=i) for i, o in enumerate(scene(rng))]
    crowns = [Obstacle(footprint=[(cx + 3 * math.cos(a), cy + 3 * math.sin(a))
                                  for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)],
                       height=rng.uniform(6, 14), transmission=0.2, bare_transmission=0.75,
                       owner=100 + k)
              for k, (cx, cy) in enumerate([(rng.uniform(-15, 15), rng.uniform(-15, 15))
                                            for _ in range(2)])]
    return houses + crowns


def _cells(rng: random.Random, obstacles: list[Obstacle]) -> Cells:
    xs = np.arange(-20.0, 20.0, CELL)
    ys = np.arange(-20.0, 20.0, CELL)
    z = np.array([[0.4 * math.sin(x / 7) + 0.3 * math.cos(y / 5) + 0.8 for x in xs] for y in ys])
    owner = np.full(z.shape, -1)
    # The first house's roof: its cells stand at its top and leave it out.
    roofed = obstacles[0]
    from ninanatur.garden.footprint import covers
    for r, y in enumerate(ys):
        for c, x in enumerate(xs):
            if covers(list(roofed.footprint), (float(x), float(y))):
                owner[r, c] = roofed.owner if roofed.owner is not None else -1
                z[r, c] = roofed.top - rng.uniform(0, 1)
    # A valley's ring, ragged, and a hill that takes the afternoon: both reach
    # well above the altitude the model stops counting at.
    rings = np.array([[rng.uniform(0, 15) for _ in range(360)], [0.0] * 180 + [20.0] * 180])
    sky = np.array([[rng.choice([-1, 0, 1]) for _ in xs] for _ in ys])
    return Cells(xs=xs, ys=ys, cell_m=CELL, z=z, owner=owner, sky=sky, rings=rings)


def _field_answer(obstacles: list[Obstacle], cells: Cells, month: int) -> np.ndarray:
    field = shadow_field(BERLIN, obstacles, ground_floor=float(cells.z.min()), month=month)
    skies = {i: field.moments_under(tuple(cells.rings[i])) for i in range(len(cells.rings))}
    skies[-1] = field.moments_under(None)
    out = np.zeros(cells.z.shape + (2,))
    for r, y in enumerate(cells.ys):
        for c, x in enumerate(cells.xs):
            owner = int(cells.owner[r, c])
            out[r, c] = field.halves_at(float(x), float(y), float(cells.z[r, c]),
                                        under=skies[int(cells.sky[r, c])],
                                        ignore=None if owner < 0 else owner)
    return out


def test_the_raster_answers_every_cell_as_the_field_does() -> None:
    sample = MINUTE_STEP / 60
    # April and October bare, May the first month in leaf.
    for seed, month in ((1, 4), (2, 5), (3, 10)):
        rng = random.Random(seed)
        obstacles = _garden(rng)
        cells = _cells(rng, obstacles)
        before, after = grid_hours(parts_of(obstacles), moments_for(BERLIN, month=month), cells)
        field = _field_answer(obstacles, cells, month)
        # Exactly, but for a sample that falls on a shadow's very edge.
        worst = max(np.abs(before - field[..., 0]).max(), np.abs(after - field[..., 1]).max())
        assert worst < sample / 3, (seed, month, worst)
        assert np.abs(before - field[..., 0]).mean() + np.abs(after - field[..., 1]).mean() < 1e-6


def test_one_point_answers_as_the_grid_does() -> None:
    for month in (5, 10):
        _point_as_grid(month)


def _point_as_grid(month: int) -> None:
    rng = random.Random(5)
    obstacles = _garden(rng)
    cells = _cells(rng, obstacles)
    moments = moments_for(BERLIN, month=month)
    parts = parts_of(obstacles)
    before, after = grid_hours(parts, moments, cells)
    for _ in range(40):
        r, c = rng.randrange(len(cells.ys)), rng.randrange(len(cells.xs))
        sky = int(cells.sky[r, c])
        owner = int(cells.owner[r, c])
        alone = point_hours(parts, moments, float(cells.xs[c]), float(cells.ys[r]),
                            float(cells.z[r, c]),
                            ring=None if sky < 0 else list(cells.rings[sky]),
                            owner=None if owner < 0 else owner)
        assert alone == (float(before[r, c]), float(after[r, c])) or np.allclose(
            alone, (before[r, c], after[r, c]), atol=1e-9)


def test_a_second_cell_costs_no_second_question(monkeypatch: pytest.MonkeyPatch) -> None:
    """A guard on the shape of the thing, carried over from the field (Wave
    16): a cell is a column of an array, so the shadow tests are one per part
    and moment however many cells there are. It was a timing ratio, which
    failed on a loaded machine (review, 2026-09-22); this counts."""
    obstacles = [Obstacle(footprint=[(10 + i, 7), (18 + i, 7), (18 + i, 13), (10 + i, 13)],
                          height=8.0) for i in range(12)]
    parts, moments = parts_of(obstacles), moments_for(BERLIN, month=6)
    calls = {"parts": 0, "tests": 0}
    shade, covered = raster_grid._shade, raster_grid.covered

    def asking(*args: Any, **kwargs: Any) -> None:
        calls["parts"] += 1
        shade(*args, **kwargs)

    def testing(*args: Any, **kwargs: Any) -> np.ndarray:
        calls["tests"] += 1
        return covered(*args, **kwargs)

    # The parts asked about per moment — the same box at either cell size —
    # and at most one test of all the cells for each.
    monkeypatch.setattr(raster_grid, "_shade", asking)
    monkeypatch.setattr(raster_grid, "covered", testing)
    asked = []
    for cell in (1.0, 0.5):
        calls.update(parts=0, tests=0)
        grid_hours(parts, moments, _flat(np.arange(-10.0 + cell / 2, 10.0, cell)))
        assert 0 < calls["tests"] <= calls["parts"]
        asked.append(calls["parts"])
    assert asked[0] == asked[1]


def _flat(xs: np.ndarray) -> Cells:
    n = len(xs)
    return Cells(xs=xs, ys=xs.copy(), cell_m=float(xs[1] - xs[0]), z=np.zeros((n, n)),
                 owner=np.full((n, n), -1), sky=np.full((n, n), -1), rings=np.empty((0, 360)))


def test_walls_drawn_as_lines_and_things_at_the_grids_edge_answer_as_the_field() -> None:
    """A hedge whose straight joints are bevelled into corners one bit apart,
    a wall with the editor's midpoint on it, a bent hedge (review, 2026-09-22:
    half of each cast no shadow) — and a shed just outside each edge of the
    grid, whose shadow reaches only its outermost row or column."""
    from ninanatur.garden.polyline import band_of

    lines = [
        band_of([(-7.1, -8.15), (-5.7, -5.35), (-4.7, -3.35), (-3.1, -0.15), (-1.3, 3.45)],
                width=0.5),
        band_of([(0.0, 0.0), (2.65, 3.82), (5.3, 7.64)], width=0.3),
        band_of([(4.95, 0.67), (7.83, -0.05), (8.95, -0.33), (9.07, 0.15), (9.47, 1.75)],
                width=0.5),
    ]
    sheds = [[(x0, y0), (x0 + 1.5, y0), (x0 + 1.5, y0 + 1.5), (x0, y0 + 1.5)]
             for x0, y0 in ((10.2, -1.0), (-11.7, -1.0), (-1.0, 10.2), (-1.0, -11.7))]
    obstacles = [Obstacle(footprint=o, height=2.0, owner=i)
                 for i, o in enumerate([*lines, *sheds])]
    cells = _flat(np.arange(-9.5, 10.0, 1.0))
    before, after = grid_hours(parts_of(obstacles), moments_for(BERLIN, month=6), cells)
    field = _field_answer(obstacles, cells, 6)
    worst = max(np.abs(before - field[..., 0]).max(), np.abs(after - field[..., 1]).max())
    assert worst < MINUTE_STEP / 60 / 3, worst
