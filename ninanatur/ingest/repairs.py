"""Mending rows the plan cannot draw.

A one-time migration in the sense of `one_time.py`: it changes what existing
rows hold, runs once, and marks itself in `catalogue_meta`. It lives apart only
because that module is close to the 300-line limit.
"""
from __future__ import annotations

import json
import logging
import sqlite3

from ninanatur.garden.footprint import Shape, footprint_of
from ninanatur.garden.objects import ObjectKind, default_size

logger = logging.getLogger(__name__)

#: Marks the one-time repair that followed the owner's check of waves 24 and 25.
UNBUILDABLE_KEY = "wave_25_unbuildable_elements"

#: A path's band when its kind names none: what a freehand stroke is drawn at.
FALLBACK_WIDTH_M = 1.0


def mend_unbuildable_elements(conn: sqlite3.Connection) -> str | None:
    """Give reshaped paths their width back, and remove lines that are no line.

    Until 2026-09-21 the server stored an element first and built its footprint
    only when the garden was read. Two routes stored rows that no footprint can
    be built from. One was a freehand press that stayed within one centimetre,
    which made a line of one point twice. The other was any reshape of a path,
    which cleared its width. Either kind of row made every later read of its
    garden fail: the whole plan answered 422, and nothing on the page could
    reach the row.

    A cleared width is restored. The path is real and somebody drew it; only its
    band was lost, so it gets its kind's usual width. A line without two
    different points, or an outline of fewer than three points, is removed,
    and each removal is logged by id: such a row never reached a plan, because
    no request that stored one ever returned, and a garden that cannot open is
    the greater loss.

    Judged by what *reading* needs (`footprint_of`), not by the stricter check
    a write now makes. An outline of three corners two of which coincide covers
    no ground, but it opened, and a bed like that may hold plantings. Removing
    it would take them too, for good, for a row that broke nothing.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS catalogue_meta"
        " (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    done = conn.execute(
        "SELECT 1 FROM catalogue_meta WHERE key = ?", (UNBUILDABLE_KEY,)
    ).fetchone()
    if done is not None:
        return None
    mended = removed = 0
    rows = conn.execute(
        "SELECT element_id, garden_id, kind, shape, width, points FROM element"
        " WHERE shape IN ('line', 'polygon')"
    ).fetchall()
    for row in rows:
        points = None if row["points"] is None else list(json.loads(row["points"]))
        if _buildable(str(row["shape"]), row["width"], points):
            continue
        width = _usual_width(str(row["kind"]))
        if row["shape"] == "line" and _buildable("line", width, points):
            conn.execute(
                "UPDATE element SET width = ? WHERE element_id = ?",
                (width, row["element_id"]),
            )
            mended += 1
            continue
        logger.warning(
            "removed element %s of garden %s: %s %s cannot be drawn",
            row["element_id"], row["garden_id"], row["shape"], points,
        )
        conn.execute("DELETE FROM element WHERE element_id = ?", (row["element_id"],))
        removed += 1
    conn.execute(
        "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
        (UNBUILDABLE_KEY, f"mended {mended}, removed {removed}"),
    )
    conn.commit()
    if mended == 0 and removed == 0:
        return None
    return f"gave {mended} path(s) their width back, removed {removed} undrawable element(s)"


def _buildable(shape: str, width: float | None, points: list[list[float]] | None) -> bool:
    """Whether the garden can be read with this row in it."""
    try:
        footprint_of(shape=Shape(shape), x=0.0, y=0.0, width=width, depth=None,
                     rotation=0.0, points=points)
    except ValueError:
        return False
    return True


def _usual_width(kind: str) -> float:
    try:
        width, _ = default_size(ObjectKind(kind))
    except ValueError:
        return FALLBACK_WIDTH_M
    return width if width and width > 0 else FALLBACK_WIDTH_M
