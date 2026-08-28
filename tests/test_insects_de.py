"""Intersecting worldwide interaction records with what actually lives here."""
import sqlite3

import pytest

from ninanatur.data.interactions import PartnerCounts, german_partner_counts
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.summarise import summarise_interactions


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:")
    init_schema(c)
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (1, 'Testus', 1)")
    for name in ("Apis mellifera", "Bombus terrestris"):
        c.execute(
            "INSERT INTO insect_de (canonical_name, occurrences) VALUES (?, 500)", (name,)
        )
    return c


def _rel(c: sqlite3.Connection, partner: str, kind: str = "visitedBy") -> None:
    """Record a relation and rebuild the aggregates the read path uses."""
    c.execute(
        "INSERT INTO interaction (taxon_id, partner_name, interaction_type, source, license)"
        " VALUES (1, ?, ?, 'GloBI', 'CC0-1.0')",
        (partner, kind),
    )
    summarise_interactions(c)


def test_only_partners_recorded_in_germany_are_counted(conn: sqlite3.Connection) -> None:
    """The whole point — a global count ranks by research effort, not garden value."""
    _rel(conn, "Apis mellifera")
    _rel(conn, "Bombus terrestris")
    _rel(conn, "Hylaeus relegatus")  # New Zealand bee, not in the German list
    counts = german_partner_counts(conn, 1)
    assert counts.german == 2
    assert counts.global_total == 3


def test_unmatched_partners_are_reported_not_silently_dropped(
    conn: sqlite3.Connection,
) -> None:
    """A low match rate would invalidate the score, so it has to be visible."""
    _rel(conn, "Apis mellifera")
    _rel(conn, "Nonexistent bogusia")
    assert german_partner_counts(conn, 1).unmatched == 1


def test_relations_are_grouped_by_kind(conn: sqlite3.Connection) -> None:
    """Wave 5 weights a larval host differently from a flower visit."""
    _rel(conn, "Apis mellifera", "visitedBy")
    _rel(conn, "Bombus terrestris", "pollinatedBy")
    by_kind = german_partner_counts(conn, 1).by_kind
    assert by_kind == {"visitedBy": 1, "pollinatedBy": 1}


def test_a_plant_absent_from_globi_reports_none_not_zero(conn: sqlite3.Connection) -> None:
    """No data and no partners are different facts."""
    assert german_partner_counts(conn, 1) is None


def test_a_plant_with_only_foreign_partners_reports_zero_german(
    conn: sqlite3.Connection,
) -> None:
    """Here zero IS the answer — the records exist, none of them apply here."""
    _rel(conn, "Hylaeus relegatus")
    counts = german_partner_counts(conn, 1)
    assert isinstance(counts, PartnerCounts)
    assert counts.german == 0
    assert counts.global_total == 1


def test_the_same_partner_twice_counts_once(conn: sqlite3.Connection) -> None:
    _rel(conn, "Apis mellifera", "visitedBy")
    _rel(conn, "Apis mellifera", "pollinatedBy")
    assert german_partner_counts(conn, 1).german == 1


def test_canonical_name_strips_authorship_for_matching() -> None:
    """GloBI records binomials; GBIF facets carry authorship. Matching needs both aligned."""
    from ninanatur.ingest.sources.gbif import canonical_name

    assert canonical_name("Aglais io (Linnaeus, 1758)") == "Aglais io"
    assert canonical_name("Apis mellifera Linnaeus, 1758") == "Apis mellifera"
    assert canonical_name("Formica rufa") == "Formica rufa"


def test_canonical_name_collapses_subspecies_onto_the_species() -> None:
    """GloBI records the species, so keeping the trinomial would simply never match."""
    from ninanatur.ingest.sources.gbif import canonical_name

    assert canonical_name("Apis mellifera carnica Pollmann, 1879") == "Apis mellifera"


def test_higher_rank_names_are_excluded_from_the_species_checklist() -> None:
    """A GloBI partner named "Diptera" matching "Germany has Diptera" is vacuous.

    A third of GBIF's name facet is orders and families from records identified
    no further; counting them would inflate every plant's partner count.
    """
    from ninanatur.ingest.sources.gbif import canonical_name

    for higher_rank in ("Diptera", "Chironomidae", "Syrphidae"):
        assert " " not in canonical_name(higher_rank), "single-word names are not species"
