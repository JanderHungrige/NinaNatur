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


def _colour(conn: sqlite3.Connection, taxon_id: int) -> str | None:
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

    beds: list[dict[str, Any]] = []
    for bed in garden.beds:
        per_month: dict[int, tuple[set[str], int, int]] = {
            m: (set(), 0, 0) for m in MONTHS
        }
        for planting in bed.plantings:
            # No taxon, no data — it is on the plan and out of the colours.
            if planting.taxon_id is None:
                continue
            tid = planting.taxon_id
            if tid not in windows:
                windows[tid] = _window(conn, tid)
                colours[tid] = _colour(conn, tid)
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
            }
        )
    return {"beds": beds}
