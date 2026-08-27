"""GBIF — taxonomy backbone and the German candidate set.

The candidate set is derived from actual occurrence records rather than from a
curated list: every vascular plant species with observations in Germany. Pulled
via the occurrence facet, which returns backbone species keys directly, so no
name matching is involved and the whole set costs a handful of requests.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from dbnatura.ingest.http import get_json
from dbnatura.ingest.sources.base import finish_run, start_run

SOURCE_NAME = "GBIF"
LICENSE = "CC-BY-4.0"
OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"
SPECIES_URL = "https://api.gbif.org/v1/species"
TRACHEOPHYTA_KEY = 7707728
FACET_PAGE = 1000
MIN_OCCURRENCES = 5


def fetch_german_species_keys(max_species: int = 20000) -> dict[int, int]:
    """Return {speciesKey: occurrence count} for vascular plants recorded in Germany.

    `MIN_OCCURRENCES` filters out single stray records, which are typically
    misidentifications or garden escapes rather than an established presence.
    """
    keys: dict[int, int] = {}
    offset = 0
    while offset < max_species:
        payload = get_json(
            OCCURRENCE_URL,
            {
                "country": "DE",
                "taxonKey": TRACHEOPHYTA_KEY,
                "facet": "speciesKey",
                "facetLimit": FACET_PAGE,
                "facetOffset": offset,
                "limit": 0,
            },
        )
        counts = _facet_counts(payload)
        if not counts:
            break
        for entry in counts:
            count = int(entry["count"])
            if count >= MIN_OCCURRENCES:
                keys[int(entry["name"])] = count
        if len(counts) < FACET_PAGE:
            break
        offset += FACET_PAGE
    return keys


def _facet_counts(payload: Any) -> list[dict[str, Any]]:
    for facet in (payload or {}).get("facets", []):
        if facet.get("field") in {"SPECIES_KEY", "speciesKey"}:
            return list(facet.get("counts", []))
    return []


class GbifSource:
    """Populates `taxon` with the German candidate set and marks `occurs_de`."""

    name = SOURCE_NAME
    license = LICENSE

    def run(self, conn: sqlite3.Connection) -> int:
        started = start_run(conn, self.name)
        keys = fetch_german_species_keys()
        written = 0
        for index, taxon_id in enumerate(sorted(keys), start=1):
            detail = get_json(f"{SPECIES_URL}/{taxon_id}")
            if not isinstance(detail, dict):
                continue
            canonical = detail.get("canonicalName") or detail.get("scientificName")
            if not canonical:
                continue
            conn.execute(
                """
                INSERT INTO taxon (taxon_id, scientific_name, canonical_name, rank,
                                   status, family, genus, occurs_de)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT (taxon_id) DO UPDATE SET occurs_de = 1
                """,
                (
                    taxon_id,
                    detail.get("scientificName"),
                    canonical,
                    detail.get("rank"),
                    detail.get("taxonomicStatus"),
                    detail.get("family"),
                    detail.get("genus"),
                ),
            )
            written += 1
            if index % 250 == 0:
                conn.commit()
                print(f"  GBIF: {index}/{len(keys)} taxa", flush=True)
        conn.commit()
        finish_run(conn, self.name, started, written, "complete")
        return written
