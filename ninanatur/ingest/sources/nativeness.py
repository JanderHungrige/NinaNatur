"""Whether a species is native to Germany.

`occurs_de` only ever meant *recorded in Germany*, which is equally true of
Vitis riparia and of Impatiens glandulifera. The landing page promises native
plants; this is what lets it mean something.

GBIF surfaces WCVP/Euro+Med distributions in two shapes, and both must be parsed
— the unstructured one is where the invasive species live, because they are the
ones with sprawling introduced ranges.
"""
from __future__ import annotations

import re
import sqlite3
from enum import Enum
from typing import Any

from ninanatur.ingest.http import get_json
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.ingest.sources.base import finish_run, start_run

SOURCE_NAME = "GBIF-WCVP"
LICENSE = "CC-BY-4.0"
TRAIT_KEY = "native_de"
SPECIES_URL = "https://api.gbif.org/v1/species"

# Whole word, so "Germaniella Reserve" cannot pass for Germany.
GERMANY = re.compile(r"\bGermany\b", re.IGNORECASE)
# The Euro+Med convention: "[I]" marks a region the species was introduced to.
INTRODUCED_MARK = "[i]"


class Establishment(Enum):
    """How a species came to be here — or that we do not know."""

    NATIVE = "native"
    INTRODUCED = "introduced"
    UNKNOWN = "unknown"


def _german_segment(locality: str) -> str | None:
    """The part of a long locality string that names Germany.

    Segments are separated by semicolons, so a marker on a later country cannot
    bleed onto Germany: "Germany; ... USA [I]" is two segments, not one.
    """
    for segment in locality.split(";"):
        if GERMANY.search(segment):
            return segment
    return None


def parse_german_establishment(distributions: list[dict[str, Any]]) -> Establishment:
    """Read native-or-introduced for Germany out of GBIF's distributions.

    An explicit `establishmentMeans` wins outright. Otherwise the locality string
    is read: the segment naming Germany, and whether `[I]` is attached to it.

    Returns UNKNOWN when there is no German entry at all. A gap in the data is
    not evidence that a plant belongs here.
    """
    fallback = Establishment.UNKNOWN
    for entry in distributions:
        locality = str(entry.get("locality") or "")
        segment = _german_segment(locality)
        if segment is None:
            continue

        means = str(entry.get("establishmentMeans") or "").strip().lower()
        if means.startswith("native"):
            return Establishment.NATIVE
        if means.startswith("introduc"):
            return Establishment.INTRODUCED

        # No structured value: fall back to the Euro+Med marker on this segment.
        fallback = (
            Establishment.INTRODUCED
            if INTRODUCED_MARK in segment.lower()
            else Establishment.NATIVE
        )
    return fallback


class NativenessSource:
    """Fills `native_de` for every German candidate."""

    name = SOURCE_NAME
    license = LICENSE

    def run(self, conn: sqlite3.Connection, limit: int | None = None) -> int:
        started = start_run(conn, self.name)
        rows = conn.execute(
            "SELECT taxon_id, canonical_name FROM taxon WHERE occurs_de = 1"
            " ORDER BY canonical_name"
        ).fetchall()
        if limit is not None:
            rows = rows[:limit]

        written = 0
        for index, row in enumerate(rows, start=1):
            taxon_id = int(row["taxon_id"])
            payload = get_json(f"{SPECIES_URL}/{taxon_id}/distributions", {"limit": 300})
            results = payload.get("results", []) if isinstance(payload, dict) else []
            establishment = parse_german_establishment(results)
            upsert_trait(
                conn,
                taxon_id,
                TRAIT_KEY,
                value_text=establishment.value,
                source=self.name,
                license=self.license,
                confidence=0.6 if establishment is Establishment.UNKNOWN else 0.9,
            )
            written += 1
            if index % 250 == 0:
                conn.commit()
                print(f"  nativeness: {index}/{len(rows)}", flush=True)

        conn.commit()
        finish_run(conn, self.name, started, written, "complete")
        return written
