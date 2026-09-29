"""A crown's cells at the heights under it — doc 121, review of stage 3.

The grid asks a crown about the cells under the ellipse it throws, a box
sized from the grid's lowest cell to its highest: one roof on the plot
stretches every crown's box towards the sun by the ridge's height, which the
estimate prices (`CROWN_RELIEF_CELL_MS`). Narrowing each box to the heights of
the cells it covers was tried and saved nothing (review of stage 3,
2026-09-28). Whichever way the box is sized, it must keep every cell the
crown's shadow reaches, and it is checked the way every crown path is: each
cell says what the point says — beside a roof the crown's shadow reaches,
and far from it.
"""
from __future__ import annotations

import math
import random

import numpy as np
import pytest

from ninanatur.solar.crown import Crown
from ninanatur.solar.raster import Directions, parts_of, point_sums
from ninanatur.solar.raster_grid import Cells, grid_sums
from ninanatur.solar.shading import Obstacle


def _crowned(crown: Crown) -> Obstacle:
    ring = [(crown.x + crown.radius * math.cos(a), crown.y + crown.radius * math.sin(a))
            for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    return Obstacle(footprint=ring, height=crown.top, transmission=0.2, bare_transmission=0.75,
                    crown=crown)


@pytest.mark.parametrize(("roof_z", "shaded"), [(9.0, True), (11.5, False)])
def test_a_crown_beside_a_roof_is_asked_about_every_cell_it_reaches(roof_z: float,
                                                                    shaded: bool) -> None:
    """A block of roof cells north of a tree, at its crown's height — where
    low suns from the south put the crown's shadow on it — or just under its
    top, where none can reach. Far from the roof, on the ground, a second
    crown's shadow falls too. Every cell answers what the point does: the
    box keeps them all."""
    near_roof = Crown(x=10.0, y=2.0, radius=3.0, base=3.0, top=12.0)
    far_away = Crown(x=-12.0, y=-12.0, radius=3.0, base=3.0, top=12.0)
    parts = parts_of([_crowned(near_roof), _crowned(far_away)])
    rng = random.Random(8)
    directions = Directions(
        azimuth=np.array([rng.uniform(150, 210) for _ in range(40)]),
        altitude=np.array([rng.uniform(8, 55) for _ in range(40)]),
        month=np.array([4, 8] * 20), weight=np.full(40, 1 / 40),
        group=np.zeros(40, dtype=int), groups=1)
    xs = np.arange(-20.0, 26.0, 1.0)
    z = np.zeros((len(xs), len(xs)))
    z[(xs >= 8)[:, None] & (xs <= 16)[:, None] & ((xs >= 6) & (xs <= 16))[None, :]] = roof_z
    cells = Cells(xs=xs, ys=xs.copy(), cell_m=1.0, z=z, owner=np.full(z.shape, -1),
                  sky=np.full(z.shape, -1), rings=np.empty((0, 360)))
    grid = grid_sums(parts, directions, cells)
    roof_rows = np.nonzero((xs >= 8) & (xs <= 16))[0]
    on_roof = float(grid[0][np.ix_(roof_rows, np.nonzero((xs >= 6) & (xs <= 16))[0])].min())
    assert (on_roof < 0.95) is shaded, on_roof
    for r in range(len(xs)):
        for c in range(len(xs)):
            point = point_sums(parts, directions, float(xs[c]), float(xs[r]), float(z[r, c]))
            assert float(grid[0, r, c]) == pytest.approx(float(point[0]), abs=1e-9), (r, c)
