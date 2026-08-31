"""Reading and writing the things drawn on a plan.

Split out of `store.py` when Wave 11 merged `bed` and `obstacle` into `element`:
the garden's own lifecycle and the elements on it are read for different
reasons, and `store.py` was already over the file-length limit before this
feature added to it.

The geometry conversion lives here too. Callers still describe a rectangle as a
width, a depth and an angle — that is what a resize handle produces — and this
module turns it into the four points that get stored, so nothing downstream has
to know both representations.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import UTC, datetime
from typing import Any

from ninanatur.garden.models import PLANTING_KIND, Element, Planting, Polygon


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def polygon_centroid(polygon: Polygon) -> tuple[float, float]:
    """The average of the corners. Good enough to hang an element off, and it
    is where a bed's own coordinates are measured from."""
    xs = [float(p[0]) for p in polygon]
    ys = [float(p[1]) for p in polygon]
    return sum(xs) / len(xs), sum(ys) / len(ys)

#: Columns in the order `_row_to_element` expects them.
_COLUMNS = (
    "element_id, kind, shape, x, y, points, width, constraint_hint, height,"
    " height_source, label, name, soil_type, moisture, ellenberg_l, ellenberg_m,"
    " ellenberg_n, ellenberg_r, sun_hours, light_computed_at, height_above_ground"
)


def _rect_points(
    width: float, depth: float, rotation: float
) -> list[list[float]]:
    """A rectangle as its four corners, rotated clockwise from north.

    Wave 11 stores points rather than a width, a depth and an angle, so dragging
    a vertex has nothing to convert. The rectangle-ness survives as a constraint
    hint the editing tool honours, not as a second geometry.
    """
    half_w, half_d = width / 2, depth / 2
    a = math.radians(rotation)
    cos, sin = math.cos(a), math.sin(a)
    corners = ((-half_w, -half_d), (half_w, -half_d), (half_w, half_d), (-half_w, half_d))
    return [[cx * cos + cy * sin, -cx * sin + cy * cos] for cx, cy in corners]


def geometry_for(
    *,
    shape: str,
    width: float | None,
    depth: float | None,
    rotation: float,
    points: list[list[float]] | None,
) -> tuple[str, list[list[float]] | None, float | None, str | None]:
    """`(shape, points, width, constraint_hint)` as stored.

    A rectangle becomes a polygon carrying the `rect` hint. A circle keeps its
    diameter and stores no points. A line and a free polygon store what they
    were given.
    """
    if shape == "circle":
        return "circle", None, width, None
    if shape == "line":
        return "line", points, width, None
    if shape == "rect":
        return (
            "polygon",
            _rect_points(width or 0.0, depth if depth is not None else (width or 0.0), rotation),
            None,
            "rect",
        )
    return "polygon", points, None, None


def _row_to_element(row: sqlite3.Row, plantings: list[Planting] | None = None) -> Element:
    raw = row["points"]
    return Element(
        element_id=int(row["element_id"]),
        kind=str(row["kind"]),
        shape=str(row["shape"]),
        x=float(row["x"]),
        y=float(row["y"]),
        points=None if raw is None else list(json.loads(raw)),
        width=None if row["width"] is None else float(row["width"]),
        constraint_hint=row["constraint_hint"],
        height=None if row["height"] is None else float(row["height"]),
        height_source=str(row["height_source"]),
        label=row["label"],
        name=row["name"],
        soil_type=row["soil_type"],
        moisture=row["moisture"],
        ellenberg_l=row["ellenberg_l"],
        ellenberg_m=row["ellenberg_m"],
        ellenberg_n=row["ellenberg_n"],
        ellenberg_r=row["ellenberg_r"],
        sun_hours=row["sun_hours"],
        light_computed_at=row["light_computed_at"],
        height_above_ground=float(row["height_above_ground"] or 0.0),
        plantings=plantings or [],
    )


def insert_element(conn: sqlite3.Connection, garden_id: int, **fields: Any) -> int:
    """Store one element. Missing columns take their schema default."""
    points = fields.pop("points", None)
    columns = ["garden_id", *fields.keys(), "points"]
    values = [garden_id, *fields.values(), None if points is None else json.dumps(points)]
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT INTO element ({', '.join(columns)}) VALUES ({placeholders})",  # noqa: S608
        values,
    )
    return int(cursor.lastrowid or 0)


def elements_for(
    conn: sqlite3.Connection, garden_id: int, plantings_by_element: dict[int, list[Planting]]
) -> list[Element]:
    """Every element on a garden, planting sites first.

    Ordered so a caller walking the list meets the beds before the things that
    shade them — the same order the plan draws in, and the one the light
    computation wants.
    """
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM element WHERE garden_id = ?"  # noqa: S608
        " ORDER BY kind = ? DESC, element_id",
        (garden_id, PLANTING_KIND),
    ).fetchall()
    return [_row_to_element(row, plantings_by_element.get(int(row["element_id"]))) for row in rows]


def update_element(conn: sqlite3.Connection, element_id: int, **fields: Any) -> None:
    """Change what an element is. Unknown columns are refused rather than
    silently dropped — a typo in a field name is a change that never happened."""
    if not fields:
        return
    if "points" in fields and fields["points"] is not None:
        fields["points"] = json.dumps(fields["points"])
    allowed = {row[1] for row in conn.execute("PRAGMA table_info(element)")}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"no such element column: {sorted(unknown)}")
    assignments = ", ".join(f"{name} = ?" for name in fields)
    conn.execute(
        f"UPDATE element SET {assignments} WHERE element_id = ?",  # noqa: S608
        (*fields.values(), element_id),
    )


def delete_element(conn: sqlite3.Connection, element_id: int) -> None:
    """Remove one element.

    Its plantings go with it: `planting` hangs off `element_id` with
    `ON DELETE CASCADE`, and a row whose parent is gone is a query that fails at
    the worst moment. The interface says how many before asking.
    """
    conn.execute("DELETE FROM element WHERE element_id = ?", (element_id,))
