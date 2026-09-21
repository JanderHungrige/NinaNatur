"""The sun map, and the button that rebuilds it.

Its own router rather than more of `planning.py`, which is well past the length
limit already. Its response shapes are in `schemas_light.py`, which this module
outgrew the limit without.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from ninanatur.api import ratelimit
from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_garden
from ninanatur.api.schemas_light import (
    CreditOut,
    LightMap,
    MisplacedOut,
    ShadowDay,
    ShadowFrame,
    TerrainOut,
)
from ninanatur.garden.building_sync import measure_buildings
from ninanatur.garden.cloud_sync import ensure_cloud
from ninanatur.garden.credits import credits_for
from ninanatur.garden.elements import now
from ninanatur.garden.landcover_sync import ensure_landcover
from ninanatur.garden.light_state import current_signature
from ninanatur.garden.light_worker import month_grid, recompute_light
from ninanatur.garden.lightgrid import extent_of
from ninanatur.garden.lightgrid_store import load_grid
from ninanatur.garden.misplaced import misplaced_plantings
from ninanatur.garden.relief import crop_to, relief_of
from ninanatur.garden.store import load_garden
from ninanatur.garden.terrain_sync import ensure_terrain, ground_for
from ninanatur.geo.cloud_store import cloud_source
from ninanatur.geo.landcover_store import draws_landcover
from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain_store import cache_key, horizon_source
from ninanatur.solar.day import MONTHS, shadow_day

router = APIRouter(prefix="/api/v1/gardens", tags=["light"])


@router.get("/{token}/light", response_model=LightMap | None)
def light_map(
    token: str,
    request: Request,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
    month: Annotated[int | None, Query(ge=3, le=10)] = None,
) -> LightMap | None:
    """The stored map, or null when nothing has been drawn yet.

    `month` asks for one month instead of the season, computed on the spot and
    not stored. March to October, the same window the whole light model uses:
    a plant's December is not what decides where it can live, and a map of it
    would drag every German garden into shade.

    A month is a computation — about a quarter of a relight, seconds on a big
    garden — so it takes a slot and counts against the visitor's limit like the
    other three, slot first. The stored season map is a read, never turned away.
    """
    garden = require_garden(conn, token)
    if month is None:
        return _read(conn, garden.garden_id)
    with ratelimit.heavy():
        ratelimit.check(conn, request, "month")
        return _read(conn, garden.garden_id, month)


@router.post("/{token}/light", response_model=LightMap | None)
def rebuild_light_map(
    token: str,
    request: Request,
    _slot: Annotated[None, Depends(ratelimit.heavy_slot)],
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> LightMap | None:
    """Recompute the whole map, now, because somebody asked.

    Belt as well as braces. The signature should catch every change that moves a
    shadow, and if it ever does not, this is how somebody fixes their own map
    without knowing why it was wrong.

    It is also where a garden gets its ground for the first time. A state survey
    takes seconds to answer, which is too long for a page load and perfectly
    reasonable for a button — and afterwards every recompute reads it for free.
    """
    ratelimit.check(conn, request, "light")
    garden = require_garden(conn, token)
    # The one place the ground is fetched. A survey answers in seconds, which is
    # too long for a page load and fine for a button somebody pressed.
    standing = load_garden(conn, garden.garden_id)
    ensure_terrain(conn, standing)
    # The land around it, for a garden made before it was fetched (doc 114).
    ensure_landcover(conn, standing)
    # After the ground, because a raw surface model is only object heights once
    # the terrain has been taken off it.
    measure_buildings(conn, load_garden(conn, garden.garden_id))
    # And after the buildings, because the laser cannot tell a roof from a
    # crown on its own and the building model is what decides (doc 107). Only
    # where a state publishes a cloud, which is nine of them.
    ensure_cloud(conn, load_garden(conn, garden.garden_id))
    recompute_light(conn, garden.garden_id)
    return _read(conn, garden.garden_id)


@router.get("/{token}/terrain", response_model=TerrainOut | None)
def terrain(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> TerrainOut | None:
    """The ground under this garden, or null where nobody publishes it.

    Null is an answer and the page says so in words. Nine Bundesländer have no
    service in the registry, and a garden there keeps the flat assumption it
    always had — which is fine, and being quiet about it is not.
    """
    garden = require_garden(conn, token)
    stored = ground_for(conn, LatLon(lat=garden.latitude, lon=garden.longitude))
    if stored is None:
        return None
    # The window reaches 100 m out because the shading needs the neighbours.
    # The picture is the garden, and sending the rest meant forty thousand
    # rectangles for a drawing of about nine hundred.
    box = extent_of(load_garden(conn, garden.garden_id))
    shown = stored if box is None else crop_to(stored, box)
    lit = relief_of(shown)
    heights = [h for h in shown.heights if h == h]
    return TerrainOut(
        cell_m=shown.cell_m,
        min_x=shown.min_x,
        min_y=shown.min_y,
        cols=shown.cols,
        rows=shown.rows,
        relief=lit,
        lowest=round(min(heights), 2) if heights else 0.0,
        highest=round(max(heights), 2) if heights else 0.0,
        source=shown.source,
        licence=shown.licence,
        attribution=shown.attribution,
        vertical_step_m=shown.vertical_step_m,
    )


@router.get("/{token}/sources", response_model=list[CreditOut])
def sources(
    token: str,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> list[CreditOut]:
    """Every survey this garden's numbers actually rest on (doc 106).

    Empty is an ordinary answer: a garden nobody has measured anything for owes
    nobody anything. What is here is what was used, not what the state could in
    principle offer — a credit for a source a garden never touched would be a
    claim about where its numbers came from.
    """
    garden = require_garden(conn, token)
    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    found = credits_for(
        load_garden(conn, garden.garden_id),
        ground=ground_for(conn, anchor),
        horizon_source=horizon_source(conn, cache_key(anchor)),
        laser_source=cloud_source(conn, cache_key(anchor)),
        landcover=draws_landcover(conn, garden.garden_id),
    )
    return [CreditOut(**vars(credit)) for credit in found]


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


def _read(
    conn: sqlite3.Connection, garden_id: int, month: int | None = None
) -> LightMap | None:
    """The map to draw, and everything the panel says about it.

    A month is drawn from a grid computed just now, so it is never stale and
    says so. `misplaced` stays on the **stored season** grid in either case: a
    plant standing in the wrong light is a judgement about its growing season,
    and warnings that appeared and vanished as somebody scrolled through the
    months would be noise rather than advice.
    """
    stored = load_grid(conn, garden_id)
    if stored is None:
        return None
    grid, signature, computed_at = stored
    garden = load_garden(conn, garden_id)
    # The one signature the list's `light_state` uses too, so the map and the
    # list cannot disagree about what is out of date.
    now_signature = current_signature(conn, garden)
    if month is not None:
        fresh = month_grid(conn, garden, month)
        if fresh is not None:
            grid, computed_at, signature = fresh, now(), now_signature
    return LightMap(
        cell_m=grid.cell_m,
        min_x=grid.min_x,
        min_y=grid.min_y,
        cols=grid.cols,
        rows=grid.rows,
        hours=grid.hours,
        roof=grid.roof,
        max_hours=max(answered) if (answered := [
            h for i, h in enumerate(grid.hours)
            if h is not None and not grid.is_roof(i)
        ]) else 0.0,
        morning=grid.morning,
        misplaced=[
            MisplacedOut(**vars(m)) for m in misplaced_plantings(conn, garden, grid)
        ],
        computed_at=computed_at,
        stale=signature != now_signature,
    )


__all__ = ["MONTHS", "router"]
