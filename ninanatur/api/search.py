"""Ranking: score the candidates, apply the filters, order what survives.

The route's job is parameters in, schema out. The decision about what matches
lives here, and the decision about what one filter means lives in `filters.py`.
"""
from __future__ import annotations

from dataclasses import dataclass

from ninanatur.api.candidates import AXIS_PARAMS, PlantRow, ScoredPlant, load_candidates
from ninanatur.api.filters import (
    FilterCounts,
    SearchFilters,
    Verdict,
    excluded_outright,
    verdicts_for,
)
from ninanatur.fit.score import SiteVector, score_species

# The one filter that orders rather than removes; named so the two places that
# must treat it differently cannot drift apart.
COLOUR = "colour"

__all__ = [
    "AXIS_PARAMS",
    "FilterCounts",
    "PlantRow",
    "RankedResult",
    "ScoredPlant",
    "SearchFilters",
    "Verdict",
    "load_candidates",
    "rank_plants",
]


@dataclass(frozen=True)
class RankedResult:
    """The ordered list, plus what each active filter did to get there."""

    items: list[ScoredPlant]
    report: dict[str, FilterCounts]


def _order_key(scored: ScoredPlant, verdicts: dict[str, Verdict]) -> tuple[int, int, float]:
    """Known matches first, then unknowns, then colour mismatches — score within.

    Unknowns are kept only when the user asked for them, and even then they must
    not outrank a species that actually matches what was asked.
    """
    values = verdicts.values()
    unknown = 1 if any(v is Verdict.UNKNOWN for v in values) else 0
    mismatch = 1 if any(v is Verdict.MISMATCH for v in values) else 0
    return (mismatch, unknown, -scored.score)


def rank_plants(
    candidates: list[PlantRow],
    site: SiteVector,
    filters: SearchFilters,
    colour: str | None = None,
) -> RankedResult:
    """Score, filter and order candidates against one bed.

    Every active filter reports how it divided the candidate set, so the caller
    can say what was left out. A filter that empties the list without explaining
    itself is indistinguishable from a bug — and here it usually was one.
    """
    report: dict[str, FilterCounts] = {}
    kept: list[tuple[ScoredPlant, dict[str, Verdict]]] = []

    for plant in candidates:
        if excluded_outright(plant, filters):
            continue
        fit = score_species(site, plant.niche)
        if fit.score is None:
            continue

        verdicts = verdicts_for(plant, filters, colour)
        for name, verdict in verdicts.items():
            report.setdefault(name, FilterCounts()).record(verdict, excludes=name != COLOUR)

        # Colour never removes anything; the other filters remove known
        # mismatches, and remove unknowns only when the user did not ask for them.
        hard = {n: v for n, v in verdicts.items() if n != COLOUR}
        if any(v is Verdict.MISMATCH for v in hard.values()):
            continue
        if not filters.include_unknown and any(v is Verdict.UNKNOWN for v in hard.values()):
            continue
        kept.append((ScoredPlant(plant=plant, fit=fit), verdicts))

    kept.sort(key=lambda pair: _order_key(*pair))
    return RankedResult(items=[scored for scored, _ in kept], report=report)
