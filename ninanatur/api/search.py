"""Ranking: score the candidates, apply the filters, order what survives.

The route's job is parameters in, schema out. The decision about what matches
lives here, and the decision about what one filter means lives in `filters.py`.
"""
from __future__ import annotations

from dataclasses import dataclass

from ninanatur.api.candidates import (
    AXIS_PARAMS,
    PlantRow,
    ScoredPlant,
    load_candidates,
    with_observed,
)
from ninanatur.api.filters import (
    LIGHT,
    FilterCounts,
    SearchFilters,
    Verdict,
    excluded_outright,
    is_woody,
    light_verdict,
    verdicts_for,
)
from ninanatur.fit.light_fit import light_mismatch
from ninanatur.fit.rank import growing_conditions, insect_value
from ninanatur.fit.score import FitResult, SiteVector, score_species

# Filters that order rather than remove. Named in one place so the sites that
# must treat them differently cannot drift apart.
COLOUR = "colour"
RANKS_ONLY: frozenset[str] = frozenset({COLOUR, "space"})

__all__ = [
    "AXIS_PARAMS",
    "FilterCounts",
    "PlantRow",
    "RankedResult",
    "ScoredPlant",
    "SearchFilters",
    "Verdict",
    "is_woody",
    "light_mismatch",
    "load_candidates",
    "rank_plants",
    "with_observed",
]


@dataclass(frozen=True)
class RankedResult:
    """The ordered list, plus what each active filter did to get there."""

    items: list[ScoredPlant]
    report: dict[str, FilterCounts]


def _order_key(
    scored: ScoredPlant, verdicts: dict[str, Verdict], misfit: bool
) -> tuple[int, int, int, float, float]:
    """Known matches first, then unknowns, then colour mismatches, then light
    misfits shown on request — and within each, growing conditions lifted by
    insect value (`fit.rank`), the plain fit breaking ties.

    Unknowns are kept only when the user asked for them, and even then they must
    not outrank a species that actually matches what was asked. Asking to see
    what the light does not suit is not asking to have it mixed in.
    """
    values = verdicts.values()
    unknown = 1 if any(v is Verdict.UNKNOWN for v in values) else 0
    mismatch = 1 if any(v is Verdict.MISMATCH for v in values) else 0
    return (int(misfit), mismatch, unknown, -scored.rank, -scored.score)


def _light_misfit(
    fit: FitResult, filters: SearchFilters, lit: bool, report: dict[str, FilterCounts]
) -> bool | None:
    """The light cut, counted: None when it removes the species, otherwise
    whether the species is a light misfit shown on request (the opt-out)."""
    light = light_verdict(fit, filters, lit=lit)
    if light is not None:
        report.setdefault(LIGHT, FilterCounts()).record(light, excludes=True)
        return None if light is Verdict.MISMATCH else False
    return lit and light_mismatch(fit) is not None


def _passes(verdicts: dict[str, Verdict], filters: SearchFilters) -> bool:
    """Colour never removes anything; the other filters remove known
    mismatches, and remove unknowns only when the user did not ask for them."""
    hard = [v for name, v in verdicts.items() if name not in RANKS_ONLY]
    if any(v is Verdict.MISMATCH for v in hard):
        return False
    return filters.include_unknown or not any(v is Verdict.UNKNOWN for v in hard)


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
    kept: list[tuple[ScoredPlant, dict[str, Verdict], bool]] = []
    lit = "ellenberg_l" in site.values
    # The insect value's scale is the catalogue's, not what the filters leave:
    # a plant's worth to insects does not change with the height asked for.
    most = max((p.insect_partners or 0 for p in candidates), default=0)

    for plant in candidates:
        if excluded_outright(plant, filters):
            continue
        fit = score_species(site, plant.niche)
        if fit.score is None:
            continue

        verdicts = verdicts_for(plant, filters, colour)
        for name, verdict in verdicts.items():
            report.setdefault(name, FilterCounts()).record(
                verdict, excludes=name not in RANKS_ONLY
            )
        # Counted beside the others, but kept out of `verdicts`: a species with
        # no L value must neither be dropped as an unknown nor sorted below
        # every species that has one.
        misfit = _light_misfit(fit, filters, lit, report)
        if misfit is None or not _passes(verdicts, filters):
            continue
        kept.append((ScoredPlant(
            plant=plant, fit=fit,
            growing=growing_conditions(fit, len(site.values)),
            insect=insect_value(plant.insect_partners, most), axes=len(site.values),
        ), verdicts, misfit))

    kept.sort(key=lambda entry: _order_key(*entry))
    return RankedResult(items=[scored for scored, _, _ in kept], report=report)
