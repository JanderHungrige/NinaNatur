"""Marking where a shadow really ends — doc 122.

The instrument that reaches reality: the gardener says where the shadow of
their house ended at a moment they saw it, and the model's shadow of the
house at that moment is read against it. Its own router: an observation of the
garden is not a thing in it, and the light routes are about what the model
answers, not about what the gardener saw.

Both routes that read cast a thing's shadow — the dearest geometry the app
has, for a many-cornered roof — so they take a heavy slot, as the day's
playback does, and marking counts against its own allowance (review,
2026-09-28).
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from ninanatur.api import ratelimit
from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import require_garden
from ninanatur.api.schemas_marks import ShadowMarkIn, ShadowMarkOut, ShadowReadingOut
from ninanatur.garden.shadow_marks import (
    MAX_MARKS,
    ShadowMark,
    add_mark,
    caster,
    delete_mark,
    marks_of,
    readings,
    sun_up,
)
from ninanatur.solar.shadow_edge import Reading

router = APIRouter(prefix="/api/v1/gardens", tags=["shadow marks"])

#: How far ahead of the server's clock a mark's moment may be: a phone's clock
#: running a little fast is not a mark about the future.
CLOCK_SLACK = timedelta(minutes=5)
#: The largest id SQLite can hold; a larger one is no mark of anybody's.
MAX_ID = 2**63 - 1


def now() -> datetime:
    """The server's clock. Its own function, so a test can say what time it is."""
    return datetime.now(UTC)


def _out(mark: ShadowMark, found: Reading | None) -> ShadowMarkOut:
    reading = None if found is None else ShadowReadingOut(
        altitude=round(found.altitude, 2), azimuth=round(found.azimuth, 2),
        rings=[[[round(x, 2), round(y, 2)] for x, y in ring] for ring in found.rings],
        nearest=[round(found.nearest[0], 2), round(found.nearest[1], 2)],
        offset_m=round(found.offset_m, 2), edge=found.edge, model_longer=found.model_longer,
        along_m=round(found.along_m, 2), across_m=round(found.across_m, 2),
        height_m=None if found.height_m is None else round(found.height_m, 2),
        turned_deg=None if found.turned_deg is None else round(found.turned_deg, 1),
    )
    return ShadowMarkOut(mark_id=mark.mark_id, element_id=mark.element_id, x=mark.x, y=mark.y,
                         seen_at=mark.seen_at.astimezone(UTC).isoformat(timespec="seconds"),
                         reading=reading)


@router.get("/{token}/shadow-marks", response_model=list[ShadowMarkOut])
def shadow_marks(
    token: str,
    _slot: Annotated[None, Depends(ratelimit.heavy_slot, scope="function")],
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> list[ShadowMarkOut]:
    """Every mark of this garden's, each read against the model as it is now."""
    garden = require_garden(conn, token)
    marks = marks_of(conn, garden.garden_id)
    return [_out(mark, found) for mark, found in zip(marks, readings(garden, marks), strict=True)]


@router.post("/{token}/shadow-marks", response_model=ShadowMarkOut,
             status_code=status.HTTP_201_CREATED)
def mark_shadow(
    token: str,
    payload: ShadowMarkIn,
    request: Request,
    _slot: Annotated[None, Depends(ratelimit.heavy_slot, scope="function")],
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> ShadowMarkOut:
    """Keep where a shadow was seen to end, and read the model against it.

    A mark is an observation: of a thing of this garden's that casts, at a
    moment that has passed, with the sun high enough to cast at all.
    """
    ratelimit.check(conn, request, "shadow-marks")
    garden = require_garden(conn, token)
    if caster(garden, payload.element_id) is None:
        # The same answer whether the id is another garden's or nobody's.
        raise HTTPException(status_code=404, detail=f"no such element: {payload.element_id}")
    seen_at = payload.seen_at
    if seen_at > now() + CLOCK_SLACK:
        raise HTTPException(status_code=422, detail=(
            "Eine Markierung hält fest, was zu sehen war — dieser Zeitpunkt liegt in der Zukunft."))
    if not sun_up(garden, seen_at):
        raise HTTPException(status_code=422, detail=(
            "Zu diesem Zeitpunkt stand die Sonne zu tief, um einen Schatten zu werfen."))
    mark = add_mark(conn, garden.garden_id, payload.element_id, payload.x, payload.y, seen_at)
    if mark is None:
        raise HTTPException(status_code=409, detail=(
            f"Höchstens {MAX_MARKS} Markierungen je Garten — lösche eine ältere zuerst."))
    [found] = readings(garden, [mark])
    return _out(mark, found)


@router.delete("/{token}/shadow-marks/{mark_id}", status_code=status.HTTP_204_NO_CONTENT)
def forget_mark(
    token: str,
    mark_id: Annotated[int, Path(ge=1, le=MAX_ID)],
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> None:
    """Forget one mark."""
    garden = require_garden(conn, token)
    if not delete_mark(conn, garden.garden_id, mark_id):
        raise HTTPException(status_code=404, detail="no such mark")


__all__ = ["CLOCK_SLACK", "router"]
