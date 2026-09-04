"""What colour each bed is, month by month.

The timeline says *when* a garden flowers. This says *where*, which is the
question a plan is for.

Computed here rather than in the browser: the frontend has a bed's plantings but
neither their flowering windows nor their colours, and shipping those per
planting to render a swatch would send the catalogue to the client.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ninanatur.bloom.timeline import flowering_months
from ninanatur.data.traits import resolve_trait
from ninanatur.garden.canopy import canopy_of
from ninanatur.garden.store import load_garden

MONTHS = tuple(range(1, 13))


def _window(conn: sqlite3.Connection, taxon_id: int) -> frozenset[int]:
    start = resolve_trait(conn, taxon_id, "flowering_start_month")
    end = resolve_trait(conn, taxon_id, "flowering_end_month")
    if start is None or end is None or start.value_num is None or end.value_num is None:
        return frozenset()
    # The same wrap-aware function the month filter was fixed to use: 132 German
    # species flower across the year end, and an integer comparison loses all of
    # them in every month.
    return frozenset(flowering_months(int(start.value_num), int(end.value_num)))


def _room(conn: sqlite3.Connection, taxon_id: int) -> float | None:
    """How much ground one of these wants, in m².

    Estimated from height, because the catalogue records no spread at all — GIFT
    gives `height_max_m` and nothing about width, and it gives that for 3,952 of
    8,939 species. So this is null more often than not, and where it exists it
    is a rule of thumb.

    It sizes a cluster on the plan and nothing else. `canopy.py` states the rule
    this obeys: a derived number that looks measured is worse than no number, so
    the plan draws a soft blob and never a figure.
    """
    height = resolve_trait(conn, taxon_id, "height_max_m")
    form = resolve_trait(conn, taxon_id, "growth_form")
    canopy = canopy_of(
        None if height is None else height.value_num,
        None if form is None else form.value_text,
    )
    return None if canopy is None else canopy.area_m2


def _colour(conn: sqlite3.Connection, taxon_id: int) -> str | None:
    """What to draw for this species.

    Nothing special here any more. A colour somebody entered by hand is a `trait`
    row like any other, marked `manual`, and `resolve_trait` already knows it
    ranks behind every published source. The per-garden override this used to
    carry is gone with the table it read from.
    """
    trait = resolve_trait(conn, taxon_id, "flower_colour")
    return None if trait is None else trait.value_text


def garden_palette(conn: sqlite3.Connection, garden_id: int) -> dict[str, Any]:
    """Per bed, per month: which colours are in flower and what we cannot say.

    `unknown` is a count, not a colour. Flower colour is recorded for 590 of
    8,939 species, so a bed rendered green, grey or beige for "we do not know"
    would be an answer the data does not support — and a fill is the most
    confident thing a UI can draw.
    """
    garden = load_garden(conn, garden_id)
    windows: dict[int, frozenset[int]] = {}
    colours: dict[int, str | None] = {}
    room: dict[int, float | None] = {}

    beds: list[dict[str, Any]] = []
    for bed in garden.beds:
        per_month: dict[int, tuple[set[str], int, int]] = {
            m: (set(), 0, 0) for m in MONTHS
        }
        # Per cluster as well as per bed. A colour band only ever needed to know
        # which colours were in the bed; a dot per cluster has to know which
        # cluster, and this is the one place that resolves colour — the
        # gardener's own note included.
        per_planting: list[dict[str, Any]] = []
        for planting in bed.plantings:
            # No taxon, no data — it is on the plan and out of the colours.
            # Still listed, because it is still a cluster to draw: grey, and in
            # no month.
            if planting.taxon_id is None:
                per_planting.append(
                    {
                        "planting_id": planting.planting_id,
                        "taxon_id": None,
                        "colour": None,
                        "months": [],
                        "space_m2": None,
                    }
                )
                continue
            tid = planting.taxon_id
            if tid not in windows:
                windows[tid] = _window(conn, tid)
                colours[tid] = _colour(conn, tid)
            if tid not in room:
                room[tid] = _room(conn, tid)
            per_planting.append(
                {
                    "planting_id": planting.planting_id,
                    "taxon_id": tid,
                    "colour": colours[tid],
                    "months": sorted(windows[tid]),
                    "space_m2": room[tid],
                }
            )
            for month in windows[tid]:
                found, unknown, flowering = per_month[month]
                colour = colours[tid]
                if colour is None:
                    unknown += 1
                else:
                    found.add(colour.lower())
                per_month[month] = (found, unknown, flowering + 1)

        beds.append(
            {
                "bed_id": bed.bed_id,
                "months": [
                    {
                        "month": m,
                        # Sorted so the same bed renders its bands the same way
                        # on every frame of the playback.
                        "colours": sorted(per_month[m][0]),
                        "unknown": per_month[m][1],
                        "flowering": per_month[m][2],
                    }
                    for m in MONTHS
                ],
                "plantings": per_planting,
            }
        )
    return {"beds": beds}
