"""Name resolution — the join key for the whole database.

Each source spells taxa its own way. Everything passes through GBIF's matching
API so that EIVE's `Achillea millefolium`, GIFT's `Achillea millefolium L.` and
GloBI's `Achillea millefolium` land on one taxon_id. Results are cached in
`taxon_name`, so a name costs at most one lookup ever.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Protocol

from dbnatura.ingest.http import get_json

GBIF_MATCH_URL = "https://api.gbif.org/v1/species/match"
MIN_MATCH_CONFIDENCE = 90
REJECTED_MATCH_TYPES = frozenset({"NONE", "HIGHERRANK"})
ACCEPTED_RANKS = frozenset({"SPECIES", "SUBSPECIES", "VARIETY"})


class SpeciesMatcher(Protocol):
    """The one call NameResolver needs — kept narrow so tests can substitute it."""

    def match(self, name: str) -> dict[str, Any]: ...


class GbifMatcher:
    """Live GBIF backbone matching."""

    def match(self, name: str) -> dict[str, Any]:
        result = get_json(GBIF_MATCH_URL, {"name": name, "kingdom": "Plantae"})
        return result if isinstance(result, dict) else {}


class NameResolver:
    """Resolves raw source names to canonical GBIF taxon ids, with caching."""

    def __init__(self, conn: sqlite3.Connection, matcher: SpeciesMatcher | None = None) -> None:
        self.conn = conn
        self.matcher = matcher or GbifMatcher()

    def resolve(self, raw_name: str, *, source: str, only_known: bool = False) -> int | None:
        """Return the taxon id for `raw_name`, or None when no usable match exists.

        Resolution is tried in cost order: the per-source cache, then an exact
        match against canonical names already in `taxon`, then the network. With
        `only_known` set, the network step is skipped entirely — used when the
        candidate set is already established and names outside it are irrelevant,
        which turns a 50-minute API crawl into a local join.

        A rejected match is still cached, so an unresolvable name is never
        looked up twice and stays visible in the coverage report.
        """
        cached = self.conn.execute(
            "SELECT taxon_id, match_type FROM taxon_name WHERE raw_name = ? AND source = ?",
            (raw_name, source),
        ).fetchone()
        if cached is not None:
            return int(cached["taxon_id"]) if cached["taxon_id"] is not None else None

        local = self.conn.execute(
            "SELECT taxon_id FROM taxon WHERE canonical_name = ?", (raw_name,)
        ).fetchone()
        if local is not None:
            local_id = int(local["taxon_id"])
            self.conn.execute(
                "INSERT OR REPLACE INTO taxon_name"
                " (raw_name, source, taxon_id, match_type, confidence) VALUES (?, ?, ?, ?, ?)",
                (raw_name, source, local_id, "LOCAL", 100),
            )
            return local_id

        if only_known:
            return None

        match = self.matcher.match(raw_name)
        taxon_id = self._accept(match)
        if taxon_id is not None:
            self._store_taxon(taxon_id, match)

        self.conn.execute(
            "INSERT OR REPLACE INTO taxon_name (raw_name, source, taxon_id, match_type, confidence)"
            " VALUES (?, ?, ?, ?, ?)",
            (raw_name, source, taxon_id, match.get("matchType"), match.get("confidence")),
        )
        return taxon_id

    @staticmethod
    def _accept(match: dict[str, Any]) -> int | None:
        """Apply the acceptance rules — a weak match must not carry traits."""
        if match.get("matchType") in REJECTED_MATCH_TYPES:
            return None
        if int(match.get("confidence") or 0) < MIN_MATCH_CONFIDENCE:
            return None
        if str(match.get("rank") or "").upper() not in ACCEPTED_RANKS:
            return None
        key = match.get("usageKey")
        return int(key) if key is not None else None

    def _store_taxon(self, taxon_id: int, match: dict[str, Any]) -> None:
        canonical = match.get("canonicalName") or match.get("scientificName")
        if not canonical:
            return
        self.conn.execute(
            """
            INSERT INTO taxon (taxon_id, scientific_name, canonical_name, rank,
                               status, family, genus, accepted_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (taxon_id) DO UPDATE SET
                scientific_name = COALESCE(excluded.scientific_name, taxon.scientific_name),
                family          = COALESCE(excluded.family, taxon.family),
                genus           = COALESCE(excluded.genus, taxon.genus)
            """,
            (
                taxon_id,
                match.get("scientificName"),
                canonical,
                match.get("rank"),
                match.get("status"),
                match.get("family"),
                match.get("genus"),
                match.get("acceptedUsageKey"),
            ),
        )
