"""Print what crowns cost the light grid against what its estimate says (doc 121).

    python -m scripts.measure_crown_cost

Drawn trees 8 m across and 12 m tall, in Wuppertal: 12 and 36 of them on a
94 m plot, at forced cells from 2 m to 0.5 m; and 24 round the plot, 6 to
30 m outside it, where a crown throws its shadow in at most moments. Each line
gives the estimate (`lightgrid_cost.estimate_ms`) and the best of two runs.
Timings are this machine's; what must hold anywhere is that the estimate is
the larger. A few minutes.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from ninanatur.garden import lightgrid, lightview
from ninanatur.garden.ground import standing_on
from ninanatur.garden.lightgrid import compute_grid
from ninanatur.garden.lightgrid_cost import estimate_ms
from ninanatur.garden.lightgrid_extent import cells_at, grid_extent_of, stands_in
from ninanatur.garden.models import Element, Garden
from ninanatur.solar.raster import parts_of

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


def measure(trees: list[Element], cell: float) -> tuple[float, float]:
    """(estimate, measured) in milliseconds."""
    plot = Element(element_id=1, kind="garden", shape="polygon", x=0.0, y=0.0, points=PLOT)
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="g", latitude=LAT,
                    longitude=LON, created_at="", updated_at="", elements=[plot, *trees])
    obstacles = lightview.shading_obstacles(None, garden)  # type: ignore[arg-type]
    best = float("inf")
    with forced(cell):
        for _ in range(2):
            start = time.perf_counter()
            compute_grid(garden, obstacles)
            best = min(best, (time.perf_counter() - start) * 1000)
    box = grid_extent_of(garden)
    assert box is not None
    parts = parts_of(standing_on(obstacles, None))
    on = [stands_in([(float(x), float(y)) for x, y in p.corners], box) for p in parts]
    far_crowns = sum(1 for p, o in zip(parts, on, strict=True) if not o and p.crown is not None)
    cells = cells_at(max(box[2] - box[0], 1.0), max(box[3] - box[1], 1.0), cell)
    return estimate_ms(cells, len(parts), sum(on), False, True, False,
                       far_crowns=far_crowns), best


def main() -> None:
    cases = [(f"{n} trees on the plot", on_the_plot(n)) for n in (12, 36)]
    cases += [(f"24 trees {out:.0f} m outside it", round_the_plot(out))
              for out in (6.0, 12.0, 20.0, 30.0)]
    for name, trees in cases:
        for cell in (2.0, 1.0, 0.5):
            estimate, took = measure(trees, cell)
            verdict = "held" if estimate >= took else "UNDER THE ESTIMATE"
            print(f"{name}, {cell} m cells: estimate {estimate:6.0f} ms, "
                  f"took {took:6.0f} ms — {verdict}", flush=True)


if __name__ == "__main__":
    main()
