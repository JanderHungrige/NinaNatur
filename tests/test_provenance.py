"""Provenance is the one invariant the whole DB rests on: no trait without a source."""
import sqlite3

import pytest

from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import ProvenanceError, upsert_trait


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:")
    init_schema(c)
    c.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Achillea millefolium')")
    return c


def test_upsert_trait_stores_value_with_full_provenance(conn: sqlite3.Connection) -> None:
    upsert_trait(conn, 1, "ellenberg_l", value_num=7.5, source="EIVE-1.0",
                 license="CC-BY-4.0", confidence=0.9)
    row = conn.execute(
        "SELECT value_num, source, license, confidence, retrieved_at FROM trait"
    ).fetchone()
    assert row["value_num"] == 7.5
    assert row["source"] == "EIVE-1.0"
    assert row["license"] == "CC-BY-4.0"
    assert row["confidence"] == 0.9
    assert row["retrieved_at"], "retrieved_at must be stamped automatically"


def test_upsert_trait_rejects_missing_source(conn: sqlite3.Connection) -> None:
    with pytest.raises(ProvenanceError):
        upsert_trait(conn, 1, "ellenberg_l", value_num=7.5, source="", license="CC-BY-4.0")


def test_upsert_trait_rejects_missing_license(conn: sqlite3.Connection) -> None:
    with pytest.raises(ProvenanceError):
        upsert_trait(conn, 1, "ellenberg_l", value_num=7.5, source="EIVE-1.0", license="")


def test_two_sources_disagreeing_both_persist(conn: sqlite3.Connection) -> None:
    """Sources must not overwrite each other — disagreement stays visible."""
    upsert_trait(conn, 1, "height_max_m", value_num=0.6, source="GIFT", license="CC-BY-4.0")
    upsert_trait(conn, 1, "height_max_m", value_num=0.8, source="LEDA", license="CC-BY-4.0")
    rows = conn.execute(
        "SELECT source, value_num FROM trait WHERE trait_key='height_max_m' ORDER BY source"
    ).fetchall()
    assert [(r["source"], r["value_num"]) for r in rows] == [("GIFT", 0.6), ("LEDA", 0.8)]


def test_rerunning_same_source_is_idempotent(conn: sqlite3.Connection) -> None:
    upsert_trait(conn, 1, "height_max_m", value_num=0.6, source="GIFT", license="CC-BY-4.0")
    upsert_trait(conn, 1, "height_max_m", value_num=0.7, source="GIFT", license="CC-BY-4.0")
    rows = conn.execute("SELECT value_num FROM trait WHERE trait_key='height_max_m'").fetchall()
    assert len(rows) == 1, "same source must update in place, not duplicate"
    assert rows[0]["value_num"] == 0.7


def test_untrusted_api_text_is_stored_verbatim_not_interpreted(conn: sqlite3.Connection) -> None:
    """API-supplied text is untrusted — parameterised binding must keep it inert."""
    hostile = "white'); DELETE FROM trait WHERE ('1'='1"
    upsert_trait(conn, 1, "flower_colour", value_text=hostile,
                 source="GIFT", license="CC-BY-4.0")
    rows = conn.execute("SELECT value_text FROM trait").fetchall()
    assert len(rows) == 1
    assert rows[0]["value_text"] == hostile, "value must round-trip unchanged"
