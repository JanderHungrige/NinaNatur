"""EIVE 1.0 — Ecological Indicator Values for Europe (Dengler et al. 2023, CC-BY-4.0).

Supplies the site-condition axes the bed matcher runs on: light, moisture,
nutrients, soil reaction and temperature, on a continuous 0-10 scale.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from ninanatur.ingest.http import download
from ninanatur.ingest.names import NameResolver
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.ingest.sources.base import TraitRecord, finish_run, start_run

SOURCE_NAME = "EIVE-1.0"
LICENSE = "CC-BY-4.0"
DOI_URL = "https://zenodo.org/records/7534792/files/EIVE_Paper_1.0_SM_08.xlsx?download=1"
LOCAL_FILE = Path("data/raw/EIVE_SM_08.xlsx")
SHEET = "mainTable"

# Indicator values, plus the niche width EIVE reports beside each one. The widths
# are what let fit scoring distinguish a generalist from a fussy species instead
# of applying one tolerance band to everything (see 03-niche-fit).
EIVE_TRAIT_MAP: dict[str, str] = {
    "EIVEres-L": "ellenberg_l",
    "EIVEres-M": "ellenberg_m",
    "EIVEres-N": "ellenberg_n",
    "EIVEres-R": "ellenberg_r",
    "EIVEres-T": "ellenberg_t",
    "EIVEres-L.nw3": "ellenberg_l_nw",
    "EIVEres-M.nw3": "ellenberg_m_nw",
    "EIVEres-N.nw3": "ellenberg_n_nw",
    "EIVEres-R.nw3": "ellenberg_r_nw",
    "EIVEres-T.nw3": "ellenberg_t_nw",
}

ACCEPTED_RANKS = {"species", "subspecies", "variety"}


def parse_eive_frame(frame: pd.DataFrame) -> list[TraitRecord]:
    """Turn the EIVE main table into normalised trait records.

    Non-species ranks are dropped — a genus-level indicator value would be
    attached to the wrong thing. Missing values are skipped, never coerced to 0,
    which on a 0-10 scale would read as an extreme rather than as absent.
    """
    records: list[TraitRecord] = []
    present = [(col, key) for col, key in EIVE_TRAIT_MAP.items() if col in frame.columns]
    # Column access by label, not itertuples: pandas rewrites names that are not
    # valid identifiers ("EIVEres-L") to positional "_N", which loses the mapping.
    for _, row in frame.iterrows():
        rank = str(row.get("TaxonRank") or "").strip().lower()
        if rank not in ACCEPTED_RANKS:
            continue
        name = str(row.get("TaxonConcept") or "").strip()
        if not name:
            continue
        for column, trait_key in present:
            value = row[column]
            if value is None or pd.isna(value):
                continue
            records.append(TraitRecord(name=name, trait_key=trait_key, value=float(value)))
    return records


class EiveSource:
    name = SOURCE_NAME
    license = LICENSE

    def run(self, conn: sqlite3.Connection, only_known: bool = True) -> int:
        """With `only_known` (the default), EIVE rows are attached only to taxa already
        in the candidate set — EIVE is European, the candidate set is German."""
        started = start_run(conn, self.name)
        download(DOI_URL, LOCAL_FILE)
        frame = pd.read_excel(LOCAL_FILE, sheet_name=SHEET)
        records = parse_eive_frame(frame)

        resolver = NameResolver(conn)
        written = 0
        by_name: dict[str, list[TraitRecord]] = {}
        for record in records:
            by_name.setdefault(record.name, []).append(record)

        for index, (name, group) in enumerate(by_name.items(), start=1):
            taxon_id = resolver.resolve(name, source=self.name, only_known=only_known)
            if taxon_id is None:
                continue
            for record in group:
                upsert_trait(
                    conn,
                    taxon_id,
                    record.trait_key,
                    value_num=record.value,
                    source=self.name,
                    license=self.license,
                    confidence=0.9,
                )
                written += 1
            if index % 500 == 0:
                conn.commit()
                print(f"  EIVE: {index}/{len(by_name)} taxa resolved", flush=True)

        conn.commit()
        finish_run(conn, self.name, started, written, "complete")
        return written
