"""The aggregates that make the catalogue shippable."""
import sqlite3

import pytest

from ninanatur.data.interactions import german_partner_counts
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.summarise import summarise_interactions


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (1, 'Plant', 1)")
    for name in ("Apis mellifera", "Bombus terrestris"):
        c.execute("INSERT INTO insect_de (canonical_name, occurrences) VALUES (?, 9)", (name,))
    return c


def _rel(c: sqlite3.Connection, partner: str, kind: str = "visitedBy") -> None:
    c.execute(
        "INSERT INTO interaction (taxon_id, partner_name, interaction_type, source, license)"
        " VALUES (1, ?, ?, 'GloBI', 'CC0-1.0')",
        (partner, kind),
    )


def test_summarising_counts_only_german_partners(conn: sqlite3.Connection) -> None:
    _rel(conn, "Apis mellifera")
    _rel(conn, "Hylaeus relegatus")  # not on the German list
    summarise_interactions(conn)
    counts = german_partner_counts(conn, 1)
    assert counts is not None
    assert (counts.german, counts.global_total, counts.unmatched) == (1, 2, 1)


def test_rerunning_replaces_rather_than_accumulates(conn: sqlite3.Connection) -> None:
    """Re-ingesting must not double every count."""
    _rel(conn, "Apis mellifera")
    summarise_interactions(conn)
    summarise_interactions(conn)
    assert german_partner_counts(conn, 1).german == 1


def test_a_removed_relation_disappears_from_the_summary(conn: sqlite3.Connection) -> None:
    """The aggregate is derived, so a stale row would be a lie the UI repeats."""
    _rel(conn, "Apis mellifera")
    _rel(conn, "Bombus terrestris")
    summarise_interactions(conn)
    assert german_partner_counts(conn, 1).german == 2

    conn.execute("DELETE FROM interaction WHERE partner_name = 'Bombus terrestris'")
    summarise_interactions(conn)
    assert german_partner_counts(conn, 1).german == 1


def test_a_plant_with_no_relations_is_absent_not_zero(conn: sqlite3.Connection) -> None:
    """No data and no partners stay different facts through the aggregate too."""
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (2, 'Other', 1)")
    _rel(conn, "Apis mellifera")
    summarise_interactions(conn)
    assert german_partner_counts(conn, 2) is None


def test_kinds_are_summarised_separately(conn: sqlite3.Connection) -> None:
    """Wave 5 weights a larval host differently from a flower visit."""
    _rel(conn, "Apis mellifera", "visitedBy")
    _rel(conn, "Bombus terrestris", "eatenBy")
    summarise_interactions(conn)
    assert german_partner_counts(conn, 1).by_kind == {"visitedBy": 1, "eatenBy": 1}


def test_summarising_before_the_insect_list_exists_yields_zero_not_an_error(
    conn: sqlite3.Connection,
) -> None:
    """It runs, and it is wrong — which is why the CLI orders it after insects-de.
    Zero German partners is a legitimate answer, so nothing would flag this."""
    conn.execute("DELETE FROM insect_de")
    _rel(conn, "Apis mellifera")
    summarise_interactions(conn)
    counts = german_partner_counts(conn, 1)
    assert counts is not None and counts.german == 0
