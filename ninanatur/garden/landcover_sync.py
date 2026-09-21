"""Getting a garden's surroundings from OpenStreetMap, once (doc 114).

**At creation**, from the map import, around the exact centre of the outline
the garden was drawn from — the anchor its streets and houses were placed by.

**On the shade rebuild** for a garden that has none yet: one made before this
existed, or one whose first fetch failed. The stored anchor is rounded to four
places (`store.create_garden`), which puts a fetch from it up to about 6 m off
the streets and houses the import placed from the exact one. Where the garden
holds OpenStreetMap's streets, the same streets are fetched again and the
offset is read off them; where it holds none, the areas are placed from the
stored anchor and the page is as far off as that.

Either way it runs **after the answer has gone out** (`fetch_later`,
`add_later`, as background tasks) with one attempt, and a failure costs the
colours and nothing else. It was inside the rebuild at first, and the review
found "Sonne & Schatten" — the button the owner had just called endless — then
waited on up to two Overpass requests with retries, again on every press
while Overpass failed. A failure is remembered for `FAILURE_PAUSE_S` now.
"""
from __future__ import annotations

import logging
import math
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from ninanatur.garden.models import Garden
from ninanatur.garden.objects import ObjectKind
from ninanatur.garden.terrain_sync import is_precise
from ninanatur.geo.landcover_clip import (
    Box,
    LandArea,
    Point,
    box_around,
    degrees_of,
    in_garden,
)
from ninanatur.geo.landcover_store import fetched, save_landcover
from ninanatur.geo.osm_landcover import fetch_once, landcover_in
from ninanatur.geo.osm_streets import streets_in
from ninanatur.geo.projection import LatLon, to_metres

log = logging.getLogger(__name__)

#: How far a stored street point may be from the same node fetched again. The
#: rounding moves the anchor at most 5.6 m north–south and less east–west.
REACH_M = 8.0
#: The offset is read to this, which is finer than the areas are rounded to.
BIN_M = 0.1
#: How many street points must agree on one offset before it is believed.
MIN_AGREEING = 3
#: How long a garden whose fetch failed is left alone. In memory: a restart
#: forgets it, which costs one more attempt and no more.
FAILURE_PAUSE_S = 6 * 3600
#: By share token: SQLite gives a deleted garden's id to the next one, and a new
#: garden inherited its predecessor's pause (review, 2026-09-21). A token is
#: never given out twice.
_failed_at: dict[str, float] = {}
#: Fetches running now, by share token, and how many may run at once. The heavy
#: slot no longer bounds them (it is let go before the answer is sent), so a
#: second press while Overpass is slow started a second fetch of the same land,
#: and a handful of presses held as many server threads (review, 2026-09-21).
#: A fetch that finds its garden already being fetched, or no room, is skipped
#: and records no failure: the next rebuild asks again.
MAX_BACKGROUND_FETCHES = 2
_running: set[str] = set()
_room = threading.BoundedSemaphore(MAX_BACKGROUND_FETCHES)
_claims = threading.Lock()


