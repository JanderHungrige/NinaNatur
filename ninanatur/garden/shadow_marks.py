"""Keeping where the gardener saw a shadow end, and reading the model against it.

Doc 122. A mark is an observation: a point, the standing thing whose shadow
ended there, and the moment. Only that is stored. The model's answer — the
thing cast as the light model casts it (`garden.casting`), its shadow at that
moment, and the way from the mark to that shadow's edge — is worked out on
every read, so a mark keeps measuring the model as it changes, and as the
gardener corrects the height it disagrees with.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from ninanatur.garden.casting import casting, casts
from ninanatur.garden.elements import now
from ninanatur.garden.models import Element, Garden
from ninanatur.solar.position import Location, sun_position
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle
from ninanatur.solar.shadow_edge import Reading, reach_past, read_edge

#: How many marks a garden keeps. An instrument, not a diary: a handful at
#: different hours says what there is to say, and each is read on every look.
MAX_MARKS = 50


@dataclass(frozen=True)
class ShadowMark:
    """Where the shadow of one standing thing was seen to end, and when."""

    mark_id: int
    element_id: int
    x: float
    y: float
    #: UTC.
    seen_at: datetime


def add_mark(conn: sqlite3.Connection, garden_id: int, element_id: int, x: float, y: float,
             seen_at: datetime) -> ShadowMark | None:
    """Keep one observation, or None where the garden already keeps
    `MAX_MARKS`. Counted and written in one statement, so two at once cannot
    both slip under the limit. The caller has checked the thing and the moment."""
    seen = seen_at.astimezone(UTC).replace(microsecond=0)
    cursor = conn.execute(
        "INSERT INTO shadow_mark (garden_id, element_id, x, y, seen_at, created_at)"
        " SELECT ?, ?, ?, ?, ?, ?"
        " WHERE (SELECT COUNT(*) FROM shadow_mark WHERE garden_id = ?) < ?",
        (garden_id, element_id, x, y, seen.isoformat(timespec="seconds"), now(),
         garden_id, MAX_MARKS),
    )
    conn.commit()
    if cursor.rowcount == 0 or cursor.lastrowid is None:
        return None
    return ShadowMark(mark_id=int(cursor.lastrowid), element_id=element_id, x=x, y=y,
                      seen_at=seen)


def marks_of(conn: sqlite3.Connection, garden_id: int) -> list[ShadowMark]:
    """A garden's marks, oldest first."""
    rows = conn.execute(
        "SELECT mark_id, element_id, x, y, seen_at FROM shadow_mark WHERE garden_id = ?"
        " ORDER BY seen_at, mark_id", (garden_id,),
    ).fetchall()
    return [ShadowMark(mark_id=int(r["mark_id"]), element_id=int(r["element_id"]),
                       x=float(r["x"]), y=float(r["y"]),
                       seen_at=datetime.fromisoformat(str(r["seen_at"]))) for r in rows]


def delete_mark(conn: sqlite3.Connection, garden_id: int, mark_id: int) -> bool:
    """Forget one mark of this garden's. False where it has none by that id."""
    cursor = conn.execute("DELETE FROM shadow_mark WHERE garden_id = ? AND mark_id = ?",
                          (garden_id, mark_id))
    conn.commit()
    return cursor.rowcount > 0


def caster(garden: Garden, element_id: int) -> Element | None:
    """The standing thing a mark can be of: one of this garden's that casts."""
    return next((e for e in garden.obstacles if e.element_id == element_id and casts(e)), None)


def sun_up(garden: Garden, seen_at: datetime) -> bool:
    """Whether the sun was high enough at that moment for the model to cast."""
    location = Location(latitude=garden.latitude, longitude=garden.longitude)
    return sun_position(location, seen_at).altitude > MIN_ALTITUDE


def readings(garden: Garden, marks: list[ShadowMark]) -> list[Reading | None]:
    """Each mark read against the model as it is now — None where there is
    nothing to read: the thing no longer casts, or the sun, by the model's own
    sampling, was too low. Each thing is cast once, however many marks it has:
    casting a many-cornered roof is the dear part (review, 2026-09-28) — once
    as it is and once a metre taller, for what a height would move."""
    location = Location(latitude=garden.latitude, longitude=garden.longitude)
    cast: dict[int, tuple[Obstacle, Obstacle] | None] = {}
    found: list[Reading | None] = []
    for mark in marks:
        if mark.element_id not in cast:
            element = caster(garden, mark.element_id)
            cast[mark.element_id] = None if element is None else (
                casting(element), casting(_taller(element)))
        pair = cast[mark.element_id]
        sun = sun_position(location, mark.seen_at)
        if pair is None or sun.altitude <= MIN_ALTITUDE:
            found.append(None)
            continue
        reading = read_edge(pair[0], sun, mark.x, mark.y)
        if reading is not None and reading.height_m is not None:
            reading = _as_height(reading, reach_past(pair[1], sun, reading.nearest))
        found.append(reading)
    return found


def _taller(element: Element) -> Element:
    """The thing a metre taller, as the gardener's correction of its height
    makes it: eaves they gave stay where they are; eaves and a crown base the
    model assumes rise with it."""
    return replace(element, height=(element.height or 0.0) + 1.0)


def _as_height(reading: Reading, moved: float) -> Reading:
    """The height the way along the sun amounts to: `moved` is how far a
    metre more of the thing carries this very point of the edge, where cot h
    was assumed. Since roofs cast as roofs (doc 120), a gable's far edge is
    often its eaves' at a high sun, which the ridge's height hardly moves —
    and "as though a metre lower" was then a height no correction could
    satisfy (review of stage 3, 2026-09-28). Where a metre moves the edge
    less than a tenth of what it moves a block's, no height is said."""
    block = 1.0 / math.tan(math.radians(reading.altitude))
    if moved < 0.1 * block:
        return replace(reading, height_m=None)
    return replace(reading, height_m=reading.along_m / moved)


__all__ = ["MAX_MARKS", "ShadowMark", "add_mark", "caster", "delete_mark", "marks_of",
           "readings", "sun_up"]
