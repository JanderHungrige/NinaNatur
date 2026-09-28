"""Print what crowns cost the light grid against what its estimate says (doc 121).

    python -m scripts.measure_crown_cost

Drawn trees 8 m across and 12 m tall, in Wuppertal: 12 and 36 of them on a
94 m plot, at forced cells from 2 m to 0.5 m; 24 round the plot, 6 to 30 m
outside it, where a crown throws its shadow in at most moments; and 12 beside
a gabled house, and 12 on a slope, where every crown's box of cells is
stretched by the height between the grid's lowest cell and its highest
(review of stage 3, 2026-09-28) — as it is beside a flat or unshaped roof,
and not on level surveyed ground (review of 45eb56a); a garden as the map
makes it, on the level and on a slope; and an ordinary 24 × 40 m garden with
trees, a tall house and neighbours, where a price per cell of the grid fell
short (review of 596a89f). Each line gives the estimate
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
from ninanatur.garden.lightgrid_extent import (
    CELL_LADDER_M,
    GRID_BUDGET_S,
    MAX_CELLS,
    cells_at,
    grid_extent_of,
)
from ninanatur.garden.models import Element, Garden
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.shading import Obstacle

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


def typical() -> list[Element]:
    """An ordinary garden from the map, on the 25 × 40 m plot `TYPICAL`: its
    own gable, 30 neighbours scattered round it, 6 trees on the plot and 16
    found off it."""
    rng = random.Random(4)
    found = [Element(element_id=2, kind="house", shape="polygon", x=0.0, y=14.0, height=9.0,
                     points=[[-6, -4], [6, -4], [6, 4], [-6, 4]], roof="gable", eaves_m=5.5)]
    for i in range(30):
        while True:
            x, y = rng.uniform(-55, 55), rng.uniform(-60, 60)
            if abs(x) > 22 or abs(y) > 30:
                break
        found.append(Element(element_id=100 + i, kind="house", shape="polygon", x=x, y=y,
                             points=[[-5, -4], [5, -4], [5, 4], [-5, 4]],
                             height=rng.uniform(6, 11), height_source="osm",
                             roof=rng.choice(["gable", "hip", "unknown"]), roof_source="osm",
                             eaves_m=5.0, outline_source="osm"))
    for i in range(22):
        on = i < 6
        x = rng.uniform(-11, 11) if on else rng.uniform(-45, 45)
        y = rng.uniform(-18, 8) if on else rng.choice([-1, 1]) * rng.uniform(25, 50)
        found.append(Element(element_id=300 + i, kind="tree", shape="circle", x=x, y=y,
                             width=rng.uniform(4, 9), height=rng.uniform(6, 16),
                             height_source="user" if on else "measured"))
    return found


TYPICAL = [[-12.5, -20.0], [12.5, -20.0], [12.5, 20.0], [-12.5, 20.0]]


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


#: An ordinary garden: 24 × 40 m, a 34 × 50 m grid (review of 596a89f).
SMALL = [[-12.0, -20.0], [12.0, -20.0], [12.0, 20.0], [-12.0, 20.0]]


def small_garden(trees: int, roof: str, height: float, neighbours: int) -> list[Element]:
    """Trees 6 m across and 10 m tall on the small plot, a house at its north
    end, and neighbours from the map round it, 3 to 15 m past the grid."""
    rng = random.Random(trees + neighbours)
    found = [Element(element_id=9, kind="house", shape="polygon", x=0.0, y=0.0, height=height,
                     points=[[-5.0, 12.0], [5.0, 12.0], [5.0, 19.0], [-5.0, 19.0]], roof=roof)]
    found += [Element(element_id=50 + i, kind="tree", shape="circle", x=-8 + 5.3 * (i % 4),
                      y=-14 + 7 * (i // 4), width=6.0, height=10.0) for i in range(trees)]
    for i in range(neighbours):
        gap = rng.uniform(3.0, 15.0) + 4.0
        side = [(rng.uniform(-17, 17), 25 + gap), (rng.uniform(-17, 17), -25 - gap),
                (17 + gap, rng.uniform(-25, 25)), (-17 - gap, rng.uniform(-25, 25))][i % 4]
        found.append(Element(element_id=100 + i, kind="house", shape="polygon", x=side[0],
                             y=side[1], points=[[-4, -4], [4, -4], [4, 4], [-4, 4]],
                             height=rng.uniform(6, 11), height_source="osm", roof="gable",
                             roof_source="osm", eaves_m=5.0, outline_source="osm"))
    return found


def _garden(trees: list[Element],
            outline: list[list[float]] | None) -> tuple[Garden, list[Obstacle]]:
    plot = Element(element_id=1, kind="garden", shape="polygon", x=0.0, y=0.0,
                   points=outline or PLOT)
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="g", latitude=LAT,
                    longitude=LON, created_at="", updated_at="", elements=[plot, *trees])
    return garden, lightview.shading_obstacles(None, garden)  # type: ignore[arg-type]


def ladder_pick(trees: list[Element], ground: TerrainWindow | None = None,
                outline: list[list[float]] | None = None) -> float:
    """The cell the ladder gives this garden: the finest its estimate affords."""
    garden, obstacles = _garden(trees, outline)
    box = grid_extent_of(garden)
    assert box is not None
    for cell in CELL_LADDER_M:
        cells = cells_at(max(box[2] - box[0], 1.0), max(box[3] - box[1], 1.0), cell)
        if cells <= MAX_CELLS and grid_cost(garden, obstacles, cell, ground) <= GRID_BUDGET_S * 1e3:
            return cell
    return CELL_LADDER_M[-1]


def measure(trees: list[Element], cell: float, ground: TerrainWindow | None = None,
            outline: list[list[float]] | None = None) -> tuple[float, float]:
    """(estimate, measured) in milliseconds."""
    garden, obstacles = _garden(trees, outline)
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
              ("the 94 m plot as the map fills it", from_the_map(), None),
              ("the 94 m plot as the map fills it, on a slope", from_the_map(), slope())]
    small = [("24 × 40 m: 10 trees, a flat 9 m house", small_garden(10, "flat", 9.0, 0)),
             ("24 × 40 m: 16 trees, a 15 m house of no known shape",
              small_garden(16, "unknown", 15.0, 0)),
             ("24 × 40 m: 20 trees, a 15 m house, 15 neighbours",
              small_garden(20, "unknown", 15.0, 15)),
             ("24 × 40 m: 20 trees, an 18 m house, 20 neighbours",
              small_garden(20, "unknown", 18.0, 20))]
    runs: list[tuple[str, list[Element], TerrainWindow | None, list[list[float]] | None]] = [
        (name, trees, ground, None) for name, trees, ground in cases]
    runs += [(name, trees, None, SMALL) for name, trees in small]
    runs += [("an ordinary 25 × 40 m garden from the map", typical(), None, TYPICAL)]
    for name, trees, ground, outline in runs:
        print(f"{name}: the ladder picks {ladder_pick(trees, ground, outline)} m", flush=True)
        for cell in (2.0, 1.0, 0.5):
            estimate, took = measure(trees, cell, ground, outline)
            verdict = "held" if estimate >= took else "UNDER THE ESTIMATE"
            print(f"{name}, {cell} m cells: estimate {estimate:6.0f} ms, "
                  f"took {took:6.0f} ms — {verdict}", flush=True)


if __name__ == "__main__":
    main()
