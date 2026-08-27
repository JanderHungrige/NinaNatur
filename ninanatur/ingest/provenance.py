"""The only write path into `trait`.

Every trait value in this database carries where it came from and under which
licence it may be used. That is enforced here, not by convention: a write with
an empty source or licence raises rather than silently producing an
unattributable row.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime


class ProvenanceError(ValueError):
    """A trait write was attempted without complete provenance."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def upsert_trait(
    conn: sqlite3.Connection,
    taxon_id: int,
    trait_key: str,
    *,
    source: str,
    license: str,
    value_num: float | None = None,
    value_text: str | None = None,
    unit: str | None = None,
    confidence: float | None = None,
) -> None:
    """Insert or update one trait value for one taxon from one source.

    Two different sources for the same trait coexist as separate rows — the
    primary key includes `source`, so disagreement stays visible instead of
    being silently resolved at ingest time.
    """
    if not source.strip():
        raise ProvenanceError(f"trait {trait_key!r} for taxon {taxon_id}: source is required")
    if not license.strip():
        raise ProvenanceError(f"trait {trait_key!r} for taxon {taxon_id}: license is required")
    if value_num is None and value_text is None:
        raise ProvenanceError(f"trait {trait_key!r} for taxon {taxon_id}: no value supplied")

    conn.execute(
        """
        INSERT INTO trait (taxon_id, trait_key, value_num, value_text, unit,
                           source, license, confidence, retrieved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (taxon_id, trait_key, source) DO UPDATE SET
            value_num    = excluded.value_num,
            value_text   = excluded.value_text,
            unit         = excluded.unit,
            license      = excluded.license,
            confidence   = excluded.confidence,
            retrieved_at = excluded.retrieved_at
        """,
        (taxon_id, trait_key, value_num, value_text, unit, source, license, confidence, _now()),
    )


def record_interaction(
    conn: sqlite3.Connection,
    taxon_id: int,
    partner_name: str,
    interaction_type: str,
    *,
    source: str,
    license: str,
    partner_group: str | None = None,
    n_records: int = 1,
) -> None:
    """Store one plant-animal relation, accumulating the record count on repeat."""
    if not source.strip() or not license.strip():
        raise ProvenanceError(f"interaction for taxon {taxon_id}: source and license are required")
    conn.execute(
        """
        INSERT INTO interaction (taxon_id, partner_name, partner_group,
                                 interaction_type, source, license, n_records)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (taxon_id, partner_name, interaction_type, source) DO UPDATE SET
            n_records     = excluded.n_records,
            partner_group = COALESCE(excluded.partner_group, interaction.partner_group)
        """,
        (taxon_id, partner_name, partner_group, interaction_type, source, license, n_records),
    )
