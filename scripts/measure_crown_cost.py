"""Print what crowns cost the light grid against what its estimate says (doc 121).

    python -m scripts.measure_crown_cost

Drawn trees 8 m across and 12 m tall, in Wuppertal: 12 and 36 of them on a
94 m plot, at forced cells from 2 m to 0.5 m; 24 round the plot, 6 to 30 m
outside it, where a crown throws its shadow in at most moments; and 12 beside
a gabled house, and 12 on a slope, where every crown's box of cells is
stretched by the height between the grid's lowest cell and its highest
(review of stage 3, 2026-09-28) — as it is beside a flat or unshaped roof,
and not on level surveyed ground (review of 45eb56a); and a garden as the
map makes it, on the level and on a slope. Each line gives the estimate
(`lightgrid_cost.estimate_ms`) and the best of two runs. Timings are this
machine's; what must hold anywhere is that the estimate is the larger. A few
minutes.
"""
from __future__ import annotations

import random
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace

from ninanatur.garden import lightgrid, lightview
from ninanatur.garden.lightgrid import compute_grid, grid_cost
from ninanatur.garden.models import Element, Garden
from ninanatur.geo.terrain import TerrainWindow

LAT, LON = 51.2562, 7.1508
PLOT = [[-47.0, -47.0], [47.0, -47.0], [47.0, 47.0], [-47.0, 47.0]]


def _tree(number: int, x: float, y: float, source: str = "user") -> Element:
    return Element(element_id=10 + number, kind="tree", shape="circle", x=x, y=y, width=8.0,
                   height=12.0, height_source=source)


def on_the_plot(count: int) -> list[Element]:
    return [_tree(i, -40 + (i % 6) * 15, -40 + (i // 6) * 15) for i in range(count)]


def round_the_plot(out: float) -> list[Element]:
    """24 trees, six a side, their centres `out` metres outside the plot —
    taken from the laser, so the grid covers the garden and not their land
    (`grid_extent_of`)."""
    edge, trees = 47.0 + out, []
    for i in range(6):
        t = -40.0 + 16 * i
        trees += [(t, -edge), (t, edge), (-edge, t), (edge, t)]
    return [_tree(i, x, y, "measured") for i, (x, y) in enumerate(trees)]


@contextmanager
def forced(cell: float) -> Iterator[None]:
    """The grid at this cell, whatever the ladder would choose."""
    chosen, checked = lightgrid.cell_size_for, lightgrid.check_extent
    lightgrid.cell_size_for = lambda *_a, **_k: cell
    lightgrid.check_extent = lambda *_a, **_k: None
    try:
        yield
    finally:
        lightgrid.cell_size_for, lightgrid.check_extent = chosen, checked


def beside_a_house(roof: str = "gable", height: float = 9.0) -> list[Element]:
    """12 trees, and a house 10 × 8 m north of them: gabled with a 9 m ridge,
    or flat or of no known shape — whose roof raises the grid's highest cell
    as much as a gable's does (review of 45eb56a)."""
    house = Element(element_id=9, kind="house", shape="polygon", x=0.0, y=0.0, height=height,
                    points=[[-5.0, 10.0], [5.0, 10.0], [5.0, 18.0], [-5.0, 18.0]],
                    roof=roof, eaves_m=5.5 if roof == "gable" else None)
    return [house, *on_the_plot(12)]


def from_the_map() -> list[Element]:
    """A garden as the map makes it: its own gabled house on the plot, 30
    neighbours round it, 6 trees on the plot and 16 found round it."""
    rng = random.Random(4)
    own = Element(element_id=2, kind="house", shape="polygon", x=0.0, y=30.0, height=9.0,
                  points=[[-6, -4], [6, -4], [6, 4], [-6, 4]], roof="gable", eaves_m=5.5)
    found: list[Element] = [own]
    for i in range(30):
        x, y = rng.choice([(rng.uniform(-60, 60), rng.choice([-1, 1]) * rng.uniform(55, 70)),
                           (rng.choice([-1, 1]) * rng.uniform(55, 70), rng.uniform(-60, 60))])
        found.append(Element(element_id=100 + i, kind="house", shape="polygon", x=x, y=y,
                             points=[[-5, -4], [5, -4], [5, 4], [-5, 4]],
                             height=rng.uniform(6, 11), height_source="osm",
                             roof=rng.choice(["gable", "hip", "unknown"]), roof_source="osm",
                             eaves_m=5.0, outline_source="osm"))
    trees = on_the_plot(6) + round_the_plot(8.0)[:16]
    return found + [replace(tree, element_id=300 + i) for i, tree in enumerate(trees)]


def level() -> TerrainWindow:
    """Surveyed ground that is level, give or take 10 cm."""
    size, rng = 200, random.Random(2)
    return TerrainWindow(
        min_x=-100.0, min_y=-100.0, cell_m=1.0, cols=size, rows=size,
        heights=[100.0 + rng.uniform(-0.1, 0.1) for _ in range(size * size)],
        source="Test", licence="-", attribution="-", vertical_step_m=0.01)


def slope() -> TerrainWindow:
    """Ground rising 8 cm a metre to the north and 3 cm to the east."""
    size = 200
    return TerrainWindow(
        min_x=-100.0, min_y=-100.0, cell_m=1.0, cols=size, rows=size,
        heights=[100.0 + (r - size / 2) * 0.08 + (c - size / 2) * 0.03
                 for r in range(size) for c in range(size)],
        source="Test", licence="-", attribution="-", vertical_step_m=0.01)


def measure(trees: list[Element], cell: float,
            ground: TerrainWindow | None = None) -> tuple[float, float]:
    """(estimate, measured) in milliseconds."""
    plot = Element(element_id=1, kind="garden", shape="polygon", x=0.0, y=0.0, points=PLOT)
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="g", latitude=LAT,
                    longitude=LON, created_at="", updated_at="", elements=[plot, *trees])
    obstacles = lightview.shading_obstacles(None, garden)  # type: ignore[arg-type]
    best = float("inf")
    with forced(cell):
        for _ in range(2):
            start = time.perf_counter()
            compute_grid(garden, obstacles, ground=ground)
            best = min(best, (time.perf_counter() - start) * 1000)
    return grid_cost(garden, obstacles, cell, ground), best


def main() -> None:
    cases: list[tuple[str, list[Element], TerrainWindow | None]] = [
        (f"{n} trees on the plot", on_the_plot(n), None) for n in (12, 36)]
    cases += [(f"24 trees {out:.0f} m outside it", round_the_plot(out), None)
              for out in (6.0, 12.0, 20.0, 30.0)]
    cases += [("12 trees beside a gabled house", beside_a_house(), None),
              ("12 trees beside a flat 9 m house", beside_a_house("flat"), None),
              ("12 trees beside a 15 m house of no known shape",
               beside_a_house("unknown", 15.0), None),
              ("12 trees on a slope", on_the_plot(12), slope()),
              ("12 trees on level surveyed ground", on_the_plot(12), level()),
              ("a garden from the map", from_the_map(), None),
              ("a garden from the map on a slope", from_the_map(), slope())]
    for name, trees, ground in cases:
        for cell in (2.0, 1.0, 0.5):
            estimate, took = measure(trees, cell, ground)
            verdict = "held" if estimate >= took else "UNDER THE ESTIMATE"
            print(f"{name}, {cell} m cells: estimate {estimate:6.0f} ms, "
                  f"took {took:6.0f} ms — {verdict}", flush=True)


if __name__ == "__main__":
    main()
