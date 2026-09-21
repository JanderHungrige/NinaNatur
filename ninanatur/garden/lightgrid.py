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
import math
from dataclasses import dataclass, field

from ninanatur.garden.ground import lowest_ground, standing_on
from ninanatur.garden.lightcells import answer_at, roofs_of

# The box and the cell size live in `lightgrid_extent` since 2026-09-21. The
# names are re-exported because this is where every caller has imported them.
from ninanatur.garden.lightgrid_extent import CELL_COST_MS as CELL_COST_MS
from ninanatur.garden.lightgrid_extent import CELL_LADDER_M as CELL_LADDER_M
from ninanatur.garden.lightgrid_extent import GRID_BUDGET_S as GRID_BUDGET_S
from ninanatur.garden.lightgrid_extent import OBSTACLE_COST_MS as OBSTACLE_COST_MS
from ninanatur.garden.lightgrid_extent import GardenTooLarge as GardenTooLarge
from ninanatur.garden.lightgrid_extent import cell_size_for as cell_size_for
from ninanatur.garden.lightgrid_extent import check_extent as check_extent
from ninanatur.garden.lightgrid_extent import extent_of as extent_of
from ninanatur.garden.lightgrid_extent import grid_extent_of, grid_model
from ninanatur.garden.models import Garden
from ninanatur.geo.terrain import TerrainWindow
from ninanatur.solar.field import ShadowAt, ShadowField, shadow_field
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle


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
        if len(ring) < 3:
            return None  # `covers` holds nothing inside fewer than three corners
        cols, rows = self._cells_near(ring)
        inside = [
            hours
            for row in rows
            for col in cols
            if covers(ring, self.centre_of(col, row))
            and not self.is_roof(row * self.cols + col)
            and (hours := self.hours[row * self.cols + col]) is not None
        ]
        return sum(inside) / len(inside) if inside else None

    def _cells_near(self, ring: list[tuple[float, float]]) -> tuple[range, range]:
        """The columns and rows whose centres could fall inside this outline.

        Its bounding box, widened by a cell each way so a centre lying on the
        edge is still asked; `covers` decides, exactly as before. It only stops
        every cell of the garden being tested for every bed, which at 0.5 m over
        a whole plot is thousands of point-in-polygon tests per bed.
        """
        xs = [x for x, _ in ring]
        ys = [y for _, y in ring]
        if not all(math.isfinite(v) for v in xs + ys):
            return range(self.cols), range(self.rows)
        first_col = max(0, int((min(xs) - self.min_x) // self.cell_m) - 1)
        last_col = min(self.cols - 1, int((max(xs) - self.min_x) // self.cell_m) + 1)
        first_row = max(0, int((min(ys) - self.min_y) // self.cell_m) - 1)
        last_row = min(self.rows - 1, int((max(ys) - self.min_y) // self.cell_m) + 1)
        return range(first_col, last_col + 1), range(first_row, last_row + 1)


def compute_grid(
    garden: Garden,
    obstacles: list[Obstacle],
    year: int = 2026,
    height_above_ground: float = 0.0,
    ground: TerrainWindow | None = None,
    horizon: list[float] | None = None,
    month: int | None = None,
) -> LightGrid | None:
    """Sun hours for every cell of the garden. None when there is nothing to
    cover: nothing drawn, or only streets.

    The garden: its plot, its beds and what the gardener drew, with a margin —
    `grid_extent_of`. The neighbours' houses are in `obstacles` and cast their
    shadows into it; the ground under them is not computed.

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
    box = grid_extent_of(garden)
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


def signature_of(
    garden: Garden, ground: object = None, horizon: object = None,
    *, shading_taxa: frozenset[int] | None = None,
) -> str:
    """A hash of everything that changes where the shadows fall.

    **Not a list of actions that ought to trigger a recomputation.** That was the
    first design and it is the wrong shape: such a list has to be extended by
    hand whenever a feature arrives, and forgetting is silent — a stale map that
    looks right. This is a fact about the inputs instead, so a new feature
    cannot forget to declare itself.

    What is in it: where the garden is, and every obstacle's kind, height, roof
    and outline, and every planting that casts a shadow, by species and position
    (`shading_taxa`; without it, every planting) — and **what the
    ground and the horizon were measured from** (Wave 25, doc 106). A state that
    gains a source is the case this last part is for: Bayern had no terrain at
    all until its tiles were read, and a garden whose map was computed flat
    would otherwise have stayed flat for ever, quietly. What is deliberately
    not: names, labels, colours, soil, bed membership — none of them move a
    shadow.

    And the grid's own shape: the rule for what it covers, its margin, ladder
    and budget (`grid_model`), and the box it covers. A map laid over another
    box is out of date even where no shadow moved — which is how every map
    stored before 2026-09-21, laid over the neighbours' land in 3 m cells, now
    says so and offers the finer one. The box is here rather than implied by the
    outlines because it also reads where an element came from: a neighbour's
    house the gardener makes their own joins it.
    """
    box = grid_extent_of(garden)
    parts: list[str] = [
        f"{garden.latitude:.5f},{garden.longitude:.5f}",
        grid_model(),
        "box|" + ("" if box is None else ",".join(f"{v:.2f}" for v in box)),
    ]
    # Where the ground came from and how finely it was measured: a better source
    # for the same place is a different map.
    whose = getattr(ground, "source", None)
    step = getattr(ground, "vertical_step_m", None)
    parts.append(f"ground|{whose}|{step}")
    ring = list(horizon) if isinstance(horizon, list) else []
    parts.append("horizon|" + ",".join(f"{angle:.2f}" for angle in ring))
    for element in sorted(
        list(garden.beds) + list(garden.obstacles), key=lambda e: e.element_id
    ):
        outline = ";".join(f"{x:.2f},{y:.2f}" for x, y in element.footprint)
        parts.append(
            f"{element.element_id}|{element.kind}|{element.height}"
            f"|{element.roof}|{element.eaves_m}|{element.roof_fall_deg}"
            f"|{element.height_above_ground}|{outline}"
        )
        for planting in element.plantings:
            if shading_taxa is not None and planting.taxon_id not in shading_taxa:
                continue
            parts.append(
                f"p{planting.planting_id}|{planting.taxon_id}|{planting.quantity}"
                f"|{planting.x}|{planting.y}"
            )
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]
