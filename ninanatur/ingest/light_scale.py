"""Putting stored bed light values onto the current hours->L convention.

A one-time migration in the sense of `one_time.py`: it changes what existing
rows hold, runs once, and marks itself in `catalogue_meta`, even on a fresh
database with nothing to do.

A bed's light value is only ever written together with the sun hours it came
from (`lighting.recompute_light`), so a new convention needs no shadow work:
the value follows from the hours already stored. On 2026-09-21 the staircase of
classic rungs became straight lines on EIVE's 0–10 scale (`solar.light`), and
this moved every computed bed across at once. Before it, each garden had to run
the slow rebuild to re-label hours it already had, and until somebody did, one
page mixed both scales.

Whoever next changes `SUN_HOUR_ANCHORS` adds a marker here and runs this again:
reading the convention as it is on the day it runs is the point of it.
"""
from __future__ import annotations

import sqlite3

from ninanatur.solar.light import ellenberg_from_sun_hours

#: Marks the move from the staircase onto EIVE's scale (2026-09-21).
LIGHT_SCALE_KEY = "wave_25_light_on_eive_scale"


def rescale_bed_light(conn: sqlite3.Connection) -> str | None:
    """Give every bed with stored sun hours the light value those hours give now."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS catalogue_meta"
        " (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    done = conn.execute(
        "SELECT 1 FROM catalogue_meta WHERE key = ?", (LIGHT_SCALE_KEY,)
    ).fetchone()
    if done is not None:
        return None
    rows = conn.execute(
        "SELECT element_id, sun_hours, ellenberg_l FROM element"
        " WHERE sun_hours IS NOT NULL"
    ).fetchall()
    moved = 0
    for element_id, hours, old in rows:
        new = ellenberg_from_sun_hours(float(hours))
        if old != new:
            conn.execute(
                "UPDATE element SET ellenberg_l = ? WHERE element_id = ?",
                (new, element_id),
            )
            moved += 1
    conn.execute(
        "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
        (LIGHT_SCALE_KEY, str(moved)),
    )
    conn.commit()
    return None if moved == 0 else f"moved {moved} bed light value(s) onto EIVE's scale"
