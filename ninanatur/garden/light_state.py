"""Whether a bed's light value can be trusted: missing, stale or current.

Light is computed when somebody presses the button, never on a write (see
`lighting.py`). So a bed can be ranked on soil alone because its light was
never computed, or on a value from before an obstacle moved — and a list that
says "ranked by this bed's site" in either case is claiming more than it knows
(owner review #9, 2026-09-21).

"Stale" is the sun map's own test: the stored grid's signature against a
signature of what stands in the garden now. `api/light.py::_read` calls
`current_signature` for the map's `stale` flag, so the two cannot drift apart.
Measured on 2026-09-21 against a real 200 × 200 terrain window and a
garden of 40 houses and 20 beds of 10 plantings: about 4 ms per request, nearly
all of it decoding the terrain window — against a ranking of the whole catalogue
that the same request runs anyway.
"""
from __future__ import annotations

import sqlite3
from typing import Literal

from ninanatur.garden.lightgrid import signature_of
from ninanatur.garden.lightview import shading_taxa
from ninanatur.garden.models import Element, Garden
from ninanatur.garden.terrain_sync import ground_for, horizon_for
from ninanatur.geo.projection import LatLon

LightState = Literal["missing", "stale", "current"]


def current_signature(conn: sqlite3.Connection, garden: Garden) -> str:
    """A signature of the shading inputs as they stand now.

    What the map was built on is part of what makes it current (doc 106), so
    the ground and the horizon read here are the stored ones, never fetched.
    """
    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    return signature_of(
        garden, ground_for(conn, anchor), horizon_for(conn, anchor),
        shading_taxa=shading_taxa(conn, garden),
    )


def stored_signature(conn: sqlite3.Connection, garden_id: int) -> str | None:
    """The signature the stored grid was computed from, without reading the grid."""
    row = conn.execute(
        "SELECT signature FROM light_grid WHERE garden_id = ?", (garden_id,)
    ).fetchone()
    return None if row is None else str(row[0])


def light_state(conn: sqlite3.Connection, garden: Garden, bed: Element) -> LightState:
    """What the bed's light value is worth to a ranking.

    `missing`: never computed — a bed drawn after the last press of the button.
    `stale`: computed, but something that moves a shadow has changed since, or
    there is no stored map to say what it was computed from. `current`: the map
    and the garden still agree.
    """
    if bed.ellenberg_l is None:
        return "missing"
    stored = stored_signature(conn, garden.garden_id)
    if stored is None or stored != current_signature(conn, garden):
        return "stale"
    return "current"


__all__ = ["LightState", "current_signature", "light_state", "stored_signature"]
