"""Saying which stored outlines OpenStreetMap drew.

A one-time migration in the sense of `one_time.py`: it changes what existing
rows hold, runs once, and marks itself in `catalogue_meta`, even on a fresh
database with nothing to do.
"""
from __future__ import annotations

import sqlite3

#: Marks the one-time backfill of `element.outline_source` (2026-09-21).
OUTLINE_SOURCE_KEY = "wave_25_outline_source"

#: What the history makes certain, spelled out rather than read from `objects`:
#: a migration has to mean what it meant on the day it ran. A street is the
#: import's, or a gardener's that is thanked once too often. A house or shed
#: whose height, roof or eaves are not the gardener's came with the import — a
#: house drawn by hand starts as the gardener's in all three and is never
#: surveyed — which was the rule the credit was read by until this column.
_MAP_OUTLINES = (
    "UPDATE element SET outline_source = 'osm'"
    " WHERE outline_source IS NULL AND ("
    " kind = 'street'"
    " OR (kind IN ('house', 'shed') AND (height_source != 'user'"
    " OR roof_source = 'osm' OR eaves_source = 'osm_levels')))"
)


def mark_map_outlines(conn: sqlite3.Connection) -> str | None:
    """Mark the outlines the map import brought, where the history can tell.

    A map house whose height and roof the gardener had already both corrected
    reads as drawn by hand and stays unmarked: nothing stored says otherwise.
    That is the one case this cannot recover, and it errs by leaving a credit
    out, so gardens made from the map from now on carry the mark from the start.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS catalogue_meta"
        " (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    done = conn.execute(
        "SELECT 1 FROM catalogue_meta WHERE key = ?", (OUTLINE_SOURCE_KEY,)
    ).fetchone()
    if done is not None:
        return None
    marked = conn.execute(_MAP_OUTLINES).rowcount
    conn.execute(
        "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
        (OUTLINE_SOURCE_KEY, str(marked)),
    )
    conn.commit()
    return None if marked == 0 else f"marked {marked} outline(s) as OpenStreetMap's"
