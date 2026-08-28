"""The German bird checklist, and the promise that it leaves the score alone."""
import sqlite3

import pytest

from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.sources.birds_de import AVES_KEY, BirdsDeSource
from ninanatur.ingest.summarise import summarise_interactions


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:")
    init_schema(c)
    return c


def _insect(c: sqlite3.Connection, name: str) -> None:
    c.execute(
        "INSERT INTO insect_de (canonical_name, occurrences, clade) VALUES (?, 10, 'insect')",
        (name,),
    )


def _interaction(c: sqlite3.Connection, taxon_id: int, partner: str, kind: str) -> None:
    c.execute(
        """INSERT INTO interaction (taxon_id, partner_name, interaction_type,
           source, license, n_records) VALUES (?, ?, ?, 'GloBI', 'CC0', 1)""",
        (taxon_id, partner, kind),
    )


def test_existing_rows_are_insects_without_a_data_migration(conn: sqlite3.Connection) -> None:
    # The column defaults so that every row written before birds existed keeps
    # meaning exactly what it meant.
    conn.execute("INSERT INTO insect_de (canonical_name, occurrences) VALUES ('Apis mellifera', 5)")
    clade = conn.execute(
        "SELECT clade FROM insect_de WHERE canonical_name = 'Apis mellifera'"
    ).fetchone()["clade"]
    assert clade == "insect"


def test_birds_are_written_as_their_own_clade(conn: sqlite3.Connection) -> None:
    source = BirdsDeSource(fetch=lambda key: {"Turdus merula": 900, "Parus major": 800})
    assert source.run(conn) == 2
    rows = conn.execute("SELECT canonical_name, clade FROM insect_de ORDER BY 1").fetchall()
    assert [(r["canonical_name"], r["clade"]) for r in rows] == [
        ("Parus major", "bird"),
        ("Turdus merula", "bird"),
    ]


def test_it_asks_gbif_for_aves(conn: sqlite3.Connection) -> None:
    seen: list[int] = []

    def fetch(key: int) -> dict[str, int]:
        seen.append(key)
        return {}

    BirdsDeSource(fetch=fetch).run(conn)
    assert seen == [AVES_KEY]


def test_higher_ranks_are_refused(conn: sqlite3.Connection) -> None:
    """"Germany has Passeriformes" matched against a partner called
    "Passeriformes" is vacuously true and inflates every plant's count — the
    same trap the insect checklist documents."""
    source = BirdsDeSource(fetch=lambda key: {"Passeriformes": 5000, "Turdus merula": 900})
    assert source.run(conn) == 1
    names = [r["canonical_name"] for r in conn.execute("SELECT canonical_name FROM insect_de")]
    assert names == ["Turdus merula"]


def test_adding_birds_does_not_change_the_insect_count(conn: sqlite3.Connection) -> None:
    """The promise of this feature. The metric is called Insektenwert."""
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Salix caprea')")
    _insect(conn, "Apis mellifera")
    _interaction(conn, 1, "Apis mellifera", "visitedBy")
    _interaction(conn, 1, "Turdus merula", "eatenBy")
    conn.commit()

    def insect_partners() -> int:
        row = conn.execute(
            "SELECT german FROM partner_totals WHERE taxon_id = 1"
        ).fetchone()
        return int(row["german"])

    summarise_interactions(conn)
    before = insect_partners()

    BirdsDeSource(fetch=lambda key: {"Turdus merula": 900}).run(conn)
    summarise_interactions(conn)
    after = insect_partners()

    assert before == 1
    assert after == 1, "a bird leaked into the insect partner count"


def test_bird_partners_are_counted_in_their_own_table(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Sambucus nigra')")
    _interaction(conn, 1, "Turdus merula", "eatenBy")
    _interaction(conn, 1, "Sturnus vulgaris", "eatenBy")
    _interaction(conn, 1, "Ara macao", "eatenBy")  # not on the German list
    conn.commit()

    BirdsDeSource(fetch=lambda key: {"Turdus merula": 9, "Sturnus vulgaris": 8}).run(conn)
    summarise_interactions(conn)

    row = conn.execute("SELECT german FROM partner_birds WHERE taxon_id = 1").fetchone()
    assert row["german"] == 2, "a bird not recorded in Germany was counted"


def test_a_plant_with_no_bird_partners_has_no_row(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Anemone')")
    _insect(conn, "Apis mellifera")
    _interaction(conn, 1, "Apis mellifera", "visitedBy")
    conn.commit()
    summarise_interactions(conn)
    assert conn.execute("SELECT COUNT(*) n FROM partner_birds").fetchone()["n"] == 0
