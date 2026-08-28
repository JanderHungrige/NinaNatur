"""The German bird checklist.

Same trick as the insect list: GBIF's occurrence facet on the scientific name
gives a clade's German species in roughly 19 calls instead of one detail request
per species. Only the clade key differs.

Birds land in `insect_de` with `clade = 'bird'`. The table name is now
imprecise; the column, not the name, is what every read site goes by. See
25-woody-and-birds for why renaming was rejected rather than overlooked.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable

from ninanatur.ingest.sources.base import finish_run, start_run
from ninanatur.ingest.sources.gbif import canonical_name, fetch_german_scientific_names

SOURCE_NAME = "GBIF-birds-DE"
LICENSE = "CC-BY-4.0"

# GBIF backbone key for class Aves, resolved against the species/match endpoint.
AVES_KEY = 212

FetchNames = Callable[[int], dict[str, int]]


class BirdsDeSource:
    """Populates `insect_de` with bird species recorded in Germany."""

    name = SOURCE_NAME
    license = LICENSE

    def __init__(self, fetch: FetchNames | None = None) -> None:
        # Injected so the tests state what GBIF returned rather than stubbing
        # the network — the same reason every other boundary here takes its
        # collaborator as an argument.
        self._fetch: FetchNames = fetch or (lambda key: fetch_german_scientific_names(key))

    def run(self, conn: sqlite3.Connection, limit: int | None = None) -> int:
        started = start_run(conn, self.name)
        names = self._fetch(AVES_KEY)
        items = sorted(names.items())[:limit] if limit is not None else sorted(names.items())

        best: dict[str, tuple[str, int]] = {}
        for scientific, count in items:
            canonical = canonical_name(scientific)
            # Species only. A GloBI partner recorded as "Passeriformes", matched
            # against "Germany has Passeriformes", is vacuously true and would
            # inflate every plant's count — the trap the insect list documents.
            if " " not in canonical:
                continue
            if canonical not in best or count > best[canonical][1]:
                best[canonical] = (scientific, count)

        for canonical, (scientific, count) in best.items():
            conn.execute(
                """
                INSERT INTO insect_de (canonical_name, scientific_name, occurrences, clade)
                VALUES (?, ?, ?, 'bird')
                ON CONFLICT (canonical_name) DO UPDATE SET
                    occurrences = MAX(insect_de.occurrences, excluded.occurrences),
                    clade = 'bird'
                """,
                (canonical, scientific, count),
            )

        conn.commit()
        finish_run(conn, self.name, started, len(best), "complete")
        return len(best)
