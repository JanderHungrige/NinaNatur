"""German names from GBIF.

10-20 per species, and — usefully — including spellings with and without
umlauts. That is exactly what a search box needs, and it arrives free rather
than having to be generated.
"""
from __future__ import annotations

import sqlite3

from ninanatur.data.names import normalise, preferred_name
from ninanatur.ingest.http import get_json
from ninanatur.ingest.sources.base import finish_run, start_run

SOURCE_NAME = "GBIF-vernacular"
LICENSE = "CC-BY-4.0"
SPECIES_URL = "https://api.gbif.org/v1/species"
GERMAN = "deu"


def german_names(payload: object) -> list[str]:
    """The German names in a GBIF vernacularNames response, deduplicated."""
    if not isinstance(payload, dict):
        return []
    seen: dict[str, str] = {}
    for entry in payload.get("results", []):
        if not isinstance(entry, dict) or entry.get("language") != GERMAN:
            continue
        name = str(entry.get("vernacularName") or "").strip()
        if not name:
            continue
        # Keep one spelling per distinct name, but keep BOTH umlaut variants —
        # they normalise differently on purpose, and that is what makes every way
        # of typing the name findable.
        seen.setdefault(name, name)
    return sorted(seen)


class VernacularSource:
    """Fills `vernacular_name` for every German candidate."""

    name = SOURCE_NAME
    license = LICENSE

    def run(self, conn: sqlite3.Connection, limit: int | None = None) -> int:
        started = start_run(conn, self.name)
        rows = conn.execute(
            "SELECT taxon_id FROM taxon WHERE occurs_de = 1 ORDER BY taxon_id"
        ).fetchall()
        if limit is not None:
            rows = rows[:limit]

        written = 0
        for index, row in enumerate(rows, start=1):
            taxon_id = int(row["taxon_id"])
            payload = get_json(f"{SPECIES_URL}/{taxon_id}/vernacularNames", {"limit": 200})
            names = german_names(payload)
            if not names:
                continue
            best = preferred_name(names)
            for name in names:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO vernacular_name
                        (taxon_id, name, normalised, is_preferred, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (taxon_id, name, normalise(name), int(name == best), self.name),
                )
                written += 1
            if index % 250 == 0:
                conn.commit()
                print(f"  vernacular: {index}/{len(rows)}", flush=True)

        conn.commit()
        finish_run(conn, self.name, started, written, "complete")
        return written
