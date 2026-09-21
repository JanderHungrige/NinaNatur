"""Keeping what the laser saw — Wave 25, feature 4 (doc 107).

The tile is a hundred megabytes and is not a thing to keep; the window is three
hundred metres of it and is. Stored the way the terrain window is (doc 17):
centimetres above the window's own base as 16-bit integers, deflated — 66 kB
for the verified NRW window, against about a megabyte as JSON.

Keyed by place, not by garden. Two gardens in a street share a window, and the
key is the same one the terrain uses, so they are fetched and dropped together.
"""
from __future__ import annotations

import math
import sqlite3
import zlib

import numpy as np

from ninanatur.garden.elements import now
from ninanatur.geo.pointcloud import CloudWindow

#: What a cell nobody measured holds. Not zero: zero is a height, and over a
#: crown base it would mean "the canopy starts at the ground".
NOTHING = -32768


def _packed(values: list[float], base: float) -> bytes:
    centimetres = np.array(
        [NOTHING if math.isnan(v) else round((v - base) * 100) for v in values],
        dtype="<i2",
    )
    return zlib.compress(centimetres.tobytes(), 6)


def _unpacked(blob: bytes, base: float) -> list[float]:
    values = np.frombuffer(zlib.decompress(blob), dtype="<i2")
    return [math.nan if int(v) == NOTHING else base + int(v) / 100 for v in values]


def save_cloud(conn: sqlite3.Connection, key: str, window: CloudWindow) -> None:
    """Keep this window, replacing whatever was there for the place."""
    finite = [v for v in window.ground if not math.isnan(v)]
    base = min(finite) if finite else 0.0
    conn.execute(
        "INSERT INTO cloud_window (place_key, cell_m, cols, rows, base_m, ground_cm,"
        " surface_cm, crown_base_cm, source, licence, attribution, points_per_m2, fetched_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (place_key) DO UPDATE SET cell_m = excluded.cell_m,"
        " cols = excluded.cols, rows = excluded.rows, base_m = excluded.base_m,"
        " ground_cm = excluded.ground_cm, surface_cm = excluded.surface_cm,"
        " crown_base_cm = excluded.crown_base_cm, source = excluded.source,"
        " licence = excluded.licence, attribution = excluded.attribution,"
        " points_per_m2 = excluded.points_per_m2, fetched_at = excluded.fetched_at",
        (key, window.cell_m, window.cols, window.rows, base,
         _packed(window.ground, base), _packed(window.surface, base),
         # A crown base is already a height above the ground, so it is stored
         # from zero rather than from the window's base.
         _packed(window.crown_base, 0.0),
         window.source, window.licence, window.attribution, window.points_per_m2, now()),
    )
    conn.commit()


def load_cloud(conn: sqlite3.Connection, key: str) -> CloudWindow | None:
    """What the laser saw here, or None where it has not been read."""
    row = conn.execute(
        "SELECT cell_m, cols, rows, base_m, ground_cm, surface_cm, crown_base_cm,"
        " source, licence, attribution, points_per_m2 FROM cloud_window WHERE place_key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    base = float(row["base_m"])
    reach = float(row["cell_m"]) * int(row["cols"]) / 2
    return CloudWindow(
        min_x=-reach, min_y=-reach, cell_m=float(row["cell_m"]),
        cols=int(row["cols"]), rows=int(row["rows"]),
        ground=_unpacked(row["ground_cm"], base),
        surface=_unpacked(row["surface_cm"], base),
        crown_base=_unpacked(row["crown_base_cm"], 0.0),
        source=str(row["source"]), licence=str(row["licence"]),
        attribution=str(row["attribution"]), points_per_m2=float(row["points_per_m2"]),
    )


def cloud_source(conn: sqlite3.Connection, key: str) -> str | None:
    """Who flew the laser here, for the credit its licence asks for (doc 106)."""
    row = conn.execute(
        "SELECT source FROM cloud_window WHERE place_key = ?", (key,)
    ).fetchone()
    return None if row is None else str(row["source"])


__all__ = ["NOTHING", "cloud_source", "load_cloud", "save_cloud"]
