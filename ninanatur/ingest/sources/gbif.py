"""GBIF — taxonomy backbone and the German candidate set.

The candidate set is derived from actual occurrence records rather than from a
curated list: every vascular plant species with observations in Germany. Pulled
via the occurrence facet, which returns backbone species keys directly, so no
name matching is involved and the whole set costs a handful of requests.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ninanatur.ingest.http import get_json
from ninanatur.ingest.sources.base import finish_run, start_run

SOURCE_NAME = "GBIF"
LICENSE = "CC-BY-4.0"
OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"
SPECIES_URL = "https://api.gbif.org/v1/species"
TRACHEOPHYTA_KEY = 7707728
INSECTA_KEY = 216
FACET_PAGE = 1000
MIN_OCCURRENCES = 5


def fetch_german_species_keys(
    max_species: int = 20000,
    taxon_key: int = TRACHEOPHYTA_KEY,
    min_occurrences: int = MIN_OCCURRENCES,
) -> dict[int, int]:
    """Return {speciesKey: occurrence count} for a clade recorded in Germany.

    Parameterised by clade so the insect checklist reuses this rather than
    duplicating it: plants are `TRACHEOPHYTA_KEY`, insects are `INSECTA_KEY`.

    `min_occurrences` filters out single stray records, which are typically
    misidentifications or escapes rather than an established presence.
    """
    keys: dict[int, int] = {}
    offset = 0
    while offset < max_species:
        payload = get_json(
            OCCURRENCE_URL,
            {
                "country": "DE",
                "taxonKey": taxon_key,
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
            if count >= min_occurrences:
                keys[int(entry["name"])] = count
        if len(counts) < FACET_PAGE:
            break
        offset += FACET_PAGE
    return keys


def _facet_counts(payload: Any, field: str = "SPECIES_KEY") -> list[dict[str, Any]]:
    for facet in (payload or {}).get("facets", []):
        if facet.get("field") == field:
            return list(facet.get("counts", []))
    return []


def fetch_german_scientific_names(
    taxon_key: int, max_names: int = 60000, min_occurrences: int = MIN_OCCURRENCES
) -> dict[str, int]:
    """Return {scientificName: occurrence count} for a clade recorded in Germany.

    Faceting on the name rather than the species key avoids one detail request per
    species — ~19 calls instead of ~19,000 for the German insects. The names carry
    authorship ("Aglais io (Linnaeus, 1758)"), which `canonical_name` strips.
    """
    names: dict[str, int] = {}
    offset = 0
    while offset < max_names:
        payload = get_json(
            OCCURRENCE_URL,
            {
                "country": "DE",
                "taxonKey": taxon_key,
                "facet": "SCIENTIFIC_NAME",
                "facetLimit": FACET_PAGE,
                "facetOffset": offset,
                "limit": 0,
            },
        )
        counts = _facet_counts(payload, "SCIENTIFIC_NAME")
        if not counts:
            break
        for entry in counts:
            count = int(entry["count"])
            if count >= min_occurrences:
                names[str(entry["name"])] = count
        if len(counts) < FACET_PAGE:
            break
        offset += FACET_PAGE
    return names


def canonical_name(scientific_name: str) -> str:
    """Strip authorship and rank down to the binomial GloBI partner names use.

    "Aglais io (Linnaeus, 1758)" -> "Aglais io". Subspecies collapse to the
    species deliberately: GloBI records "Apis mellifera", not the subspecies, so
    keeping the trinomial would simply fail to match.
    """
    tokens = scientific_name.replace("\u00d7", "").split()
    binomial = [t for t in tokens[:2] if t and not t.startswith("(")]
    return " ".join(binomial)


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
