"""Reading traits back out, with provenance intact.

The ingest layer stores every source's value side by side on purpose. This module
collapses that to one answer for display — and keeps the losing values attached,
so disagreement between sources is something the UI can show rather than
something the read path quietly decided.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ninanatur.fit.score import AXES

# Ordered best-first. Currently a formality: measured against the database, EIVE
# and GIFT overlap in zero trait keys, so nothing is ever arbitrated. It exists so
# that when a third source arrives the winner is deterministic rather than
# whatever row SQLite happened to return first.
SOURCE_PRIORITY: tuple[str, ...] = ("EIVE-1.0", "GIFT")

#: What a gardener typed in, as opposed to what a dataset published.
#:
#: Deliberately *not* a member of SOURCE_PRIORITY. Appending it there would give
#: it rank 2 while the next source somebody adds would land at 3 — a hand entry
#: would then outrank a real dataset simply because it was named earlier. It is
#: ranked last explicitly instead, so every official source beats it, including
#: ones that do not exist yet.
MANUAL_SOURCE = "manual"

KNOWN_TRAIT_KEYS: frozenset[str] = frozenset(
    {*AXES, *(f"{a}_nw" for a in AXES),
     "height_max_m", "flowering_start_month", "flowering_end_month", "woodiness",
     "flower_colour", "growth_form", "life_form", "lifecycle",
     "pollination_syndrome", "native_de"}
)


class UnknownTraitKey(ValueError):
    """A trait key that is not part of the canonical set.

    Raised rather than returning None: a typo'd key silently resolving to "no
    value" is indistinguishable from genuinely missing data, and would hide bugs
    behind what looks like a coverage gap.
    """


@dataclass(frozen=True)
class TraitValue:
    """One source's answer for one trait."""

    trait_key: str
    value_num: float | None
    value_text: str | None
    unit: str | None
    source: str
    license: str
    confidence: float | None


@dataclass(frozen=True)
class ResolvedTrait(TraitValue):
    """The chosen answer, with the values it beat still attached."""

    alternatives: tuple[TraitValue, ...] = ()


def source_rank(source: str) -> tuple[int, str]:
    """Known sources in declared order, then unknown ones, then hand entries.

    A newly added source must not outrank the curated ones just because of how it
    sorts — and a value somebody typed in must not outrank any of them. That is
    the rule the gardener asked for: a hand entry fills a gap until real data
    arrives, and then gets out of the way.
    """
    if source == MANUAL_SOURCE:
        return (len(SOURCE_PRIORITY) + 1, "")
    if source in SOURCE_PRIORITY:
        return (SOURCE_PRIORITY.index(source), "")
    return (len(SOURCE_PRIORITY), source)


def _to_value(row: sqlite3.Row) -> TraitValue:
    return TraitValue(
        trait_key=row["trait_key"],
        value_num=row["value_num"],
        value_text=row["value_text"],
        unit=row["unit"],
        source=row["source"],
        license=row["license"],
        confidence=row["confidence"],
    )


def _resolve_group(rows: list[sqlite3.Row]) -> ResolvedTrait:
    ordered = sorted((_to_value(r) for r in rows), key=lambda v: source_rank(v.source))
    winner, *losers = ordered
    return ResolvedTrait(
        trait_key=winner.trait_key,
        value_num=winner.value_num,
        value_text=winner.value_text,
        unit=winner.unit,
        source=winner.source,
        license=winner.license,
        confidence=winner.confidence,
        alternatives=tuple(losers),
    )


def resolve_trait(
    conn: sqlite3.Connection, taxon_id: int, trait_key: str
) -> ResolvedTrait | None:
    """The value for one trait, or None when nothing recorded it.

    None means *unknown* and callers must render it as such — never as zero and
    never by omitting the field. That is what keeps flower colour honest while it
    covers 12% of the catalogue.
    """
    if trait_key not in KNOWN_TRAIT_KEYS:
        raise UnknownTraitKey(f"unknown trait key: {trait_key!r}")
    rows = conn.execute(
        "SELECT trait_key, value_num, value_text, unit, source, license, confidence"
        " FROM trait WHERE taxon_id = ? AND trait_key = ?",
        (taxon_id, trait_key),
    ).fetchall()
    return _resolve_group(list(rows)) if rows else None


def resolve_traits_for(conn: sqlite3.Connection, taxon_id: int) -> dict[str, ResolvedTrait]:
    """Every trait for one taxon in a single query.

    Scoring thousands of species one `resolve_trait` call at a time would be
    thousands of round trips.
    """
    rows = conn.execute(
        "SELECT trait_key, value_num, value_text, unit, source, license, confidence"
        " FROM trait WHERE taxon_id = ? ORDER BY trait_key",
        (taxon_id,),
    ).fetchall()
    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["trait_key"], []).append(row)
    return {key: _resolve_group(group) for key, group in grouped.items()}
