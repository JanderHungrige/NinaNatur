"""The German insect checklist.

Reuses the plant candidate-set machinery with a different clade rather than
adding a source. Faceting on the scientific name rather than the species key
turns ~19,000 detail requests into about 19 calls.
"""
from __future__ import annotations

import sqlite3

from ninanatur.ingest.sources.base import finish_run, start_run
from ninanatur.ingest.sources.gbif import (
    INSECTA_KEY,
    canonical_name,
    fetch_german_scientific_names,
)

SOURCE_NAME = "GBIF-insects-DE"
LICENSE = "CC-BY-4.0"


class InsectsDeSource:
    """Populates `insect_de` with insect species recorded in Germany."""

    name = SOURCE_NAME
    license = LICENSE

    def run(self, conn: sqlite3.Connection, limit: int | None = None) -> int:
        started = start_run(conn, self.name)
        names = fetch_german_scientific_names(INSECTA_KEY)
        items = sorted(names.items())[:limit] if limit is not None else sorted(names.items())

        # Subspecies collapse onto their species, so keep the highest occurrence
        # count rather than whichever row happened to be written last.
        best: dict[str, tuple[str, int]] = {}
        for scientific, count in items:
            canonical = canonical_name(scientific)
            # Species only. A third of the facet's names are higher ranks —
            # "Diptera" (an order), "Chironomidae" (a family) — from records
            # identified no further. Matching a GloBI partner called "Diptera"
            # against "Germany has Diptera" is vacuously true and would inflate
            # every plant's partner count.
            if " " not in canonical:
                continue
            if canonical not in best or count > best[canonical][1]:
                best[canonical] = (scientific, count)

        for canonical, (scientific, count) in best.items():
            conn.execute(
                """
                INSERT INTO insect_de (canonical_name, scientific_name, occurrences)
                VALUES (?, ?, ?)
                ON CONFLICT (canonical_name) DO UPDATE SET
                    occurrences = MAX(insect_de.occurrences, excluded.occurrences)
                """,
                (canonical, scientific, count),
            )

        conn.commit()
        finish_run(conn, self.name, started, len(best), "complete")
        return len(best)
