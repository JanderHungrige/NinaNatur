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
import json
import sqlite3
from dataclasses import dataclass, field

from ninanatur.garden.ground import height_at, lowest_ground, standing_on
from ninanatur.garden.models import Garden
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.field import ShadowField, shadow_field
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle

#: Cell sizes to choose from, finest first. A garden is measured in metres and a
#: gardener thinks in them; anything below half a metre says more than the model
#: knows, given that most building heights are assumed.
CELL_LADDER_M: tuple[float, ...] = (0.5, 1.0, 2.0, 3.0, 5.0)

#: Roughly what fits in half a second. 600 cells at 1.09 ms is 0.65 s, and the
#: whole point of the ladder is that a large plot gets a coarser grid rather
#: than a long wait.
MAX_CELLS = 600


@dataclass(frozen=True)
class LightGrid:
    """Mean daily sun hours per cell, row-major from the south-west corner."""

    min_x: float
    min_y: float
    cell_m: float
    cols: int
    rows: int
    hours: list[float]
    #: Of those hours, the ones before the sun crosses due south. Kept because
    #: afternoon sun is hotter and harsher, and a great many species sold as
    #: *Halbschatten* want the morning specifically — a total cannot say which
    #: four hours a spot gets.
    morning: list[float] = field(default_factory=list)

    def at(self, x: float, y: float) -> float | None:
        """The cell containing this point, or None outside the grid."""
        col = int((x - self.min_x) // self.cell_m)
        row = int((y - self.min_y) // self.cell_m)
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return None
        return self.hours[row * self.cols + col]

    def centre_of(self, col: int, row: int) -> tuple[float, float]:
        return (
            self.min_x + (col + 0.5) * self.cell_m,
            self.min_y + (row + 0.5) * self.cell_m,
        )

    def mean_over(self, polygon: list[list[float]]) -> float | None:
        """The mean of the cells whose centres fall inside a polygon.

        None when no cell centre lands inside — a bed narrower than a cell. The
        caller falls back rather than being handed a zero, because zero is a
        number this model uses for genuine darkness.
        """
        from ninanatur.garden.footprint import covers

        ring = [(float(p[0]), float(p[1])) for p in polygon]
        inside = [
            self.hours[row * self.cols + col]
            for row in range(self.rows)
            for col in range(self.cols)
            if covers(ring, self.centre_of(col, row))
        ]
        return sum(inside) / len(inside) if inside else None


def cell_size_for(width_m: float, depth_m: float) -> float:
    """The finest cell that keeps the grid under `MAX_CELLS`.

    A 40 x 60 m plot at 1 m is 2,400 cells and 2.7 seconds, which is too long to
    wait after nudging a shed. It gets 3 m instead, and says so.
    """
    for cell in CELL_LADDER_M:
        if (width_m / cell) * (depth_m / cell) <= MAX_CELLS:
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
) -> LightGrid | None:
    """Sun hours for every cell of the garden. None when nothing is drawn yet.

    `ground` is the terrain under the garden, or None for the flat world every
    shadow in this project was computed in until Wave 17. With it, each cell is
    asked about at its own height and each obstacle stands on the ground beneath
    its footprint — so a neighbour's house uphill shades more than one on the
    level, and one downhill shades less.
    """
    box = extent_of(garden)
    if box is None:
        return None
    min_x, min_y, max_x, max_y = box
    width = max(max_x - min_x, 1.0)
    depth = max(max_y - min_y, 1.0)
    cell = cell_size_for(width, depth)
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
    )
    grid = LightGrid(
        min_x=min_x, min_y=min_y, cell_m=cell, cols=cols, rows=rows, hours=[]
    )
    halves = [
        field_of.halves_at(
            *grid.centre_of(col, row), height_at(ground, *grid.centre_of(col, row), floor)
        )
        for row in range(rows)
        for col in range(cols)
    ]
    return LightGrid(
        min_x=min_x, min_y=min_y, cell_m=cell, cols=cols, rows=rows,
        hours=[round(a + b, 2) for a, b in halves],
        morning=[round(a, 2) for a, _b in halves],
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


def save_grid(
    conn: sqlite3.Connection, garden_id: int, grid: LightGrid, signature: str
) -> None:
    from ninanatur.garden.elements import now

    conn.execute(
        "INSERT INTO light_grid (garden_id, cell_m, min_x, min_y, cols, rows,"
        " hours, morning, signature, computed_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (garden_id) DO UPDATE SET cell_m = excluded.cell_m,"
        " min_x = excluded.min_x, min_y = excluded.min_y, cols = excluded.cols,"
        " rows = excluded.rows, hours = excluded.hours,"
        " morning = excluded.morning,"
        " signature = excluded.signature, computed_at = excluded.computed_at",
        (garden_id, grid.cell_m, grid.min_x, grid.min_y, grid.cols, grid.rows,
         json.dumps(grid.hours), json.dumps(grid.morning), signature, now()),
    )
    conn.commit()


def load_grid(
    conn: sqlite3.Connection, garden_id: int
) -> tuple[LightGrid, str, str] | None:
    """The stored grid, its signature and when it was computed."""
    row = conn.execute(
        "SELECT cell_m, min_x, min_y, cols, rows, hours, morning, signature,"
        " computed_at"
        " FROM light_grid WHERE garden_id = ?",
        (garden_id,),
    ).fetchone()
    if row is None:
        return None
    grid = LightGrid(
        min_x=float(row["min_x"]), min_y=float(row["min_y"]),
        cell_m=float(row["cell_m"]), cols=int(row["cols"]), rows=int(row["rows"]),
        hours=[float(v) for v in json.loads(row["hours"])],
        morning=[float(v) for v in json.loads(row["morning"] or "[]")],
    )
    return grid, str(row["signature"]), str(row["computed_at"])
