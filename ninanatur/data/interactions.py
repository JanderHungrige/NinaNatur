"""Plant-animal relations, restricted to what actually lives here.

GloBI's records are worldwide. Reporting them raw would rank a plant by how
thoroughly it has been studied rather than by what visits it in a German garden —
and that number is what the insect score rests on.

Reads the aggregates built by `ingest/summarise.py`, not the raw records. The
600k interaction rows are ingest-time data; the serving path only ever asks for
counts, and keeping the raw table out of the shipped catalogue is what takes it
from 93 MB to 10 MB.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class PartnerCounts:
    """A plant's animal partners, German and global, with the match quality shown."""

    taxon_id: int
    german: int
    global_total: int
    unmatched: int
    by_kind: dict[str, int]

    @property
    def match_rate(self) -> float:
        """Share of partner names that resolved against the German checklist.

        Surfaced deliberately: a low rate means the German count is an
        underestimate rather than a finding, and the UI must be able to say so.
        """
        return 0.0 if self.global_total == 0 else self.german / self.global_total


def german_partner_counts(conn: sqlite3.Connection, taxon_id: int) -> PartnerCounts | None:
    """Count a plant's partners that are recorded in Germany.

    Returns None when GloBI holds no relations for the plant at all. A plant with
    records but no German partners returns a count of 0 — those are different
    facts and must not render the same.
    """
    totals = conn.execute(
        "SELECT german, global_total, unmatched FROM partner_totals WHERE taxon_id = ?",
        (taxon_id,),
    ).fetchone()
    if totals is None:
        return None

    by_kind = {
        str(row["interaction_type"]): int(row["german"])
        for row in conn.execute(
            "SELECT interaction_type, german FROM partner_summary"
            " WHERE taxon_id = ? AND german > 0",
            (taxon_id,),
        )
    }
    return PartnerCounts(
        taxon_id=taxon_id,
        german=int(totals["german"]),
        global_total=int(totals["global_total"]),
        unmatched=int(totals["unmatched"]),
        by_kind=by_kind,
    )
