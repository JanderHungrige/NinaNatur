"""What to change, and what it buys.

A score without an action is a verdict. This turns it into "plant this instead of
that". Changes are ranked by marginal gain, which is defensible rather than merely
cheap because `18-insect-score` is submodular — a property that module asserts
directly, and that this one depends on.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from ninanatur.api.search import SearchFilters, load_candidates, rank_plants
from ninanatur.bloom.score import (
    MONTH_SATURATION,
    ScoreResult,
    garden_score,
    species_forage,
)
from ninanatur.bloom.timeline import SEASON_MONTHS, flowering_months
from ninanatur.data.interactions import german_partner_counts
from ninanatur.fit.score import SiteVector
from ninanatur.garden.models import Garden

MONTH_NAMES = {
    3: "März", 4: "April", 5: "Mai", 6: "Juni", 7: "Juli",
    8: "August", 9: "September", 10: "Oktober",
}
MAX_SUGGESTIONS = 8
# How many of the best-fitting candidates to consider per bed. A cap, not a filter.
CANDIDATE_POOL = 60
# A candidate must actually suit the bed, not merely be among the least bad.
# 0.3 is roughly the "borderline" band from 03-niche-fit; below it the species is
# in the wrong place, and raising the score by planting something that will not
# survive is not an improvement.
MIN_FIT = 0.3
# Below this share of a candidate's gain, the gain is spread rather than aimed at
# a gap, and the explanation should talk about partners instead of months.
GAP_SHARE = 0.6


@dataclass(frozen=True)
class Change:
    """One proposed change, with what it gains and why."""

    taxon_id: int
    canonical_name: str
    bed_id: int
    bed_name: str
    gain: float
    resulting_score: float
    reason: str
    german_partners: int | None = None
    replaces_planting_id: int | None = None
    replaces_name: str | None = None


@dataclass
class Improvements:
    """Everything worth doing to this garden, best first."""

    current_score: float
    additions: list[Change] = field(default_factory=list)
    swaps: list[Change] = field(default_factory=list)


def marginal_gain(
    raw_month: dict[int, float], forage: float, months: tuple[int, ...]
) -> float:
    """What adding this much forage in these months would gain.

    The saturation is applied per month, which is what makes more-of-the-same in
    an already-full month worth nothing — the same property the score is built on,
    arrived at directly instead of by rescoring the garden.
    """
    gain = 0.0
    for month in months:
        if month not in raw_month:
            continue  # outside the growing season
        before = min(raw_month[month], MONTH_SATURATION)
        after = min(raw_month[month] + forage, MONTH_SATURATION)
        gain += after - before
    return gain


def _to_score(total_gain: float) -> float:
    """Convert a forage gain into the score's 0-100 scale."""
    return 100.0 * total_gain / (len(SEASON_MONTHS) * MONTH_SATURATION)


def _reason(months: tuple[int, ...], raw_month: dict[int, float], partners: int | None) -> str:
    """One sentence naming why the score moves, not by how much."""
    empty = [m for m in months if raw_month.get(m, MONTH_SATURATION) <= 0.0]
    if empty:
        names = " und ".join(MONTH_NAMES[m] for m in empty[:2])
        return f"schließt die Lücke im {names}"
    if partners:
        return f"bringt {partners} erfasste deutsche Partnerarten mit"
    return "erweitert die Tracht in dieser Zeit"


def _candidate_forage(
    conn: sqlite3.Connection, taxon_id: int, origin: str
) -> tuple[float, int | None]:
    counts = german_partner_counts(conn, taxon_id)
    partners = counts.german if counts else None
    return species_forage(partners or 0, origin), partners


def garden_improvements(conn: sqlite3.Connection, garden: Garden) -> Improvements:
    """Rank additions and swaps by what they would gain."""
    current: ScoreResult = garden_score(conn, garden)
    raw = {m: current.raw_month.get(m, 0.0) for m in SEASON_MONTHS}
    planted = {p.taxon_id for bed in garden.beds for p in bed.plantings}
    candidates = load_candidates(conn)

    additions: list[Change] = []
    swaps: list[Change] = []

    for bed in garden.beds:
        axes = bed.site_axes
        if not axes:
            continue
        # Same fit and nativeness filters as a suggestion: a change that raises
        # the score and kills the plant is not an improvement.
        fitting = rank_plants(
            candidates,
            SiteVector(values=axes),
            SearchFilters(
                exclude_woody=True,
                exclude_introduced=True,
                exclude_taxa=frozenset(planted),
            ),
        )

        for scored in fitting[:CANDIDATE_POOL]:
            if scored.score < MIN_FIT:
                # Ranked candidates are sorted, so everything after this is worse.
                break
            plant = scored.plant
            origin = plant.text("native_de") or "unknown"
            forage, partners = _candidate_forage(conn, plant.taxon_id, origin)
            months = flowering_months(
                int(plant.number("flowering_start_month") or 0) or None,
                int(plant.number("flowering_end_month") or 0) or None,
            )
            if not months:
                continue

            gain = _to_score(marginal_gain(raw, forage, months))
            if gain <= 0:
                continue
            additions.append(
                Change(
                    taxon_id=plant.taxon_id,
                    canonical_name=plant.canonical_name,
                    bed_id=bed.bed_id,
                    bed_name=bed.name,
                    gain=round(gain, 2),
                    resulting_score=round(current.score + gain, 1),
                    reason=_reason(months, raw, partners),
                    german_partners=partners,
                )
            )

            # A swap: the same candidate, in place of the weakest thing here.
            for planting in bed.plantings:
                existing = next(
                    (c for c in current.by_species if c.taxon_id == planting.taxon_id), None
                )
                if existing is None:
                    continue
                without = {m: raw[m] for m in raw}
                for month in existing.months:
                    if month in without:
                        without[month] = max(0.0, without[month] - existing.forage)
                after_removal = sum(min(v, MONTH_SATURATION) for v in without.values())
                after_swap = after_removal + marginal_gain(without, forage, months)
                now = sum(min(v, MONTH_SATURATION) for v in raw.values())
                swap_gain = _to_score(after_swap - now)
                if swap_gain <= 0:
                    continue
                swaps.append(
                    Change(
                        taxon_id=plant.taxon_id,
                        canonical_name=plant.canonical_name,
                        bed_id=bed.bed_id,
                        bed_name=bed.name,
                        gain=round(swap_gain, 2),
                        resulting_score=round(current.score + swap_gain, 1),
                        reason=_reason(months, without, partners),
                        german_partners=partners,
                        replaces_planting_id=planting.planting_id,
                        replaces_name=planting.canonical_name,
                    )
                )

    additions.sort(key=lambda c: -c.gain)
    swaps.sort(key=lambda c: -c.gain)
    return Improvements(
        current_score=current.score,
        additions=additions[:MAX_SUGGESTIONS],
        swaps=swaps[:MAX_SUGGESTIONS],
    )
