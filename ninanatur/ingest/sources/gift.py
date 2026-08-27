"""GIFT — Global Inventory of Floras and Traits (Weigelt et al., CC-BY-4.0).

Supplies the traits EIVE does not carry: height, flowering window, flower
colour, growth form and life form. GIFT keys species by its own `work_ID`, so
the species list is pulled once and joined locally before name resolution.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ninanatur.ingest.http import get_json
from ninanatur.ingest.names import NameResolver
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.ingest.sources.base import finish_run, start_run

SOURCE_NAME = "GIFT"
LICENSE = "CC-BY-4.0"
API_URL = "https://gift.uni-goettingen.de/api/extended/index.php"
PAGE_SIZE = 10000

# GIFT trait id -> (canonical trait key, numeric?, unit)
GIFT_TRAITS: dict[str, tuple[str, bool, str | None]] = {
    "1.6.2": ("height_max_m", True, "m"),
    "3.7.1": ("flowering_start_month", True, "month"),
    "3.7.2": ("flowering_end_month", True, "month"),
    "3.21.1": ("flower_colour", False, None),
    "1.2.2": ("growth_form", False, None),
    "2.3.1": ("life_form", False, None),
    "2.1.1": ("lifecycle", False, None),
    "3.6.2": ("pollination_syndrome", False, None),
}

MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_month(raw: str) -> int | None:
    """GIFT reports months either as names or as 1-12 numbers — accept both."""
    token = raw.strip().lower()[:3]
    if token in MONTH_NAMES:
        return MONTH_NAMES[token]
    try:
        month = int(float(raw))
    except (TypeError, ValueError):
        return None
    return month if 1 <= month <= 12 else None


def fetch_species_index() -> dict[int, str]:
    """Return {work_ID: species name} for the whole GIFT backbone."""
    payload = get_json(API_URL, {"query": "species"})
    index: dict[int, str] = {}
    for row in payload or []:
        name = (row.get("work_species") or "").strip()
        if name:
            index[int(row["work_ID"])] = name
    return index


def fetch_trait(trait_id: str) -> list[dict[str, Any]]:
    """Return all GIFT rows for one trait id.

    The API caps a response at `PAGE_SIZE` rows and silently truncates rather
    than signalling more — so paging with `startat` is mandatory, not an
    optimisation. Without it, traits like flowering start lose half their rows.
    """
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = get_json(
            API_URL,
            {"query": "traits", "traitid": trait_id, "biased": "no", "startat": offset},
        )
        page_rows = list(page or [])
        rows.extend(page_rows)
        if len(page_rows) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


class GiftSource:
    name = SOURCE_NAME
    license = LICENSE

    def run(self, conn: sqlite3.Connection, limit_to_de: bool = True) -> int:
        started = start_run(conn, self.name)
        species = fetch_species_index()
        wanted = self._wanted_names(conn) if limit_to_de else None
        resolver = NameResolver(conn)
        written = 0

        for trait_id, (trait_key, numeric, unit) in GIFT_TRAITS.items():
            rows = fetch_trait(trait_id)
            print(f"  GIFT {trait_id} -> {trait_key}: {len(rows)} rows", flush=True)
            for row in rows:
                name = species.get(int(row.get("work_ID", -1)))
                if not name or (wanted is not None and name not in wanted):
                    continue
                value_num, value_text = self._coerce(row.get("trait_value"), trait_key, numeric)
                if value_num is None and value_text is None:
                    continue
                taxon_id = resolver.resolve(name, source=self.name, only_known=True)
                if taxon_id is None:
                    continue
                upsert_trait(
                    conn, taxon_id, trait_key, value_num=value_num, value_text=value_text,
                    unit=unit, source=self.name, license=self.license, confidence=0.8,
                )
                written += 1
            conn.commit()

        finish_run(conn, self.name, started, written, "complete")
        return written

    @staticmethod
    def _wanted_names(conn: sqlite3.Connection) -> set[str]:
        """Restrict the join to German candidates — GIFT is global and mostly irrelevant here."""
        return {
            str(r["canonical_name"])
            for r in conn.execute("SELECT canonical_name FROM taxon WHERE occurs_de = 1").fetchall()
        }

    @staticmethod
    def _coerce(raw: Any, trait_key: str, numeric: bool) -> tuple[float | None, str | None]:
        if raw is None or str(raw).strip() == "":
            return None, None
        text = str(raw).strip()
        if trait_key.endswith("_month"):
            month = parse_month(text)
            return (float(month), None) if month is not None else (None, None)
        if numeric:
            try:
                return float(text), None
            except ValueError:
                return None, None
        return None, text
