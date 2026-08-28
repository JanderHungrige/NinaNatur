"""German names, and the folding that makes them findable."""
import sqlite3

import pytest

from ninanatur.data.names import normalise, preferred_name, search_names
from ninanatur.ingest.db import connect, init_schema

# --- folding ---------------------------------------------------------------

@pytest.mark.parametrize("written", ["Schlüsselblume", "schlusselblume", "SCHLÜSSELBLUME"])
def test_an_umlaut_folds_to_its_bare_vowel(written: str) -> None:
    """Users type what their keyboard makes easy, not what the botanist wrote."""
    assert normalise(written) == normalise("Schlüsselblume")


def test_the_ue_digraph_is_deliberately_not_collapsed() -> None:
    """Collapsing "ue" to "u" would turn Feuer into Feur.

    Normalisation alone therefore cannot unify all three spellings — the data
    does it instead, because GBIF supplies the "ue" form as a name of its own.
    Asserted so nobody "fixes" this later and quietly mangles every word where
    the digraph is not an umlaut.
    """
    assert normalise("Schluesselblume") != normalise("Schlüsselblume")
    assert normalise("Feuer") == "feuer"


def test_hyphens_and_spaces_do_not_matter() -> None:
    assert normalise("Sal-Weide") == normalise("Sal Weide") == normalise("Salweide")


def test_eszett_folds_to_ss() -> None:
    assert normalise("Großer Wiesenknopf") == normalise("Grosser Wiesenknopf")


def test_folding_is_idempotent() -> None:
    once = normalise("Frühlings-Schlüsselblume")
    assert normalise(once) == once


def test_distinct_names_do_not_collide() -> None:
    assert normalise("Wiesensalbei") != normalise("Wiesenknopf")


# --- preferred name --------------------------------------------------------

def test_the_shortest_plain_name_is_preferred() -> None:
    """A display name is read, not parsed."""
    names = ["Gewöhnliche Schafgarbe (Artengruppe)", "Gemeine Schafgarbe", "Schafgarbe"]
    assert preferred_name(names) == "Schafgarbe"


def test_a_parenthetical_qualifier_loses_even_when_shorter() -> None:
    assert preferred_name(["Salweide (Artengruppe)", "Sal-Weide"]) == "Sal-Weide"


def test_no_names_yields_none_so_the_binomial_can_stand() -> None:
    """A species without a German name keeps its scientific one — no placeholder."""
    assert preferred_name([]) is None


# --- search ----------------------------------------------------------------

@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    for tid, sci, german in (
        (1, "Salix caprea", ["Sal-Weide", "Salweide"]),
        # GBIF supplies both spellings; the "ue" form is what makes that query work.
        (2, "Primula veris", ["Echte Schlüsselblume", "Fruehlings-Schluesselblume"]),
        (3, "Salvia pratensis", ["Wiesen-Salbei"]),
        (4, "Nurlatein spec", []),
    ):
        c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
                  (tid, sci))
        for name in german:
            c.execute(
                "INSERT INTO vernacular_name (taxon_id, name, normalised, is_preferred, source)"
                " VALUES (?, ?, ?, ?, 'GBIF')",
                (tid, name, normalise(name), int(name == german[0])),
            )
    c.commit()
    return c


def test_a_german_name_finds_its_species(conn: sqlite3.Connection) -> None:
    assert search_names(conn, "Sal-Weide") == [1]


@pytest.mark.parametrize(
    "typed", ["Schlüsselblume", "schlusselblume", "Schluesselblume"]
)
def test_every_spelling_finds_the_same_species(
    conn: sqlite3.Connection, typed: str
) -> None:
    """The requirement is finding the plant, not folding to one key. Bare-vowel
    folding covers two spellings; GBIF supplying the "ue" form covers the third."""
    assert search_names(conn, typed) == [2]


def test_the_distinctive_word_is_enough(conn: sqlite3.Connection) -> None:
    """German plant names are adjective-noun and people type the noun. Prefix
    matching would find nothing in "Echte Schlüsselblume", which reads as an
    empty catalogue rather than a mismatched query."""
    assert search_names(conn, "Salbei") == [3]
    assert search_names(conn, "Weide") == [1]


def test_a_scientific_name_finds_it_too(conn: sqlite3.Connection) -> None:
    """Someone typing "Salix" and someone typing "Weide" want the same thing."""
    assert search_names(conn, "Salix") == [1]


def test_a_leading_word_still_works(conn: sqlite3.Connection) -> None:
    assert search_names(conn, "Wiesen") == [3]


def test_a_shared_prefix_returns_both(conn: sqlite3.Connection) -> None:
    assert sorted(search_names(conn, "Sal")) == [1, 3]


def test_nothing_matching_returns_nothing_rather_than_guessing(
    conn: sqlite3.Connection,
) -> None:
    """Fuzzy matching on 3,000 species produces confident nonsense."""
    assert search_names(conn, "Rhabarbermarmelade") == []


def test_a_species_with_no_german_name_is_still_findable_by_binomial(
    conn: sqlite3.Connection,
) -> None:
    assert search_names(conn, "Nurlatein") == [4]


def test_a_wildcard_in_the_query_is_not_a_wildcard(conn: sqlite3.Connection) -> None:
    """`%` is LIKE syntax, not user intent — an unescaped one would match all."""
    assert search_names(conn, "%") == []
