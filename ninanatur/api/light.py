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
from ninanatur.garden.building_sync import measure_buildings
from ninanatur.garden.elements import now
from ninanatur.garden.lightgrid import extent_of, signature_of
from ninanatur.garden.lightgrid_store import load_grid
from ninanatur.garden.lighting import recompute_light
from ninanatur.garden.lightview import month_grid
from ninanatur.garden.misplaced import misplaced_plantings
from ninanatur.garden.relief import crop_to, relief_of
from ninanatur.garden.store import load_garden
from ninanatur.garden.terrain_sync import ensure_terrain, ground_for
from ninanatur.geo.projection import LatLon
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
    #: Null only where nothing can be answered: a building whose height nobody
    #: has recorded. A cell under a house is answered **on the roof** — at its
    #: own height and its own pitch, which at 51°N makes a north face and a
    #: south face very different places.
    hours: list[float | None]
    #: Which of those cells are a roof rather than ground, in step with `hours`.
    #: Empty on a grid computed before roofs were.
    roof: list[bool]
    #: The most any cell of **ground** gets, so the drawing can scale without a
    #: second pass. Roofs are left out of it: nothing is planted on one, and a
    #: sunny roof would otherwise set the scale for the garden below it.
    max_hours: float
    computed_at: str
    stale: bool
    #: Of those hours, the ones before the sun crosses due south. Empty on a
    #: grid computed before the split existed; the next rebuild fills it, and
    #: nulls line up with `hours`.
    morning: list[float | None]
    #: Plantings standing in light they did not ask for.
    misplaced: list[MisplacedOut]


class MisplacedOut(BaseModel):
    """A planting standing in light it did not ask for.

    A warning, never a refusal: a gardener may know something the model does
    not — a cultivar bred for shade, a wall that throws light back, or simply
    that they want it there.
    """

    planting_id: int
    bed_id: int
    taxon_id: int
    name: str
    wants: float
    gets: float
    sun_hours: float
    #: 'too_dark' | 'too_bright'. Both happen; the second is the forgotten one.
    problem: str


class TerrainOut(BaseModel):
    """The ground under a garden, and how far it is to be trusted.

    Every field after `relief` is there so the page can answer "says who, and
    how good is it" without the reader having to know what a DGM1 is. A height
    shown without its credit is a height used outside its licence, and a height
    shown without its accuracy invites more confidence than it earns.
    """

    cell_m: float
    min_x: float
    min_y: float
    cols: int
    rows: int
    #: Relief shading, 0 (in shadow) to 1 (lit), row-major from the south-west.
    #: Sent already computed: it is one pass over the grid on a server that has
    #: the heights anyway, against shipping 40,000 metre values to a browser
    #: that would then do the same arithmetic.
    relief: list[float]
    #: Metres, lowest and highest, so the page can say what it is drawing.
    lowest: float
    highest: float
    source: str
    licence: str
    attribution: str
    #: 0.01 m for a DGM1. 1.0 for Baden-Württemberg's INSPIRE coverage, which
    #: cannot see a 20 m garden's own fall at all.
    vertical_step_m: float


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
    month: Annotated[int | None, Query(ge=3, le=10)] = None,
) -> LightMap | None:
    """The stored map, or null when nothing has been drawn yet.

    `month` asks for one month instead of the season, computed on the spot and
    not stored. March to October, the same window the whole light model uses:
    a plant's December is not what decides where it can live, and a map of it
    would drag every German garden into shade.
    """
    garden = require_garden(conn, token)
    return _read(conn, garden.garden_id, month)


@router.post("/{token}/light", response_model=LightMap | None)
def rebuild_light_map(
    token: str,
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
    garden = require_garden(conn, token)
    # The one place the ground is fetched. A survey answers in seconds, which is
    # too long for a page load and fine for a button somebody pressed.
    standing = load_garden(conn, garden.garden_id)
    ensure_terrain(conn, standing)
    # After the ground, because a raw surface model is only object heights once
    # the terrain has been taken off it.
    measure_buildings(conn, load_garden(conn, garden.garden_id))
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
    if month is not None:
        fresh = month_grid(conn, garden, month)
        if fresh is not None:
            grid, computed_at, signature = fresh, now(), signature_of(garden)
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
        stale=signature != signature_of(garden),
    )


__all__ = ["MONTHS", "router"]
