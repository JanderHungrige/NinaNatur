"""Classifying partners into groups a gardener recognises."""
import sqlite3

import pytest

from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.sources.insect_groups import (
    GROUP_CLADES,
    InsectGroup,
    apply_groups,
)


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    for name in ("Bombus terrestris", "Aglais io", "Episyrphus balteatus", "Formica rufa"):
        c.execute("INSERT INTO insect_de (canonical_name, occurrences) VALUES (?, 9)", (name,))
    c.commit()
    return c


def test_every_group_names_at_least_one_clade() -> None:
    assert set(GROUP_CLADES) == {g for g in InsectGroup}
    assert all(keys for keys in GROUP_CLADES.values())


def test_members_are_labelled_with_their_group(conn: sqlite3.Connection) -> None:
    apply_groups(conn, {
        InsectGroup.BEE: {"Bombus terrestris"},
        InsectGroup.BUTTERFLY: {"Aglais io"},
        InsectGroup.HOVERFLY: {"Episyrphus balteatus"},
    })
    got = {
        r["canonical_name"]: r["insect_group"]
        for r in conn.execute("SELECT canonical_name, insect_group FROM insect_de")
    }
    assert got["Bombus terrestris"] == "bee"
    assert got["Aglais io"] == "butterfly"
    assert got["Episyrphus balteatus"] == "hoverfly"


def test_an_unclassified_insect_keeps_its_row_and_stays_null(
    conn: sqlite3.Connection,
) -> None:
    """Beetles, wasps and flies are real visitors — dropping them would make the
    total disagree with the group breakdown for no defensible reason."""
    apply_groups(conn, {InsectGroup.BEE: {"Bombus terrestris"}})
    row = conn.execute(
        "SELECT insect_group FROM insect_de WHERE canonical_name = 'Formica rufa'"
    ).fetchone()
    assert row is not None
    assert row["insect_group"] is None


def test_rerunning_is_idempotent(conn: sqlite3.Connection) -> None:
    apply_groups(conn, {InsectGroup.BEE: {"Bombus terrestris"}})
    apply_groups(conn, {InsectGroup.BEE: {"Bombus terrestris"}})
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM insect_de WHERE insect_group = 'bee'"
    ).fetchone()["n"]
    assert n == 1


def test_a_species_in_two_groups_is_an_error_not_a_silent_last_write(
    conn: sqlite3.Connection,
) -> None:
    """It would mean the clade facets overlap, which is a data problem worth seeing."""
    with pytest.raises(ValueError, match="more than one group"):
        apply_groups(conn, {
            InsectGroup.BEE: {"Bombus terrestris"},
            InsectGroup.HOVERFLY: {"Bombus terrestris"},
        })


def test_names_not_on_the_german_list_are_ignored(conn: sqlite3.Connection) -> None:
    apply_groups(conn, {InsectGroup.BEE: {"Bombus terrestris", "Nichtdeutsche biene"}})
    n = conn.execute("SELECT COUNT(*) AS n FROM insect_de").fetchone()["n"]
    assert n == 4, "the checklist is not extended by classification"
