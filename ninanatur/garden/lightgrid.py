"""Sun hours across the whole garden, cell by cell.

The light model has answered at one point per bed — the polygon's centroid — so
a bed whose northern half sits in the house's shadow all day reported one number
from its middle. There was nothing to draw a map from and nothing to place a
plant by.

A grid is the same computation asked at many points, which only became
affordable once `solar/field.py` stopped redoing the sun and the shadows for
every one of them.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ninanatur.garden.ground import lowest_ground, standing_on
from ninanatur.garden.lightcells import answer_at, roofs_of
from ninanatur.garden.models import Garden
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.field import ShadowAt, ShadowField, shadow_field
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle

#: Cell sizes to choose from, finest first. A garden is measured in metres and a
#: gardener thinks in them; anything below half a metre says more than the model
#: knows, given that most building heights are assumed and a roof pitch is
#: inferred from a rectangle.
CELL_LADDER_M: tuple[float, ...] = (0.5, 1.0, 2.0, 3.0, 5.0)

#: Seconds the recompute may spend on the grid.
#:
#: It was a flat cap of 600 cells, chosen when every write recomputed the light
#: and half a second was the whole budget. Nothing recomputes on a write any
#: more — it happens when somebody presses a button knowing it will take a
#: moment — so the limit can be what it should always have been: a time, not a
#: count.
#:
#: A count was the wrong shape anyway, because a cell is not a fixed price. It
#: costs what the obstacles around it cost. Measured on 2026-09-07: 0.24 ms in a
#: garden with three buildings and 1.9 ms in one with forty, which a single
#: number has to be wrong about at one end or the other. At 600 cells a small
#: garden waited 0.16 s for a 1 m grid it did not need to be that coarse.
GRID_BUDGET_S = 5.0

#: The straight line those measurements sit on: a fixed cost per cell, plus what
#: each obstacle adds to it. Rounded from 0.105 and 0.045 ms.
CELL_COST_MS = 0.1
OBSTACLE_COST_MS = 0.05


@dataclass(frozen=True)
class LightGrid:
    """Mean daily sun hours per cell, row-major from the south-west corner."""

    min_x: float
    min_y: float
    cell_m: float
    cols: int
    rows: int
    #: None only where nothing can be answered: a building whose height nobody
    #: has recorded, which the shading model has skipped since Wave 8.
    #:
    #: A cell under a house is **not** null. It is answered on the roof, which
    #: is the surface anything looking down at a plan can see, and which at
    #: 51°N is a very different place on its north pitch than on its south. It
    #: used to be answered on the ground under the building — where the sun
    #: never reaches, all day, every day — and painted as deep shade.
    hours: list[float | None]
    #: Of those hours, the ones before the sun crosses due south. Kept because
    #: afternoon sun is hotter and harsher, and a great many species sold as
    #: *Halbschatten* want the morning specifically — a total cannot say which
    #: four hours a spot gets.
    morning: list[float | None] = field(default_factory=list)
    #: Which cells are a roof rather than ground, in step with `hours`. Empty on
    #: a grid computed before roofs were; the next rebuild fills it.
    #:
    #: Kept apart from the hours instead of folded into them, because a roof's
    #: sun is a real answer to a different question: it is not where anything is
    #: planted, so it must not reach a bed's mean or the garden's brightest
    #: point, and the reader is told which one they are hovering.
    roof: list[bool] = field(default_factory=list)

    def at(self, x: float, y: float) -> float | None:
        """The cell containing this point.

        None outside the grid, and None for a cell that is under a roof — the
        caller cannot tell the two apart and does not need to, because both mean
        "this model has no answer for that point".
        """
        col = int((x - self.min_x) // self.cell_m)
        row = int((y - self.min_y) // self.cell_m)
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return None
        return self.hours[row * self.cols + col]

    def is_roof(self, index: int) -> bool:
        """Whether this cell is a roof. False on a grid computed before roofs."""
        return index < len(self.roof) and self.roof[index]

    def centre_of(self, col: int, row: int) -> tuple[float, float]:
        return (
            self.min_x + (col + 0.5) * self.cell_m,
            self.min_y + (row + 0.5) * self.cell_m,
        )

    def mean_over(self, polygon: list[list[float]]) -> float | None:
        """The mean of the cells whose centres fall inside a polygon.

        None when no cell centre lands inside — a bed narrower than a cell — and
        None when every cell that does land inside is under a roof. The caller
        falls back rather than being handed a zero, because zero is a number
        this model uses for genuine darkness.
        """
        from ninanatur.garden.footprint import covers

        ring = [(float(p[0]), float(p[1])) for p in polygon]
        inside = [
            hours
            for row in range(self.rows)
            for col in range(self.cols)
            if covers(ring, self.centre_of(col, row))
            and not self.is_roof(row * self.cols + col)
            and (hours := self.hours[row * self.cols + col]) is not None
        ]
        return sum(inside) / len(inside) if inside else None


class GardenTooLarge(ValueError):
    """A garden whose light grid cannot be computed in any reasonable time.

    A ValueError, so the API's one backstop turns it into a 422 with its reason
    rather than a 500 — or, as before this existed, no answer at all.
    """


#: How far past the grid budget a garden may go before it is refused outright.
#: `cell_size_for` stops at its coarsest cell and simply runs long beyond that;
#: a little over is a slow button, far over is a request that never returns.
REFUSE_AT_BUDGET_MULTIPLE = 4.0


def check_extent(
    min_x: float, min_y: float, max_x: float, max_y: float, obstacles: int = 0
) -> None:
    """Refuse a garden whose grid would take far longer than the budget allows.

    The second line of defence, behind the API's coordinate bounds. It asks the
    same question `cell_size_for` does — cells times the measured cost of each —
    at the coarsest cell the ladder has, so the limit is the budget rather than
    a second number somebody has to keep in step with it.

    Reproduced before it existed: one obstacle at x = 1e9 made the grid a
    billion metres wide, and `POST /light` did not come back.
    """
    width = max(max_x - min_x, 1.0)
    depth = max(max_y - min_y, 1.0)
    coarsest = CELL_LADDER_M[-1]
    cells = (width / coarsest + 1) * (depth / coarsest + 1)
    seconds = cells * (CELL_COST_MS + OBSTACLE_COST_MS * obstacles) / 1000
    if seconds > GRID_BUDGET_S * REFUSE_AT_BUDGET_MULTIPLE:
        raise GardenTooLarge(
            f"Garten zu groß: {width:.0f} × {depth:.0f} m lassen sich nicht in "
            f"vertretbarer Zeit berechnen"
        )


def cell_size_for(width_m: float, depth_m: float, obstacles: int = 0) -> float:
    """The finest cell that keeps the recompute inside `GRID_BUDGET_S`.

    A small garden with three buildings gets 0.5 m and takes half a second; a
    150 m street with forty gets 3 m and takes four and a half. Both are the
    finest grid that fits the same budget, which is the point of asking about
    time rather than about a cell count.
    """
    allowed = GRID_BUDGET_S * 1000 / (CELL_COST_MS + OBSTACLE_COST_MS * obstacles)
    for cell in CELL_LADDER_M:
        if (width_m / cell) * (depth_m / cell) <= allowed:
            return cell
    return CELL_LADDER_M[-1]


def extent_of(garden: Garden) -> tuple[float, float, float, float] | None:
    """(min_x, min_y, max_x, max_y) over everything drawn, or None if nothing is.

    Everything, not only the beds: the ground between them is where somebody
    decides to put the next one, and a map that stops at the bed edges cannot
    help with that.
    """
    points: list[tuple[float, float]] = []
    for element in list(garden.beds) + list(garden.obstacles):
        points.extend(element.footprint)
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def compute_grid(
    garden: Garden,
    obstacles: list[Obstacle],
    year: int = 2026,
    height_above_ground: float = 0.0,
    ground: TerrainWindow | None = None,
    horizon: list[float] | None = None,
    month: int | None = None,
) -> LightGrid | None:
    """Sun hours for every cell of the garden. None when nothing is drawn yet.

    `month` narrows the average from the whole March-to-October season to one
    month. A garden with a house on its south side is a different garden in
    April and in July, and one number for the season says neither.

    `ground` is the terrain under the garden, or None for the flat world every
    shadow in this project was computed in until Wave 17. With it, each cell is
    asked about at its own height and each obstacle stands on the ground beneath
    its footprint — so a neighbour's house uphill shades more than one on the
    level, and one downhill shades less.

    `horizon` is the ring from `geo/horizon.py`: what the land does beyond the
    plot. In flat country it changes nothing, because the ring sits below the
    5° altitude the model already stops counting at. In a valley it decides
    whether the garden sees December at all.
    """
    box = extent_of(garden)
    if box is None:
        return None
    min_x, min_y, max_x, max_y = box
    check_extent(min_x, min_y, max_x, max_y, len(obstacles))
    width = max(max_x - min_x, 1.0)
    depth = max(max_y - min_y, 1.0)
    cell = cell_size_for(width, depth, len(obstacles))
    cols = max(1, int(width / cell) + 1)
    rows = max(1, int(depth / cell) + 1)

    standing = standing_on(obstacles, ground)
    floor = lowest_ground(ground, min_x, min_y, cell, cols, rows)
    field_of: ShadowField = shadow_field(
        Location(latitude=garden.latitude, longitude=garden.longitude),
        standing,
        year=year,
        height_above_ground=height_above_ground,
        ground_floor=floor,
        horizon=horizon,
        month=month,
    )
    grid = LightGrid(
        min_x=min_x, min_y=min_y, cell_m=cell, cols=cols, rows=rows, hours=[]
    )
    skies: dict[tuple[float, ...], list[tuple[list[ShadowAt], bool]]] = {}
    roofs = roofs_of(garden, ground)
    answers = [
        answer_at(field_of, grid.centre_of(col, row), ground, horizon, floor,
                  skies, roofs)
        for row in range(rows)
        for col in range(cols)
    ]
    return LightGrid(
        min_x=min_x, min_y=min_y, cell_m=cell, cols=cols, rows=rows,
        hours=[None if a.halves is None else round(sum(a.halves), 2) for a in answers],
        morning=[None if a.halves is None else round(a.halves[0], 2) for a in answers],
        roof=[a.on_a_roof for a in answers],
    )


def signature_of(garden: Garden) -> str:
    """A hash of everything that changes where the shadows fall.

    **Not a list of actions that ought to trigger a recomputation.** That was the
    first design and it is the wrong shape: such a list has to be extended by
    hand whenever a feature arrives, and forgetting is silent — a stale map that
    looks right. This is a fact about the inputs instead, so a new feature
    cannot forget to declare itself.

    What is in it: where the garden is, and every obstacle's kind, height, roof
    and outline, and every planting's species and position. What is deliberately
    not: names, labels, colours, soil, bed membership — none of them move a
    shadow.
    """
    parts: list[str] = [f"{garden.latitude:.5f},{garden.longitude:.5f}"]
    for element in sorted(
        list(garden.beds) + list(garden.obstacles), key=lambda e: e.element_id
    ):
        outline = ";".join(f"{x:.2f},{y:.2f}" for x, y in element.footprint)
        parts.append(
            f"{element.element_id}|{element.kind}|{element.height}"
            f"|{element.roof}|{element.eaves_m}"
            f"|{element.height_above_ground}|{outline}"
        )
        for planting in element.plantings:
            parts.append(
                f"p{planting.planting_id}|{planting.taxon_id}|{planting.quantity}"
                f"|{planting.x}|{planting.y}"
            )
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]