@contextmanager
def background_connection() -> Iterator[sqlite3.Connection | None]:
    """A connection of the background task's own: the request's is closed by
    the time it runs. Replaced in tests (`tests/conftest.py`) by one that opens
    nothing, so no test can write to a real database from here."""
    from ninanatur.ingest.db import connect, database_path

    conn = connect(database_path(), same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


def fetch_later(token: str) -> None:
    """`ensure_landcover` for a garden, after its rebuild has answered. By
    token: the garden may be gone, and its id somebody else's, by then."""
    _in_background(token, lambda conn: _ensure_by_token(conn, token))


def add_later(token: str, anchor: LatLon, outline: list[list[float]]) -> None:
    """`add_landcover` for a garden just made, after its answer has gone out."""
    _in_background(token, lambda conn: add_landcover(conn, token, anchor, outline))


def _in_background(token: str, work: Callable[[sqlite3.Connection], object]) -> None:
    if not _claim(token):
        log.info("landcover for %s skipped: already running, or no room", token[:6])
        return
    try:
        with background_connection() as conn:
            if conn is not None:
                work(conn)
    except Exception:  # noqa: BLE001 — decoration, after the answer; logged
        log.warning("landcover in the background failed", exc_info=True)
    finally:
        with _claims:
            _running.discard(token)
            _room.release()


def _claim(token: str) -> bool:
    with _claims:
        if token in _running or not _room.acquire(blocking=False):
            return False
        _running.add(token)
        return True


def _ensure_by_token(conn: sqlite3.Connection, token: str) -> None:
    from ninanatur.garden.store import garden_by_token

    garden = garden_by_token(conn, token)
    if garden is not None:
        ensure_landcover(conn, garden)


def _paused(token: str) -> bool:
    failed = _failed_at.get(token)
    return failed is not None and time.monotonic() - failed < FAILURE_PAUSE_S


def _failed(token: str | None) -> None:
    """Remember a failure, and forget the ones whose pause is over."""
    now = time.monotonic()
    for over in [key for key, at in _failed_at.items() if now - at >= FAILURE_PAUSE_S]:
        del _failed_at[over]
    if token is not None:
        _failed_at[token] = now


def _id_of(conn: sqlite3.Connection, token: str) -> int | None:
    row = conn.execute("SELECT garden_id FROM garden WHERE share_token = ?", (token,)).fetchone()
    return None if row is None else int(row[0])


def add_landcover(conn: sqlite3.Connection, token: str, anchor: LatLon,
                  outline: list[list[float]]) -> None:
    """A new garden's surroundings, around the anchor its outline was drawn from.

    Overpass is a free service with no SLA: a refusal costs the colours, not
    the garden, as with the streets.
    """
    garden_id = _id_of(conn, token)
    if garden_id is None:
        return
    box = box_around([(p[0], p[1]) for p in outline])
    try:
        found = landcover_in(*degrees_of(box, anchor), centre=anchor)
        areas = in_garden(found, anchor, box)
    except Exception:  # noqa: BLE001 — the garden matters more
        log.warning("landcover unavailable, garden %s made without it", garden_id,
                    exc_info=True)
        _failed(token)
        return
    _save_if_still(conn, garden_id, token, areas, "map")


def ensure_landcover(conn: sqlite3.Connection, garden: Garden) -> bool:
    """Fetch this garden's surroundings if it has none yet; whether it has them now.

    Under the terrain's guard: a garden from before the precise anchor sits up
    to 6.6 km from where it was drawn, and its neighbourhood would be somebody
    else's.
    """
    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    if not is_precise(anchor):
        log.info("not fetching landcover: garden %s predates the precise anchor",
                 garden.garden_id)
        return False
    if fetched(conn, garden.garden_id):
        return True
    if _paused(garden.share_token):
        return False
    box = box_around(_plot_of(garden))
    try:
        found = landcover_in(*degrees_of(box, anchor), centre=anchor)
    except Exception:
        # Logged with its context and swallowed on purpose: the light is what
        # was asked for, and a rebuild without colours is yesterday's plan.
        log.warning("landcover failed for garden %s", garden.garden_id, exc_info=True)
        _failed(garden.share_token)
        return False
    shift, placed_by = _alignment(garden, anchor, box)
    return _save_if_still(conn, garden.garden_id, garden.share_token,
                          in_garden(found, anchor, box, shift), placed_by)


def _save_if_still(conn: sqlite3.Connection, garden_id: int, token: str,
                   areas: list[LandArea], placed_by: str) -> bool:
    """Save, unless the garden went while Overpass was asked: its id may be
    another garden's by now, and that garden's land is elsewhere."""
    if _id_of(conn, token) != garden_id:
        log.info("landcover for %s not kept: the garden is gone", token[:6])
        return False
    save_landcover(conn, garden_id, areas, placed_by)
    return True


def _plot_of(garden: Garden) -> list[Point]:
    """What the box is drawn around: the plot, or else what the gardener drew,
    or else the anchor. Never the streets — a way arrives at its full length."""
    plot = [p for e in garden.obstacles if e.kind == ObjectKind.GARDEN.value for p in e.footprint]
    drawn = [p for e in garden.elements
             if e.outline_source != "osm" and e.kind != ObjectKind.STREET.value
             for p in e.footprint]
    return plot or drawn or [(0.0, 0.0)]


def _alignment(garden: Garden, anchor: LatLon, box: Box) -> tuple[Point, str]:
    """How far to move areas placed from the stored anchor, and what said so."""
    stored = [(e.x + p[0], e.y + p[1]) for e in garden.obstacles
              if e.kind == ObjectKind.STREET.value and e.outline_source == "osm"
              for p in e.points or []]
    if not stored:
        return (0.0, 0.0), "anchor"
    try:
        found = streets_in(*degrees_of(box, anchor), fetch=fetch_once)
    except Exception:
        # The land is already fetched; placing it from the anchor loses metres,
        # losing it would lose the colours (review).
        log.warning("garden %s: streets for the offset unavailable", garden.garden_id,
                    exc_info=True)
        return (0.0, 0.0), "anchor"
    again = [to_metres(p, anchor) for street in found for p in street.centreline]
    offset = street_offset(stored, [(m.x, m.y) for m in again])
    if offset is None:
        log.info("garden %s: its streets did not agree on an offset", garden.garden_id)
        return (0.0, 0.0), "anchor"
    return offset, "streets"


def street_offset(stored: list[Point], again: list[Point]) -> Point | None:
    """The one offset most stored street points share with the same streets
    fetched again, or None where too few agree.

    Every pair of points within reach votes for their difference. The true
    offset is the same for every node of every street, so it gathers a vote
    from each; a pair of different nodes votes somewhere of its own.
    """
    near: defaultdict[tuple[int, int], list[Point]] = defaultdict(list)
    for x, y in again:
        near[(math.floor(x / REACH_M), math.floor(y / REACH_M))].append((x, y))
    votes: Counter[tuple[int, int]] = Counter()
    for sx, sy in stored:
        cx, cy = math.floor(sx / REACH_M), math.floor(sy / REACH_M)
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for ax, ay in near.get((gx, gy), ()):
                    if (ax - sx) ** 2 + (ay - sy) ** 2 <= REACH_M ** 2:
                        votes[(round((ax - sx) / BIN_M), round((ay - sy) / BIN_M))] += 1
    if not votes:
        return None
    (bx, by), count = votes.most_common(1)[0]
    return None if count < MIN_AGREEING else (bx * BIN_M, by * BIN_M)


__all__ = ["add_landcover", "add_later", "ensure_landcover", "fetch_later", "background_connection",
           "street_offset"]
