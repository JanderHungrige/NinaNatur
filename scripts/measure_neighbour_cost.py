"""Print what neighbours just off the grid cost against what its estimate says.

    python -m scripts.measure_neighbour_cost

36 houses from the map, 12 × 8 m with a 9 m ridge, nine to a side round a
94 m plot in Wuppertal — as blocks and as gables — in three rings: their near
walls 1 to 9 m outside the grid's box, 11 to 19 m, and 25 to 33 m. A
neighbour within its own height of the edge throws its shadow in whenever the
sun is below 45°, most of a season, where the far price assumed only the long
shadows of low suns did (review of feature 5, 2026-09-28). At forced cells from 5 m to
0.5 m; each line gives the estimate (`lightgrid_cost.estimate_ms`) and the
best of two runs. Timings are this machine's; what must hold anywhere is that
the estimate is the larger. A few minutes.
"""
from __future__ import annotations

import time

from ninanatur.garden import lightview
from ninanatur.garden.lightgrid import compute_grid, grid_cost
from ninanatur.garden.models import Element, Garden
from scripts.measure_crown_cost import LAT, LON, PLOT, forced

#: The grid's box: the plot and its 5 m margin.
EDGE = 52.0


def ring(nearest: float, roof: str) -> list[Element]:
    """36 houses, their walls nearest the grid `nearest` to `nearest` + 8 m
    outside its box, stepping 2 m from one to the next."""
    houses: list[Element] = []
    for i in range(36):
        side, place = divmod(i, 9)
        gap = nearest + 2.0 * (place % 5)
        along = -48.0 + 12.0 * place
        out = EDGE + gap + 4.0
        x, y = [(along, out), (along, -out), (out, along), (-out, along)][side]
        long_way = [[-6.0, -4.0], [6.0, -4.0], [6.0, 4.0], [-6.0, 4.0]]
        points = long_way if side < 2 else [[q[1], q[0]] for q in long_way]
        houses.append(Element(element_id=100 + i, kind="house", shape="polygon", x=x, y=y,
                              points=points, height=9.0, height_source="osm", roof=roof,
                              roof_source="osm", eaves_m=5.0, outline_source="osm"))
    return houses


def measure(houses: list[Element], cell: float) -> tuple[float, float]:
    """(estimate, measured) in milliseconds."""
    plot = Element(element_id=1, kind="garden", shape="polygon", x=0.0, y=0.0, points=PLOT)
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="g", latitude=LAT,
                    longitude=LON, created_at="", updated_at="", elements=[plot, *houses])
    obstacles = lightview.shading_obstacles(None, garden)  # type: ignore[arg-type]
    best = float("inf")
    with forced(cell):
        for _ in range(2):
            start = time.perf_counter()
            compute_grid(garden, obstacles)
            best = min(best, (time.perf_counter() - start) * 1000)
    return grid_cost(garden, obstacles, cell), best


def main() -> None:
    for nearest in (1.0, 11.0, 25.0):
        for roof in ("flat", "gable"):
            houses = ring(nearest, roof)
            for cell in (5.0, 2.0, 1.0, 0.5):
                estimate, took = measure(houses, cell)
                verdict = "held" if estimate >= took else "UNDER THE ESTIMATE"
                print(f"36 {roof} houses {nearest:.0f}–{nearest + 8:.0f} m out, {cell} m cells: "
                      f"estimate {estimate:6.0f} ms, took {took:6.0f} ms — {verdict}",
                      flush=True)


if __name__ == "__main__":
    main()
