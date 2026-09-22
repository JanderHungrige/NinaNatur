"""Keeping a garden's surroundings (doc 114).

Per garden, not per place like the terrain: the areas are cut to a box around
one plot and placed in that garden's own metres. As JSON, because a garden's
surroundings are tens of rings and read whole or not at all.

Never as elements. An element is part of the garden: the light grid would
stretch to cover a forest's corner, the shade raster would coarsen with it, and
the element list and the plan's count would name every meadow.
"""
from __future__ import annotations

import json
import sqlite3

from ninanatur.garden.elements import now
from ninanatur.geo.landcover_clip import LandArea

#: Where the areas were placed from. `map`: the exact centre of the outline the
#: garden was drawn from, at its creation. `streets`: the stored anchor, moved
#: by the offset its own imported streets showed. `anchor`: the stored anchor as
#: it is — rounded to four places, so up to about 6 m off the imported houses.
PLACEMENTS = ("map", "streets", "anchor")


def save_landcover(conn: sqlite3.Connection, garden_id: int, areas: list[LandArea],
                   placed_by: str) -> None:
    """Keep these areas for the garden, replacing any it had. None found is
    kept too: it is an answer, and the next rebuild need not ask again."""
    if placed_by not in PLACEMENTS:
        raise ValueError(f"unknown placement {placed_by!r}")
    rows = [{"kind": a.kind, "rings": [[list(p) for p in ring] for ring in a.rings]}
            for a in areas]
    conn.execute(
        "INSERT INTO garden_landcover (garden_id, areas, placed_by, fetched_at)"
        " VALUES (?, ?, ?, ?) ON CONFLICT (garden_id) DO UPDATE SET"
        " areas = excluded.areas, placed_by = excluded.placed_by,"
        " fetched_at = excluded.fetched_at",
        (garden_id, json.dumps(rows, separators=(",", ":")), placed_by, now()),
    )
    conn.commit()


def load_landcover(conn: sqlite3.Connection, garden_id: int) -> list[LandArea] | None:
    """The garden's areas; None where they were never fetched."""
    row = conn.execute(
        "SELECT areas FROM garden_landcover WHERE garden_id = ?", (garden_id,)
    ).fetchone()
    if row is None:
        return None
    return [LandArea(kind=str(a["kind"]),
                     rings=[[(float(p[0]), float(p[1])) for p in ring] for ring in a["rings"]])
            for a in json.loads(row["areas"])]


def fetched(conn: sqlite3.Connection, garden_id: int) -> bool:
    """Whether the garden's surroundings have been asked for, found or not."""
    return conn.execute(
        "SELECT 1 FROM garden_landcover WHERE garden_id = ?", (garden_id,)
    ).fetchone() is not None


def draws_landcover(conn: sqlite3.Connection, garden_id: int) -> bool:
    """Whether the plan draws any of it — what its credit depends on (doc 106).
    Empty is written as exactly `[]` (`save_landcover`)."""
    return conn.execute(
        "SELECT 1 FROM garden_landcover WHERE garden_id = ? AND areas <> '[]'", (garden_id,)
    ).fetchone() is not None


__all__ = ["PLACEMENTS", "draws_landcover", "fetched", "load_landcover", "save_landcover"]
