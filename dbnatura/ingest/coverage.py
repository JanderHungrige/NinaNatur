"""The coverage report — the number that decides whether open data carries the product.

Candidate set: taxa that occur in Germany. A taxon counts as covered for a trait
if at least one source supplied it, regardless of how many did.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

CORE_TRAITS: tuple[str, ...] = (
    "ellenberg_l",
    "ellenberg_m",
    "ellenberg_n",
    "height_max_m",
    "flowering_start_month",
    "flowering_end_month",
)

REPORTED_TRAITS: tuple[str, ...] = CORE_TRAITS + (
    "ellenberg_r",
    "ellenberg_t",
    "flower_colour",
    "growth_form",
    "life_form",
    "lifecycle",
    "pollination_syndrome",
)


@dataclass
class CoverageReport:
    """Per-trait and per-threshold coverage over the candidate set."""

    candidates: int
    per_trait: dict[str, int] = field(default_factory=dict)
    core_complete: int = 0
    full_complete: int = 0
    with_interactions: int = 0
    unresolved_names: int = 0

    def _pct(self, n: int) -> float:
        return 0.0 if self.candidates == 0 else round(100.0 * n / self.candidates, 1)

    @property
    def core_complete_pct(self) -> float:
        return self._pct(self.core_complete)

    @property
    def full_complete_pct(self) -> float:
        return self._pct(self.full_complete)

    def trait_pct(self, key: str) -> float:
        return self._pct(self.per_trait.get(key, 0))


def compute_coverage(conn: sqlite3.Connection) -> CoverageReport:
    """Measure how much of the needed field set exists for German taxa."""
    candidates = conn.execute("SELECT COUNT(*) AS n FROM taxon WHERE occurs_de = 1").fetchone()["n"]
    report = CoverageReport(candidates=int(candidates))

    for key in REPORTED_TRAITS:
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT t.taxon_id) AS n
            FROM trait t JOIN taxon x ON x.taxon_id = t.taxon_id
            WHERE t.trait_key = ? AND x.occurs_de = 1
            """,
            (key,),
        ).fetchone()
        report.per_trait[key] = int(row["n"])

    placeholders = ",".join("?" for _ in CORE_TRAITS)
    core_rows = conn.execute(
        f"""
        SELECT t.taxon_id
        FROM trait t JOIN taxon x ON x.taxon_id = t.taxon_id
        WHERE x.occurs_de = 1 AND t.trait_key IN ({placeholders})
        GROUP BY t.taxon_id
        HAVING COUNT(DISTINCT t.trait_key) = ?
        """,
        (*CORE_TRAITS, len(CORE_TRAITS)),
    ).fetchall()
    core_ids = {int(r["taxon_id"]) for r in core_rows}
    report.core_complete = len(core_ids)

    colour_ids = {
        int(r["taxon_id"])
        for r in conn.execute(
            "SELECT DISTINCT taxon_id FROM trait WHERE trait_key = 'flower_colour'"
        ).fetchall()
    }
    interaction_ids = {
        int(r["taxon_id"])
        for r in conn.execute("SELECT DISTINCT taxon_id FROM interaction").fetchall()
    }
    report.full_complete = len(core_ids & colour_ids & interaction_ids)

    report.with_interactions = int(
        conn.execute(
            """
            SELECT COUNT(DISTINCT i.taxon_id) AS n
            FROM interaction i JOIN taxon x ON x.taxon_id = i.taxon_id
            WHERE x.occurs_de = 1
            """
        ).fetchone()["n"]
    )
    report.unresolved_names = int(
        conn.execute("SELECT COUNT(*) AS n FROM taxon_name WHERE taxon_id IS NULL").fetchone()["n"]
    )
    return report


def format_report(report: CoverageReport) -> str:
    """Render the report as the CLI prints it."""
    lines = [
        "Coverage — candidate set: taxa occurring in Germany",
        f"  Candidates:            {report.candidates}",
        "",
        "  Per trait:",
    ]
    for key in REPORTED_TRAITS:
        n = report.per_trait.get(key, 0)
        marker = "  " if key not in CORE_TRAITS else "* "
        lines.append(f"    {marker}{key:<24} {n:>6}  {report.trait_pct(key):>5.1f}%")
    lines += [
        "",
        f"  Core complete:         {report.core_complete:>6}  {report.core_complete_pct:>5.1f}%",
        f"  Full complete:         {report.full_complete:>6}  {report.full_complete_pct:>5.1f}%",
        f"  With interactions:     {report.with_interactions:>6}",
        f"  Unresolved names:      {report.unresolved_names:>6}",
        "",
        "  (* = core trait; core = light, moisture, nutrients, height, flowering start/end)",
    ]
    return "\n".join(lines)
