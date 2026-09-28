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
from dataclasses import dataclass

import numpy as np

from ninanatur.garden.elements import now
from ninanatur.geo.pointcloud import CloudWindow
from ninanatur.geo.projection import LatLon, Metres, to_metres

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


def save_cloud(conn: sqlite3.Connection, key: str, window: CloudWindow,
               anchor: LatLon | None = None, *, classified: bool = False) -> None:
    """Keep this window, replacing whatever was there for the place.

    `anchor` is the garden it was read around, `classified` whether a building
    model told its roofs from its crowns (doc 121)."""
    finite = [v for v in window.ground if not math.isnan(v)]
    base = min(finite) if finite else 0.0
    conn.execute(
        "INSERT INTO cloud_window (place_key, cell_m, cols, rows, base_m, ground_cm,"
        " surface_cm, crown_base_cm, source, licence, attribution, points_per_m2, fetched_at,"
        " anchor_lat, anchor_lon, classified)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (place_key) DO UPDATE SET cell_m = excluded.cell_m,"
        " cols = excluded.cols, rows = excluded.rows, base_m = excluded.base_m,"
        " ground_cm = excluded.ground_cm, surface_cm = excluded.surface_cm,"
        " crown_base_cm = excluded.crown_base_cm, source = excluded.source,"
        " licence = excluded.licence, attribution = excluded.attribution,"
        " points_per_m2 = excluded.points_per_m2, fetched_at = excluded.fetched_at,"
        " anchor_lat = excluded.anchor_lat, anchor_lon = excluded.anchor_lon,"
        " classified = excluded.classified",
        (key, window.cell_m, window.cols, window.rows, base,
         _packed(window.ground, base), _packed(window.surface, base),
         # A crown base is already a height above the ground, so it is stored
         # from zero rather than from the window's base.
         _packed(window.crown_base, 0.0),
         window.source, window.licence, window.attribution, window.points_per_m2, now(),
         None if anchor is None else anchor.lat, None if anchor is None else anchor.lon,
         int(classified)),
    )
    conn.commit()


@dataclass(frozen=True)
class Stored:
    """What is known about a place's stored window without unpacking it."""

    #: Whether it says which garden it was read around (doc 121).
    anchored: bool
    #: Whether a building model told its roofs from its crowns.
    classified: bool


def stored_cloud(conn: sqlite3.Connection, key: str) -> Stored | None:
    """Whether a window is stored for this place, and what it can be used for."""
    row = conn.execute(
        "SELECT anchor_lat, classified FROM cloud_window WHERE place_key = ?", (key,),
    ).fetchone()
    if row is None:
        return None
    return Stored(anchored=row["anchor_lat"] is not None, classified=bool(row["classified"]))


def load_cloud(conn: sqlite3.Connection, key: str,
               around: LatLon | None = None) -> CloudWindow | None:
    """What the laser saw here, or None where it has not been read.

    On the axes of the garden that read it, or of `around`: a window is shared
    by every garden in its place, so another garden moves it onto its own axes
    by where it stands from the first (doc 121). A window stored before that
    garden was kept cannot be moved, and is None for `around`.
    """
    row = conn.execute(
        "SELECT cell_m, cols, rows, base_m, ground_cm, surface_cm, crown_base_cm,"
        " source, licence, attribution, points_per_m2, anchor_lat, anchor_lon"
        " FROM cloud_window WHERE place_key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    shift = Metres(0.0, 0.0)
    if around is not None:
        if row["anchor_lat"] is None:
            return None
        shift = to_metres(around, LatLon(float(row["anchor_lat"]), float(row["anchor_lon"])))
    base = float(row["base_m"])
    reach = float(row["cell_m"]) * int(row["cols"]) / 2
    return CloudWindow(
        min_x=-reach - shift.x, min_y=-reach - shift.y, cell_m=float(row["cell_m"]),
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


__all__ = ["NOTHING", "Stored", "cloud_source", "load_cloud", "save_cloud", "stored_cloud"]
