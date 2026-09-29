"""The light grid itself: mean daily sun hours per cell, and what goes with them.

Split out of `lightgrid.py` when Wave 26's feature 3 gave every cell a sky
share, a relative illuminance and expected hours, and the file passed its
length. `lightgrid` computes the grid; this is what it computes and how a bed
reads it. Imported from `lightgrid`, as it always was.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


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
    #: The light model that computed it (`solar.light.MODEL_VERSION`); empty on
    #: a map computed before Wave 26 gave the model a version.
    model: str = ""
    #: Since Wave 26's feature 3 (doc 118), in step with `hours` and empty on a
    #: map computed before: the share of the sky each cell sees with the crowns
    #: in leaf, its relative illuminance (its light as a share of open
    #: ground's, sun and sky, in the garden's climate), and the hours of
    #: sunshine it can expect, cloud included.
    sky: list[float | None] = field(default_factory=list)
    relative: list[float | None] = field(default_factory=list)
    expected: list[float | None] = field(default_factory=list)

    def at(self, x: float, y: float,
           values: list[float | None] | None = None) -> float | None:
        """The cell containing this point — its hours, or its value in another
        list in step with them (`sky`, `relative`).

        None outside the grid, and None for a cell that is under a roof — the
        caller cannot tell the two apart and does not need to, because both mean
        "this model has no answer for that point". None too from a list the
        grid does not have: a map computed before the sky counted.
        """
        read = self.hours if values is None else values
        col = int((x - self.min_x) // self.cell_m)
        row = int((y - self.min_y) // self.cell_m)
        if not (0 <= col < self.cols and 0 <= row < self.rows) or len(read) != len(self.hours):
            return None
        index = row * self.cols + col
        # As the docstring always said, and the code did not: a plant beside a
        # house was judged by the sun on its roof (review, 2026-09-21).
        return None if self.is_roof(index) else read[index]

    def centre_at(self, x: float, y: float) -> tuple[float, float] | None:
        """The centre of the cell containing this point; None outside the grid."""
        col = int((x - self.min_x) // self.cell_m)
        row = int((y - self.min_y) // self.cell_m)
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return None
        return self.centre_of(col, row)

    def is_roof(self, index: int) -> bool:
        """Whether this cell is a roof. False on a grid computed before roofs."""
        return index < len(self.roof) and self.roof[index]

    def centre_of(self, col: int, row: int) -> tuple[float, float]:
        return (
            self.min_x + (col + 0.5) * self.cell_m,
            self.min_y + (row + 0.5) * self.cell_m,
        )

    def mean_over(self, polygon: list[list[float]],
                  values: list[float | None] | None = None) -> float | None:
        """The mean of the cells whose centres fall inside a polygon — of the
        hours, or of another list in step with them (`sky`, `relative`).

        None when no cell centre lands inside — a bed narrower than a cell — and
        None when every cell that does land inside is under a roof. The caller
        falls back rather than being handed a zero, because zero is a number
        this model uses for genuine darkness.
        """
        from ninanatur.garden.footprint import covers

        read = self.hours if values is None else values
        ring = [(float(p[0]), float(p[1])) for p in polygon]
        if len(ring) < 3 or len(read) != len(self.hours):
            return None  # `covers` holds nothing inside fewer than three corners
        cols, rows = self._cells_near(ring)
        inside = [
            value
            for row in rows
            for col in cols
            if covers(ring, self.centre_of(col, row))
            and not self.is_roof(row * self.cols + col)
            and (value := read[row * self.cols + col]) is not None
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


__all__ = ["LightGrid"]
