"""Trait resolution: one answer, still attributable."""
import sqlite3

import pytest

from ninanatur.data.traits import (
    SOURCE_PRIORITY,
    UnknownTraitKey,
    resolve_trait,
    resolve_traits_for,
)
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:")
    init_schema(c)
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (1, 'Testus', 1)")
    return c


def test_resolved_value_carries_its_source_and_licence(conn: sqlite3.Connection) -> None:
    upsert_trait(conn, 1, "ellenberg_l", value_num=7.0, source="EIVE-1.0", license="CC-BY-4.0")
    r = resolve_trait(conn, 1, "ellenberg_l")
    assert r is not None
    assert r.value_num == 7.0
    assert r.source == "EIVE-1.0"
    assert r.license == "CC-BY-4.0"


def test_absent_trait_resolves_to_none_not_zero(conn: sqlite3.Connection) -> None:
    """Unknown and zero must never render the same — this keeps colour honest."""
    assert resolve_trait(conn, 1, "flower_colour") is None


def test_priority_decides_deterministically_when_sources_disagree(
    conn: sqlite3.Connection,
) -> None:
    upsert_trait(conn, 1, "height_max_m", value_num=0.9, source="GIFT", license="CC-BY-4.0")
    upsert_trait(conn, 1, "height_max_m", value_num=0.6, source="EIVE-1.0", license="CC-BY-4.0")
    r = resolve_trait(conn, 1, "height_max_m")
    assert r.source == SOURCE_PRIORITY[0]
    assert r.value_num == 0.6


def test_losing_values_stay_visible_rather_than_being_discarded(
    conn: sqlite3.Connection,
) -> None:
    """Disagreement is surfaced, not hidden — that is the whole provenance point."""
    upsert_trait(conn, 1, "height_max_m", value_num=0.9, source="GIFT", license="CC-BY-4.0")
    upsert_trait(conn, 1, "height_max_m", value_num=0.6, source="EIVE-1.0", license="CC-BY-4.0")
    r = resolve_trait(conn, 1, "height_max_m")
    assert [(a.source, a.value_num) for a in r.alternatives] == [("GIFT", 0.9)]


def test_a_single_source_has_no_alternatives(conn: sqlite3.Connection) -> None:
    upsert_trait(conn, 1, "height_max_m", value_num=0.6, source="GIFT", license="CC-BY-4.0")
    assert resolve_trait(conn, 1, "height_max_m").alternatives == ()


def test_an_unknown_source_ranks_below_known_ones(conn: sqlite3.Connection) -> None:
    """A new source must not silently outrank the curated ones by accident."""
    upsert_trait(conn, 1, "height_max_m", value_num=9.9, source="AAA-New", license="CC0")
    upsert_trait(conn, 1, "height_max_m", value_num=0.6, source="GIFT", license="CC-BY-4.0")
    assert resolve_trait(conn, 1, "height_max_m").source == "GIFT"


def test_bulk_read_returns_every_trait_for_a_taxon(conn: sqlite3.Connection) -> None:
    upsert_trait(conn, 1, "ellenberg_l", value_num=7.0, source="EIVE-1.0", license="CC-BY-4.0")
    upsert_trait(conn, 1, "flower_colour", value_text="blue", source="GIFT", license="CC-BY-4.0")
    traits = resolve_traits_for(conn, 1)
    assert set(traits) == {"ellenberg_l", "flower_colour"}
    assert traits["flower_colour"].value_text == "blue"


def test_text_and_numeric_values_both_survive(conn: sqlite3.Connection) -> None:
    upsert_trait(conn, 1, "flower_colour", value_text="yellow", source="GIFT", license="CC-BY-4.0")
    r = resolve_trait(conn, 1, "flower_colour")
    assert r.value_text == "yellow"
    assert r.value_num is None


def test_an_unknown_trait_key_is_rejected_not_silently_empty(
    conn: sqlite3.Connection,
) -> None:
    """A typo'd key returning None would look exactly like missing data."""
    with pytest.raises(UnknownTraitKey):
        resolve_trait(conn, 1, "ellenberg_x")
