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
from ninanatur.solar.position import Location, SunPosition, sun_position
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
    casting a many-cornered roof is the dear part (review, 2026-09-28) — and
    once more a step taller or lower, for what a height would move."""
    location = Location(latitude=garden.latitude, longitude=garden.longitude)
    cast: dict[int, _Cast | None] = {}
    found: list[Reading | None] = []
    for mark in marks:
        if mark.element_id not in cast:
            element = caster(garden, mark.element_id)
            cast[mark.element_id] = None if element is None else _Cast(element)
        thing = cast[mark.element_id]
        sun = sun_position(location, mark.seen_at)
        if thing is None or sun.altitude <= MIN_ALTITUDE:
            found.append(None)
            continue
        reading = read_edge(thing.obstacle, sun, mark.x, mark.y)
        if reading is not None and reading.height_m is not None:
            reading = _as_height(reading, thing.moved(reading, sun))
        found.append(reading)
    return found


#: How far a height is changed to see what it moves, in metres: a metre, or
#: half a low thing's height.
STEP_M = 1.0
#: Below this share of what a height moves a block's edge, no height is said:
#: the number would be more than four times a block's, and say more about the
#: shape than about the height.
ENOUGH = 0.25


class _Cast:
    """A thing as the model casts it and, when asked, as it would cast a step
    taller or lower — as the gardener's correction of its height makes it:
    eaves they gave stay where they are, eaves and a crown base the model
    assumes move with it, and eaves above a lowered ridge come down to it."""

    def __init__(self, element: Element) -> None:
        self.element = element
        self.obstacle = casting(element)
        self._stepped: dict[float, Obstacle] = {}

    def moved(self, reading: Reading, sun: SunPosition) -> float:
        """How far a metre of height carries this very point of the edge, in
        the direction the mark asks for: lower where the model's shadow
        reaches past it, taller where it stops short. Probed upward only, a
        roof's own switches — eaves clamped to the ridge, the shallowest pitch
        that counts, eaves or ridge deciding the edge — answered for the wrong
        direction: a flat-cast gable said no height, or 2.5 m where 0.75 was
        right (review of 45eb56a)."""
        height = self.element.height or 0.0
        lower = reading.along_m > 0
        step = min(STEP_M, height / 2) if lower else STEP_M
        if step <= 0:
            return 0.0
        key = -step if lower else step
        if key not in self._stepped:
            self._stepped[key] = casting(replace(self.element, height=height + key))
        return reach_past(self._stepped[key], sun, reading.nearest, back=lower) / step


def _as_height(reading: Reading, moved: float) -> Reading:
    """The height the way along the sun amounts to: `moved` is how far a
    metre of the thing carries this point of the edge, where cot h was
    assumed. Since roofs cast as roofs (doc 120), a gable's far edge is often
    its eaves', which the ridge's height hardly moves — and "as though a metre
    lower" was then a height no correction could satisfy (review of stage 3,
    2026-09-28). No point of an edge moves faster than a block's; one that
    seems to is a gap between two shadows closing, and is taken at a block's
    rate. Where a metre moves it less than `ENOUGH` of a block's, no height is
    said."""
    block = 1.0 / math.tan(math.radians(reading.altitude))
    moved = min(moved, block)
    if moved < ENOUGH * block:
        return replace(reading, height_m=None)
    return replace(reading, height_m=reading.along_m / moved)


__all__ = ["MAX_MARKS", "ShadowMark", "add_mark", "caster", "delete_mark", "marks_of",
           "readings", "sun_up"]
