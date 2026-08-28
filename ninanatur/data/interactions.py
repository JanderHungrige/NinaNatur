"""Plant-animal relations, restricted to what actually lives here.

GloBI's records are worldwide. Reporting them raw would rank a plant by how
thoroughly it has been studied rather than by what visits it in a German garden —
and that number is what the insect score rests on.
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
    rows = conn.execute(
        """
        SELECT i.partner_name,
               i.interaction_type,
               (d.canonical_name IS NOT NULL) AS is_german
        FROM interaction i
        LEFT JOIN insect_de d ON d.canonical_name = i.partner_name
        WHERE i.taxon_id = ?
        """,
        (taxon_id,),
    ).fetchall()
    if not rows:
        return None

    german_partners: set[str] = set()
    all_partners: set[str] = set()
    by_kind: dict[str, int] = {}
    for row in rows:
        name = str(row["partner_name"])
        all_partners.add(name)
        if row["is_german"]:
            german_partners.add(name)
            kind = str(row["interaction_type"])
            by_kind[kind] = by_kind.get(kind, 0) + 1

    return PartnerCounts(
        taxon_id=taxon_id,
        german=len(german_partners),
        global_total=len(all_partners),
        unmatched=len(all_partners) - len(german_partners),
        by_kind=by_kind,
    )
