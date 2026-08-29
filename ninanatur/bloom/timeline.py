"""The garden's bloom year, and the gaps in it.

Twelve months — not twenty-four. Every flowering bound in the catalogue is an
integer month, so half-month buckets would be the same invented precision this
project refuses for flower colour and for sun hours.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from enum import Enum

from ninanatur.data.interactions import german_partner_counts
from ninanatur.data.traits import resolve_trait
from ninanatur.garden.models import Garden

# Gaps are only reported inside the growing season. The winter trough is not a
# finding, and reporting "nothing flowers in January" would train users to ignore
# the feature entirely.
SEASON_MONTHS: tuple[int, ...] = (3, 4, 5, 6, 7, 8, 9, 10)

# A month counts as a gap below this share of the garden's own best month.
# Relative rather than absolute so the number means "compared to your peak",
# which a user can interpret. A quarter is the point where a month looks bare
# next to the same garden in July.
GAP_THRESHOLD = 0.25


class TimelineMode(Enum):
    """How much a flowering planting is worth."""

    FORAGE = "forage"   # weighted by counted German insect partners
    VISUAL = "visual"   # every planting counts the same


@dataclass(frozen=True)
class MonthCoverage:
    """One month, and what is flowering in it."""

    month: int
    coverage: float
    species: tuple[str, ...]


@dataclass(frozen=True)
class Gap:
    """A run of consecutive months below the threshold."""

    months: tuple[int, ...]

    @property
    def length(self) -> int:
        return len(self.months)


@dataclass(frozen=True)
class Timeline:
    """The bloom year, with the reasoning kept attached."""

    mode: TimelineMode
    months: dict[int, MonthCoverage]
    gaps: list[Gap] = field(default_factory=list)
    plantings_total: int = 0
    plantings_without_interaction_data: int = 0

    @property
    def is_empty(self) -> bool:
        return self.plantings_total == 0


def flowering_months(start: int | None, end: int | None) -> tuple[int, ...]:
    """Expand a flowering interval into the months it covers.

    Handles the wrap explicitly: 132 species in the catalogue start after they
    end (November to February and similar), and `range(start, end + 1)` yields
    nothing for exactly those — the ones covering the hardest part of the year.
    The failure is silent, which is why it is expanded here and pinned by a test.
    """
    if start is None or end is None:
        return ()
    if not (1 <= start <= 12 and 1 <= end <= 12):
        return ()
    if start <= end:
        return tuple(range(start, end + 1))
    return tuple(range(start, 13)) + tuple(range(1, end + 1))


def _forage_weight(conn: sqlite3.Connection, taxon_id: int) -> tuple[float, bool]:
    """How much a planting of this species is worth to insects.

    Returns the weight and whether interaction data was missing. A species GloBI
    has never recorded contributes its plain quantity rather than zero: unknown
    is not the same as worthless, which is the rule this whole project runs on.
    """
    counts = german_partner_counts(conn, taxon_id)
    if counts is None:
        return 1.0, True
    # Diminishing returns: the difference between 5 and 50 partners matters more
    # than between 500 and 545, and raw counts would let one well-studied plant
    # dominate a whole month.
    return 1.0 + counts.german**0.5, False


def garden_timeline(
    conn: sqlite3.Connection,
    garden: Garden,
    mode: TimelineMode = TimelineMode.FORAGE,
) -> Timeline:
    """Twelve months of flowering for a whole garden."""
    raw: dict[int, float] = dict.fromkeys(range(1, 13), 0.0)
    names: dict[int, set[str]] = {m: set() for m in range(1, 13)}
    total = 0
    unknown_interactions = 0

    for bed in garden.beds:
        for planting in bed.plantings:
            # No taxon, no data: it is on the plan and out of the maths.
            if planting.taxon_id is None:
                continue
            total += 1
            start = resolve_trait(conn, planting.taxon_id, "flowering_start_month")
            end = resolve_trait(conn, planting.taxon_id, "flowering_end_month")
            active = flowering_months(
                int(start.value_num) if start and start.value_num is not None else None,
                int(end.value_num) if end and end.value_num is not None else None,
            )
            if not active:
                continue

            if mode is TimelineMode.FORAGE:
                weight, missing = _forage_weight(conn, planting.taxon_id)
                unknown_interactions += int(missing)
            else:
                weight = 1.0

            for month in active:
                raw[month] += weight * planting.quantity
                names[month].add(planting.display_name)

    peak = max(raw.values()) if raw else 0.0
    months = {
        m: MonthCoverage(
            month=m,
            coverage=round(raw[m] / peak, 4) if peak > 0 else 0.0,
            species=tuple(sorted(names[m])),
        )
        for m in range(1, 13)
    }
    return Timeline(
        mode=mode,
        months=months,
        gaps=[] if total == 0 else _find_gaps(months),
        plantings_total=total,
        plantings_without_interaction_data=unknown_interactions,
    )


def _find_gaps(months: dict[int, MonthCoverage]) -> list[Gap]:
    """Runs of consecutive season months below the threshold."""
    gaps: list[Gap] = []
    run: list[int] = []
    for month in SEASON_MONTHS:
        if months[month].coverage < GAP_THRESHOLD:
            run.append(month)
        elif run:
            gaps.append(Gap(months=tuple(run)))
            run = []
    if run:
        gaps.append(Gap(months=tuple(run)))
    return gaps
