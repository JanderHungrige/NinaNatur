"""Turn raw interaction records into the counts the runtime actually asks for.

GloBI's 600k rows exist so the intersection with the German insect list can be
recomputed when either source changes. The serving path never needs them — it
asks only "how many German partners does this plant have", which is one number
per plant per relation kind.

Summarising here is what makes the catalogue shippable: 93 MB of raw records
become 10 MB of answers.
"""
from __future__ import annotations

import sqlite3

SUMMARY_SQL = """
INSERT OR REPLACE INTO partner_summary (taxon_id, interaction_type, german)
SELECT i.taxon_id, i.interaction_type, COUNT(DISTINCT i.partner_name)
FROM interaction i
JOIN insect_de d ON d.canonical_name = i.partner_name
GROUP BY i.taxon_id, i.interaction_type
"""

# `unmatched` is kept because a low match rate makes the German count an
# underestimate rather than a finding, and the UI has to be able to say so.
TOTALS_SQL = """
INSERT OR REPLACE INTO partner_totals (taxon_id, german, global_total, unmatched)
SELECT i.taxon_id,
       COUNT(DISTINCT CASE WHEN d.canonical_name IS NOT NULL THEN i.partner_name END),
       COUNT(DISTINCT i.partner_name),
       COUNT(DISTINCT CASE WHEN d.canonical_name IS NULL THEN i.partner_name END)
FROM interaction i
LEFT JOIN insect_de d ON d.canonical_name = i.partner_name
GROUP BY i.taxon_id
"""


GROUPS_SQL = """
INSERT OR REPLACE INTO partner_groups (taxon_id, insect_group, german)
SELECT i.taxon_id, d.insect_group, COUNT(DISTINCT i.partner_name)
FROM interaction i
JOIN insect_de d ON d.canonical_name = i.partner_name
WHERE d.insect_group IS NOT NULL
GROUP BY i.taxon_id, d.insect_group
"""


def summarise_interactions(conn: sqlite3.Connection) -> int:
    """Rebuild the partner aggregates. Returns the number of plants summarised.

    Must run after `globi`, `insects-de` and `insect-groups`: it is their
    intersection, so running it earlier leaves counts at zero — silently, because
    zero German partners is a legitimate answer.
    """
    conn.execute("DELETE FROM partner_summary")
    conn.execute("DELETE FROM partner_totals")
    conn.execute("DELETE FROM partner_groups")
    conn.execute(SUMMARY_SQL)
    conn.execute(TOTALS_SQL)
    conn.execute(GROUPS_SQL)
    conn.commit()
    return int(conn.execute("SELECT COUNT(*) AS n FROM partner_totals").fetchone()["n"])
