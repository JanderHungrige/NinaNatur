"""Coverage is the deliverable — its arithmetic must be exact, not approximate."""
import sqlite3

import pytest

from dbnatura.ingest.coverage import CORE_TRAITS, compute_coverage
from dbnatura.ingest.db import connect, init_schema
from dbnatura.ingest.provenance import upsert_trait


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:")
    init_schema(c)
    for i in (1, 2, 3, 4):
        c.execute(
            "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
            (i, f"Testus specius{i}"),
        )
    return c


def _fill_core(c: sqlite3.Connection, taxon_id: int) -> None:
    for key in CORE_TRAITS:
        upsert_trait(c, taxon_id, key, value_num=5.0, source="TEST", license="CC0")


def test_coverage_counts_only_candidate_taxa(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (9, 'X', 0)")
    _fill_core(conn, 1)
    report = compute_coverage(conn)
    assert report.candidates == 4, "taxa outside Germany must not enter the denominator"


def test_core_complete_requires_every_core_trait(conn: sqlite3.Connection) -> None:
    _fill_core(conn, 1)
    _fill_core(conn, 2)
    for key in list(CORE_TRAITS)[:-1]:
        upsert_trait(conn, 3, key, value_num=5.0, source="TEST", license="CC0")
    report = compute_coverage(conn)
    assert report.core_complete == 2
    assert report.core_complete_pct == pytest.approx(50.0)


def test_per_trait_coverage_is_reported(conn: sqlite3.Connection) -> None:
    upsert_trait(conn, 1, "ellenberg_l", value_num=7.0, source="TEST", license="CC0")
    upsert_trait(conn, 2, "ellenberg_l", value_num=6.0, source="TEST", license="CC0")
    report = compute_coverage(conn)
    assert report.per_trait["ellenberg_l"] == 2
    assert report.per_trait["height_max_m"] == 0


def test_a_taxon_with_two_sources_counts_once(conn: sqlite3.Connection) -> None:
    """Duplicate sources must not inflate coverage."""
    upsert_trait(conn, 1, "ellenberg_l", value_num=7.0, source="EIVE", license="CC-BY-4.0")
    upsert_trait(conn, 1, "ellenberg_l", value_num=6.5, source="GIFT", license="CC-BY-4.0")
    report = compute_coverage(conn)
    assert report.per_trait["ellenberg_l"] == 1


def test_full_complete_requires_colour_and_interaction(conn: sqlite3.Connection) -> None:
    _fill_core(conn, 1)
    upsert_trait(conn, 1, "flower_colour", value_text="yellow", source="TEST", license="CC0")
    _fill_core(conn, 2)
    upsert_trait(conn, 2, "flower_colour", value_text="blue", source="TEST", license="CC0")
    conn.execute(
        "INSERT INTO interaction (taxon_id, partner_name, interaction_type, source, license)"
        " VALUES (2, 'Apis mellifera', 'visitsFlowersOf', 'GloBI', 'CC0')"
    )
    report = compute_coverage(conn)
    assert report.full_complete == 1, "taxon 1 has colour but no interaction — not full"
