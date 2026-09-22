"""Keeping a light grid, and reading it back.

Split out of `lightgrid.py` when the month view pushed that file past the length
limit. The same seam `terrain_store.py` uses, and for the same reason: the
arithmetic and the table it happens to be kept in are two different subjects,
and only one of them changes when a column does.
"""
from __future__ import annotations

import json
import sqlite3

from ninanatur.garden.lightgrid import LightGrid


def save_grid(
    conn: sqlite3.Connection, garden_id: int, grid: LightGrid, signature: str
) -> None:
    from ninanatur.garden.elements import now

    conn.execute(
        "INSERT INTO light_grid (garden_id, cell_m, min_x, min_y, cols, rows,"
        " hours, morning, roof, model, sky, relative, expected, signature, computed_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (garden_id) DO UPDATE SET cell_m = excluded.cell_m,"
        " min_x = excluded.min_x, min_y = excluded.min_y, cols = excluded.cols,"
        " rows = excluded.rows, hours = excluded.hours,"
        " morning = excluded.morning, roof = excluded.roof, model = excluded.model,"
        " sky = excluded.sky, relative = excluded.relative, expected = excluded.expected,"
        " signature = excluded.signature, computed_at = excluded.computed_at",
        (garden_id, grid.cell_m, grid.min_x, grid.min_y, grid.cols, grid.rows,
         json.dumps(grid.hours), json.dumps(grid.morning),
         json.dumps(grid.roof), grid.model, json.dumps(grid.sky), json.dumps(grid.relative),
         json.dumps(grid.expected), signature, now()),
    )
    conn.commit()


def shows_climate(conn: sqlite3.Connection, garden_id: int) -> bool:
    """Whether the garden's page can show a number the DWD's climate went into
    (doc 118): whenever it has a map. A month's map is computed on the spot,
    always with the climate, even beside a season map stored before the sky
    counted — so asking whether the stored map has a sky left the DWD
    uncredited under its own numbers (review, 2026-09-22)."""
    row = conn.execute("SELECT 1 FROM light_grid WHERE garden_id = ?",
                       (garden_id,)).fetchone()
    return row is not None


def _values(stored: str | None) -> list[float | None]:
    """A list in step with the hours, nulls kept: an unanswered cell is not 0."""
    return [None if v is None else float(v) for v in json.loads(stored or "[]")]


def load_grid(
    conn: sqlite3.Connection, garden_id: int
) -> tuple[LightGrid, str, str] | None:
    """The stored grid, its signature and when it was computed."""
    row = conn.execute(
        "SELECT cell_m, min_x, min_y, cols, rows, hours, morning, roof, model,"
        " sky, relative, expected,"
        " signature, computed_at"
        " FROM light_grid WHERE garden_id = ?",
        (garden_id,),
    ).fetchone()
    if row is None:
        return None
    grid = LightGrid(
        min_x=float(row["min_x"]), min_y=float(row["min_y"]),
        cell_m=float(row["cell_m"]), cols=int(row["cols"]), rows=int(row["rows"]),
        # Null survives the round trip: it is the answer for a cell under a roof,
        # and reading it back as 0.0 would be the deep-shade claim this grid
        # exists to stop making.
        hours=[None if v is None else float(v) for v in json.loads(row["hours"])],
        morning=[
            None if v is None else float(v)
            for v in json.loads(row["morning"] or "[]")
        ],
        # Empty on a grid computed before roofs existed. Every cell is then
        # ground, which is exactly what it was.
        roof=[bool(v) for v in json.loads(row["roof"] or "[]")],
        model=str(row["model"] or ""),
        sky=_values(row["sky"]), relative=_values(row["relative"]),
        expected=_values(row["expected"]),
    )
    return grid, str(row["signature"]), str(row["computed_at"])
