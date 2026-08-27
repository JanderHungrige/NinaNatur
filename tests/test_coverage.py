"""Coverage is the deliverable — its arithmetic must be exact, not approximate.

The candidate set is deliberately narrower than "taxa in Germany": a taxon with
no indicator values can never be matched to a bed, so counting it would measure
the size of the German flora instead of the usability of the data.
"""
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
        # An indicator value is what makes a taxon a candidate.
        upsert_trait(c, i, "ellenberg_l", value_num=5.0, source="TEST", license="CC0")
    return c


def _fill_core(c: sqlite3.Connection, taxon_id: int) -> None:
    for key in CORE_TRAITS:
        upsert_trait(c, taxon_id, key, value_num=5.0, source="TEST", license="CC0")


def test_german_taxon_without_indicator_values_is_not_a_candidate(
    conn: sqlite3.Connection,
) -> None:
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (8, 'Bare', 1)")
    report = compute_coverage(conn)
    assert report.candidates == 4
    assert report.german_taxa == 5, "the wider flora count stays visible for context"


def test_taxon_outside_germany_is_not_a_candidate(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (9, 'Alien', 0)")
    upsert_trait(conn, 9, "ellenberg_l", value_num=5.0, source="TEST", license="CC0")
    report = compute_coverage(conn)
    assert report.candidates == 4, "indicator values alone do not make a German candidate"


def test_core_complete_requires_every_core_trait(conn: sqlite3.Connection) -> None:
    _fill_core(conn, 1)
    _fill_core(conn, 2)
    for key in list(CORE_TRAITS)[:-1]:
        upsert_trait(conn, 3, key, value_num=5.0, source="TEST", license="CC0")
    report = compute_coverage(conn)
    assert report.core_complete == 2
    assert report.core_complete_pct == pytest.approx(50.0)


def test_per_trait_coverage_counts_candidates_only(conn: sqlite3.Connection) -> None:
    upsert_trait(conn, 1, "height_max_m", value_num=0.4, source="TEST", license="CC0")
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (9, 'Alien', 0)")
    upsert_trait(conn, 9, "height_max_m", value_num=0.9, source="TEST", license="CC0")
    report = compute_coverage(conn)
    assert report.per_trait["height_max_m"] == 1
    assert report.per_trait["flower_colour"] == 0


def test_a_taxon_with_two_sources_counts_once(conn: sqlite3.Connection) -> None:
    """Duplicate sources must not inflate coverage."""
    upsert_trait(conn, 1, "ellenberg_m", value_num=7.0, source="EIVE", license="CC-BY-4.0")
    upsert_trait(conn, 1, "ellenberg_m", value_num=6.5, source="GIFT", license="CC-BY-4.0")
    report = compute_coverage(conn)
    assert report.per_trait["ellenberg_m"] == 1


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
    assert report.with_interactions == 1
