"""What a planting is worth to insects.

One number, with every part of it traceable to counted records. The shape matters
as much as the value: the score is deliberately **submodular**, which is what
makes the greedy swap search defensible rather than merely convenient.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field

from ninanatur.bloom.timeline import SEASON_MONTHS, flowering_months
from ninanatur.data.interactions import german_partner_counts
from ninanatur.data.traits import resolve_trait
from ninanatur.garden.models import Garden

# A stated convention, like the sun-hour mapping and the soil table. Introduced
# species are not worthless to insects, and scoring them at zero would be as
# dishonest as ignoring origin altogether.
ORIGIN_FACTOR: dict[str, float] = {
    "native": 1.0,
    "unknown": 0.85,
    "introduced": 0.5,
}

# Forage above which a month counts as well supplied. Roughly two well-connected
# native species in flower. This constant is what makes the score submodular, so
# it is not a tuning knob to move casually.
MONTH_SATURATION = 25.0


@dataclass(frozen=True)
class SpeciesContribution:
    """One planted species and what it brings."""

    taxon_id: int
    canonical_name: str
    german_partners: int | None
    origin: str
    forage: float
    months: tuple[int, ...]


@dataclass
class ScoreResult:
    """The score with everything needed to argue about it."""

    score: float
    by_month: dict[int, float] = field(default_factory=dict)
    # Uncapped sums, so a candidate's marginal gain can be computed without
    # rescoring the whole garden. See ninanatur/bloom/improve.py.
    raw_month: dict[int, float] = field(default_factory=dict)
    by_species: list[SpeciesContribution] = field(default_factory=list)
    by_group: dict[str, int] = field(default_factory=dict)
    plantings_total: int = 0
    plantings_without_interaction_data: int = 0

    @property
    def is_empty(self) -> bool:
        return self.plantings_total == 0


def species_forage(german_partners: int, origin: str) -> float:
    """What one species of this kind is worth.

    The square root is deliberate: the difference between 5 and 50 partners
    matters far more than between 500 and 545, and raw counts would let one
    well-studied plant dominate a whole garden.

    A species with no records still scores above zero — unknown is not worthless.
    """
    base = 1.0 + math.sqrt(max(german_partners, 0))
    return base * ORIGIN_FACTOR.get(origin, ORIGIN_FACTOR["unknown"])


def _origin_of(conn: sqlite3.Connection, taxon_id: int) -> str:
    trait = resolve_trait(conn, taxon_id, "native_de")
    return str(trait.value_text) if trait and trait.value_text else "unknown"


def garden_score(conn: sqlite3.Connection, garden: Garden) -> ScoreResult:
    """Score a whole garden, keeping the reasoning attached.

    Per season month, the forage in flower is capped at `MONTH_SATURATION`. That
    cap is the whole design: adding a species to a saturated July gains nothing,
    adding one to an empty April gains the full amount. Continuity therefore falls
    out of the function rather than being multiplied on afterwards — and the
    result is submodular, which is what `19-swap-suggestions` relies on.
    """
    per_month: dict[int, float] = dict.fromkeys(SEASON_MONTHS, 0.0)
    contributions: list[SpeciesContribution] = []
    groups: dict[str, int] = {}
    total = 0
    unknown_records = 0

    for bed in garden.beds:
        for planting in bed.plantings:
            # No taxon, no data. It stays on the plan and out of the maths — and
            # it is counted separately, so the score can say what it could not
            # count instead of quietly averaging over fewer plants.
            if planting.taxon_id is None:
                continue
            total += 1
            start = resolve_trait(conn, planting.taxon_id, "flowering_start_month")
            end = resolve_trait(conn, planting.taxon_id, "flowering_end_month")
            months = flowering_months(
                int(start.value_num) if start and start.value_num is not None else None,
                int(end.value_num) if end and end.value_num is not None else None,
            )

            counts = german_partner_counts(conn, planting.taxon_id)
            if counts is None:
                unknown_records += 1
            else:
                for group, n in counts.by_group.items():
                    groups[group] = groups.get(group, 0) + n

            origin = _origin_of(conn, planting.taxon_id)
            forage = species_forage(counts.german if counts else 0, origin) * planting.quantity

            contributions.append(
                SpeciesContribution(
                    taxon_id=planting.taxon_id,
                    canonical_name=planting.display_name,
                    german_partners=counts.german if counts else None,
                    origin=origin,
                    forage=round(forage, 3),
                    months=months,
                )
            )
            for month in months:
                if month in per_month:
                    per_month[month] += forage

    capped = {m: min(v, MONTH_SATURATION) for m, v in per_month.items()}
    ceiling = len(SEASON_MONTHS) * MONTH_SATURATION
    score = 0.0 if total == 0 else 100.0 * sum(capped.values()) / ceiling

    return ScoreResult(
        score=round(score, 1),
        by_month={m: round(v, 2) for m, v in capped.items()},
        raw_month=dict(per_month),
        by_species=sorted(contributions, key=lambda c: -c.forage),
        by_group=groups,
        plantings_total=total,
        plantings_without_interaction_data=unknown_records,
    )
