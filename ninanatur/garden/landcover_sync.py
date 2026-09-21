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

Either way a failure costs the colours and nothing else: a garden is made
without them, a rebuild computes its light without them, and the next rebuild
asks again.
"""
from __future__ import annotations

import logging
import math
import sqlite3
from collections import Counter, defaultdict

from ninanatur.garden.models import Garden
from ninanatur.garden.objects import ObjectKind
from ninanatur.garden.terrain_sync import is_precise
from ninanatur.geo.landcover_clip import Box, Point, box_around, degrees_of, in_garden
from ninanatur.geo.landcover_store import fetched, save_landcover
from ninanatur.geo.osm_landcover import landcover_in
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


def add_landcover(conn: sqlite3.Connection, garden_id: int, anchor: LatLon,
                  outline: list[list[float]]) -> None:
    """A new garden's surroundings, around the anchor its outline was drawn from.

    Overpass is a free service with no SLA: a refusal costs the colours, not
    the garden, as with the streets.
    """
    box = box_around([(p[0], p[1]) for p in outline])
    try:
        found = landcover_in(*degrees_of(box, anchor), centre=anchor)
        areas = in_garden(found, anchor, box)
    except Exception:  # noqa: BLE001 — the garden matters more
        log.warning("landcover unavailable, garden %s made without it", garden_id,
                    exc_info=True)
        return
    save_landcover(conn, garden_id, areas, "map")


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
    box = box_around(_plot_of(garden))
    try:
        found = landcover_in(*degrees_of(box, anchor), centre=anchor)
        shift, placed_by = _alignment(garden, anchor, box)
        areas = in_garden(found, anchor, box, shift)
    except Exception:
        # Logged with its context and swallowed on purpose: the light is what
        # was asked for, and a rebuild without colours is yesterday's plan.
        log.warning("landcover failed for garden %s", garden.garden_id, exc_info=True)
        return False
    save_landcover(conn, garden.garden_id, areas, placed_by)
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
    again = [to_metres(p, anchor) for street in streets_in(*degrees_of(box, anchor))
             for p in street.centreline]
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


__all__ = ["add_landcover", "ensure_landcover", "street_offset"]
