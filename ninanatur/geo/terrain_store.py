"""Keeping a fetched terrain window, and finding it again.

Split from `terrain.py` when that file crossed three hundred lines, and the
seam is a real one: fetching is about a service's quirks, storing is about a
shape on a volume. The two change for different reasons.

Keyed by **location**, not by garden. Terrain does not change and two gardens in
the same street stand on the same ground, so one window serves both — less
storage, and far fewer requests against services nobody is paying us to use.
"""
from __future__ import annotations

import math
import sqlite3
import zlib

import numpy as np

from ninanatur.garden.elements import now
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import TerrainWindow

#: How coarsely a location is rounded before it becomes a cache key.
KEY_GRID_M = 100.0

#: The stored value for ground nobody surveyed. The extreme of the 16-bit range,
#: so it can never collide with a real height: 32767 cm is 327 m of relief inside
#: a 200 m window, which would be a slope of 160 %.
NO_HEIGHT = -32768


def cache_key(anchor: LatLon) -> str:
    """A location rounded to the shared-window grid.

    Rounded in metres rather than in degrees: a hundredth of a degree of
    longitude is 68 m in Flensburg and 74 m in Konstanz, and a key whose meaning
    drifts across the country is a key that shares the wrong windows.

    A grid has lines, so two gardens twenty metres apart can still land either
    side of one and fetch a window each. That costs one request. The guarantee
    that matters is the other way round: a shared key never puts distant gardens
    together, because they would then be handed each other's ground.
    """
    lat = round(anchor.lat * 111_320 / KEY_GRID_M)
    lon = round(anchor.lon * 111_320 * math.cos(math.radians(anchor.lat)) / KEY_GRID_M)
    return f"{lat}:{lon}"


def save_window(conn: sqlite3.Connection, key: str, window: TerrainWindow) -> None:
    """Keep the window, not the raster it came from.

    Centimetres above the window's own minimum, deflated: a garden's ground
    spans a few metres, so every value fits in a 16-bit integer. Stored as JSON
    the same window came to 202 KB, larger than the GeoTIFF it was made from;
    as a blob it is about a quarter of that.

    `NO_HEIGHT` marks ground nobody surveyed, because a zero there would be a
    cliff rather than an absence.
    """
    finite = [h for h in window.heights if not math.isnan(h)]
    base = min(finite) if finite else 0.0
    centimetres = np.array(
        [NO_HEIGHT if math.isnan(h) else round((h - base) * 100) for h in window.heights],
        dtype="<i2",
    )
    blob = zlib.compress(centimetres.tobytes(), 6)
    conn.execute(
        "INSERT INTO terrain_window (place_key, min_x, min_y, cell_m, cols, rows,"
        " base_m, heights_cm, source, licence, attribution, vertical_step_m, fetched_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (place_key) DO UPDATE SET min_x = excluded.min_x,"
        " min_y = excluded.min_y, cell_m = excluded.cell_m, cols = excluded.cols,"
        " rows = excluded.rows, base_m = excluded.base_m,"
        " heights_cm = excluded.heights_cm, source = excluded.source,"
        " licence = excluded.licence, attribution = excluded.attribution,"
        " vertical_step_m = excluded.vertical_step_m, fetched_at = excluded.fetched_at",
        (key, window.min_x, window.min_y, window.cell_m, window.cols, window.rows,
         base, blob, window.source, window.licence,
         window.attribution, window.vertical_step_m, now()),
    )
    conn.commit()


def load_window(conn: sqlite3.Connection, key: str) -> TerrainWindow | None:
    """The stored window for this location, or None if it was never fetched."""
    row = conn.execute(
        "SELECT min_x, min_y, cell_m, cols, rows, base_m, heights_cm, source,"
        " licence, attribution, vertical_step_m FROM terrain_window WHERE place_key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    base = float(row["base_m"])
    centimetres = np.frombuffer(zlib.decompress(row["heights_cm"]), dtype="<i2")
    heights = [
        float("nan") if cm == NO_HEIGHT else base + float(cm) / 100.0
        for cm in centimetres
    ]
    return TerrainWindow(
        min_x=float(row["min_x"]),
        min_y=float(row["min_y"]),
        cell_m=float(row["cell_m"]),
        cols=int(row["cols"]),
        rows=int(row["rows"]),
        heights=heights,
        source=str(row["source"]),
        licence=str(row["licence"]),
        attribution=str(row["attribution"]),
        vertical_step_m=float(row["vertical_step_m"]),
    )


__all__ = ["KEY_GRID_M", "NO_HEIGHT", "cache_key", "load_window", "save_window"]
