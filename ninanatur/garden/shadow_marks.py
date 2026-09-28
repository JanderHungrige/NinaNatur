"""Keeping where the gardener saw a shadow end, and reading the model against it.

Doc 122. A mark is an observation: a point, the standing thing whose shadow
ended there, and the moment. Only that is stored. The model's answer — the
thing cast as the light model casts it (`garden.casting`), its shadow at that
moment, and the way from the mark to that shadow's edge — is worked out on
every read, so a mark keeps measuring the model as it changes, and as the
gardener corrects the height it disagrees with.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from ninanatur.garden.casting import casting, casts
from ninanatur.garden.elements import now
from ninanatur.garden.models import Element, Garden
from ninanatur.solar.position import Location, sun_position
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle
from ninanatur.solar.shadow_edge import Reading, read_edge

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
    casting a many-cornered roof is the dear part (review, 2026-09-28)."""
    location = Location(latitude=garden.latitude, longitude=garden.longitude)
    cast: dict[int, Obstacle | None] = {}
    found: list[Reading | None] = []
    for mark in marks:
        if mark.element_id not in cast:
            element = caster(garden, mark.element_id)
            cast[mark.element_id] = None if element is None else casting(element)
        obstacle = cast[mark.element_id]
        sun = sun_position(location, mark.seen_at)
        found.append(None if obstacle is None or sun.altitude <= MIN_ALTITUDE
                     else read_edge(obstacle, sun, mark.x, mark.y))
    return found


__all__ = ["MAX_MARKS", "ShadowMark", "add_mark", "caster", "delete_mark", "marks_of",
           "readings", "sun_up"]
