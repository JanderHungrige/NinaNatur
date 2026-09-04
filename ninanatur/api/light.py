"""The sun map, and the button that rebuilds it.

Its own router rather than more of `planning.py`, which is well past the length
limit already. The schemas live here for the same reason `feedback.py` keeps
its own: they are used by nothing else.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_garden
from ninanatur.garden.lightgrid import load_grid, signature_of
from ninanatur.garden.lighting import recompute_light
from ninanatur.garden.store import load_garden
from ninanatur.solar.day import MONTHS, shadow_day

router = APIRouter(prefix="/api/v1/gardens", tags=["light"])


class LightMap(BaseModel):
    """Mean daily sun hours per cell, row-major from the south-west corner.

    `stale` is the honest half. The map is expensive enough to store, so it can
    be out of date — and a map that is quietly out of date is worse than one
    that says so. It is computed by comparing a signature of the shading inputs,
    not by remembering which actions ought to have invalidated it.
    """

    cell_m: float
    min_x: float
    min_y: float
    cols: int
    rows: int
    hours: list[float]
    #: The most any cell gets, so the drawing can scale without a second pass.
    max_hours: float
    computed_at: str
    stale: bool


class ShadowFrame(BaseModel):
    """Every shadow in the garden at one moment of one day."""

    #: Minutes since midnight, local solar time as the model computes it.
    minute: int
    altitude: float
    azimuth: float
    polygons: list[list[list[float]]]


class ShadowDay(BaseModel):
    month: int
    day: int
    frames: list[ShadowFrame]


@router.get("/{token}/light", response_model=LightMap | None)
def light_map(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> LightMap | None:
    """The stored map, or null when nothing has been drawn yet."""
    garden = require_garden(conn, token)
    return _read(conn, garden.garden_id)


@router.post("/{token}/light", response_model=LightMap | None)
def rebuild_light_map(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> LightMap | None:
    """Recompute the whole map, now, because somebody asked.

    Belt as well as braces. The signature should catch every change that moves a
    shadow, and if it ever does not, this is how somebody fixes their own map
    without knowing why it was wrong.
    """
    garden = require_garden(conn, token)
    recompute_light(conn, garden.garden_id)
    return _read(conn, garden.garden_id)


@router.get("/{token}/shadows", response_model=ShadowDay)
def shadows_through_a_day(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
    month: Annotated[int, Query(ge=1, le=12)] = 6,
) -> ShadowDay:
    """Where the shadows fall through one middling day of a month.

    The 15th, because a month's first and last days differ by a fortnight of sun
    and the middle is the one that represents it. Computed rather than stored:
    it is one day rather than a season, and nobody watches it twice in a row.
    """
    garden = require_garden(conn, token)
    day = shadow_day(conn, load_garden(conn, garden.garden_id), month)
    return ShadowDay(
        month=day.month,
        day=day.day,
        frames=[
            ShadowFrame(
                minute=f.minute,
                altitude=round(f.altitude, 1),
                azimuth=round(f.azimuth, 1),
                polygons=[[[round(x, 2), round(y, 2)] for x, y in p] for p in f.polygons],
            )
            for f in day.frames
        ],
    )


def _read(conn: sqlite3.Connection, garden_id: int) -> LightMap | None:
    stored = load_grid(conn, garden_id)
    if stored is None:
        return None
    grid, signature, computed_at = stored
    return LightMap(
        cell_m=grid.cell_m,
        min_x=grid.min_x,
        min_y=grid.min_y,
        cols=grid.cols,
        rows=grid.rows,
        hours=grid.hours,
        max_hours=max(grid.hours) if grid.hours else 0.0,
        computed_at=computed_at,
        stale=signature != signature_of(load_garden(conn, garden_id)),
    )


__all__ = ["MONTHS", "router"]
