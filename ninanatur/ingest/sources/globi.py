"""GloBI — Global Biotic Interactions (Poelen et al., CC0/CC-BY per dataset).

Supplies the evidence behind the insect score. Three relations matter for a
garden: who pollinates the plant, who visits its flowers, and who eats it —
the last one being where butterflies actually depend on a plant, since larvae
feed on foliage rather than nectar.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ninanatur.ingest.coverage import core_complete_ids
from ninanatur.ingest.http import HttpError, get_json
from ninanatur.ingest.provenance import record_interaction
from ninanatur.ingest.sources.base import finish_run, start_run

SOURCE_NAME = "GloBI"
LICENSE = "CC0-1.0"
TAXON_URL = "https://api.globalbioticinteractions.org/taxon"

# GloBI relation -> the group it contributes to in the score
RELATIONS: dict[str, str] = {
    "pollinatedBy": "pollinator",
    "visitedBy": "flower_visitor",
    "eatenBy": "herbivore",
}


def fetch_partners(plant_name: str, relation: str) -> list[str]:
    """Return the distinct partner taxa for one plant and one relation."""
    encoded = plant_name.replace(" ", "%20")
    payload = get_json(f"{TAXON_URL}/{encoded}/{relation}", {"type": "json.v2"})
    partners: list[str] = []
    for entry in _as_list(payload):
        names = entry.get("target_taxon_name")
        if isinstance(names, list):
            partners.extend(str(n) for n in names)
        elif names:
            partners.append(str(names))
    return sorted({p.strip() for p in partners if p and p.strip()})


def _as_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    return []


class GlobiSource:
    name = SOURCE_NAME
    license = LICENSE

    def run(self, conn: sqlite3.Connection, limit: int | None = None) -> int:
        """Query only core-complete taxa.

        A taxon missing site conditions or a flowering window can never be
        suggested for a bed, so its interaction records could never reach the
        score. Restricting here turns a multi-hour crawl into a targeted one.
        """
        started = start_run(conn, self.name)
        wanted = core_complete_ids(conn)
        rows = [
            r
            for r in conn.execute(
                "SELECT taxon_id, canonical_name FROM taxon WHERE occurs_de = 1"
                " ORDER BY canonical_name"
            ).fetchall()
            if int(r["taxon_id"]) in wanted
        ]
        if limit is not None:
            rows = rows[:limit]
        print(f"  GloBI: querying {len(rows)} core-complete taxa", flush=True)

        written = 0
        failures = 0
        for index, row in enumerate(rows, start=1):
            taxon_id = int(row["taxon_id"])
            name = str(row["canonical_name"])
            for relation, group in RELATIONS.items():
                try:
                    partners = fetch_partners(name, relation)
                except HttpError:
                    # One unreachable relation must not abort a multi-hour run.
                    failures += 1
                    continue
                for partner in partners:
                    record_interaction(
                        conn, taxon_id, partner, relation,
                        source=self.name, license=self.license, partner_group=group,
                    )
                    written += 1
            if index % 100 == 0:
                conn.commit()
                print(f"  GloBI: {index}/{len(rows)} taxa, {written} relations", flush=True)

        conn.commit()
        status = "complete" if failures == 0 else "partial"
        finish_run(conn, self.name, started, written, status, f"{failures} failed requests")
        return written
