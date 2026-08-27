"""Name resolution decides whether a source's rows attach to anything at all."""
import sqlite3

import pytest

from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.names import MIN_MATCH_CONFIDENCE, NameResolver

GOOD_MATCH: dict[str, object] = {
    "usageKey": 3120060,
    "canonicalName": "Achillea millefolium",
    "scientificName": "Achillea millefolium L.",
    "matchType": "EXACT",
    "confidence": 98,
    "rank": "SPECIES",
    "status": "ACCEPTED",
    "family": "Asteraceae",
    "genus": "Achillea",
}


class FakeGbif:
    """Records calls so the cache can be proven to prevent repeat lookups."""

    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[str] = []

    def match(self, name: str) -> dict[str, object]:
        self.calls.append(name)
        return self.response


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:")
    init_schema(c)
    return c


def test_resolver_returns_taxon_id_for_a_confident_match(conn: sqlite3.Connection) -> None:
    resolver = NameResolver(conn, FakeGbif(GOOD_MATCH))
    assert resolver.resolve("Achillea millefolium", source="EIVE") == 3120060


def test_resolver_writes_the_taxon_row_it_matched(conn: sqlite3.Connection) -> None:
    resolver = NameResolver(conn, FakeGbif(GOOD_MATCH))
    resolver.resolve("Achillea millefolium", source="EIVE")
    row = conn.execute("SELECT canonical_name, family FROM taxon WHERE taxon_id=3120060").fetchone()
    assert row is not None
    assert row["canonical_name"] == "Achillea millefolium"
    assert row["family"] == "Asteraceae"


def test_resolver_caches_and_does_not_call_api_twice(conn: sqlite3.Connection) -> None:
    api = FakeGbif(GOOD_MATCH)
    resolver = NameResolver(conn, api)
    resolver.resolve("Achillea millefolium", source="EIVE")
    resolver.resolve("Achillea millefolium", source="EIVE")
    assert len(api.calls) == 1, "second lookup must be served from the taxon_name cache"


def test_resolver_rejects_low_confidence_match(conn: sqlite3.Connection) -> None:
    api = FakeGbif({"usageKey": 1, "canonicalName": "Something", "matchType": "FUZZY",
                    "confidence": MIN_MATCH_CONFIDENCE - 1, "rank": "SPECIES"})
    resolver = NameResolver(conn, api)
    assert resolver.resolve("Zzz qqq", source="EIVE") is None


def test_resolver_rejects_higherrank_match(conn: sqlite3.Connection) -> None:
    """A family-level match must not silently absorb species-level traits."""
    api = FakeGbif({"usageKey": 3065, "canonicalName": "Asteraceae", "matchType": "HIGHERRANK",
                    "confidence": 99, "rank": "FAMILY"})
    resolver = NameResolver(conn, api)
    assert resolver.resolve("Asteraceae sp.", source="EIVE") is None


def test_unresolved_names_are_recorded_for_the_coverage_report(conn: sqlite3.Connection) -> None:
    resolver = NameResolver(conn, FakeGbif({"matchType": "NONE", "confidence": 0}))
    resolver.resolve("Nonexistent plantus", source="EIVE")
    row = conn.execute(
        "SELECT taxon_id, match_type FROM taxon_name WHERE raw_name=?", ("Nonexistent plantus",)
    ).fetchone()
    assert row is not None
    assert row["taxon_id"] is None
    assert row["match_type"] == "NONE"


def test_resolver_matches_local_canonical_name_without_api(conn: sqlite3.Connection) -> None:
    """A name already in `taxon` must resolve from the table, not over the network."""
    conn.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, occurs_de)"
        " VALUES (555, 'Salvia pratensis', 1)"
    )
    api = FakeGbif(GOOD_MATCH)
    resolver = NameResolver(conn, api)
    assert resolver.resolve("Salvia pratensis", source="EIVE") == 555
    assert api.calls == [], "local match must not trigger an API call"


def test_only_known_skips_the_network_for_unknown_names(conn: sqlite3.Connection) -> None:
    api = FakeGbif(GOOD_MATCH)
    resolver = NameResolver(conn, api)
    assert resolver.resolve("Achillea millefolium", source="EIVE", only_known=True) is None
    assert api.calls == [], "only_known must never reach the API"


def test_backbone_allows_homonyms_sharing_a_canonical_name(conn: sqlite3.Connection) -> None:
    """Regression: a UNIQUE canonical_name aborted the GBIF ingest partway through.

    198 of the 8939 German candidate keys share a canonical name with another
    key, almost all as an ACCEPTED/DOUBTFUL pair — e.g. Huperzia selago carries
    both 8190643 (accepted) and 2688495 (doubtful).
    """
    conn.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, status, family)"
        " VALUES (8190643, 'Huperzia selago', 'ACCEPTED', 'Lycopodiaceae')"
    )
    conn.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, status, family)"
        " VALUES (2688495, 'Huperzia selago', 'DOUBTFUL', 'Lycopodiaceae')"
    )
    assert conn.execute("SELECT COUNT(*) AS n FROM taxon").fetchone()["n"] == 2


def test_resolver_prefers_the_accepted_taxon_among_homonyms(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, status)"
        " VALUES (11, 'Rosa canina', 'DOUBTFUL')"
    )
    conn.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, status)"
        " VALUES (12, 'Rosa canina', 'ACCEPTED')"
    )
    api = FakeGbif(GOOD_MATCH)
    assert NameResolver(conn, api).resolve("Rosa canina", source="EIVE") == 12
    assert api.calls == []


def test_resolver_refuses_to_guess_between_two_accepted_homonyms(
    conn: sqlite3.Connection,
) -> None:
    for taxon_id in (21, 22):
        conn.execute(
            "INSERT INTO taxon (taxon_id, canonical_name, status)"
            " VALUES (?, 'Aster sp', 'ACCEPTED')",
            (taxon_id,),
        )
    resolver = NameResolver(conn, FakeGbif(GOOD_MATCH))
    assert resolver.resolve("Aster sp", source="EIVE") is None
    row = conn.execute(
        "SELECT match_type FROM taxon_name WHERE raw_name = 'Aster sp'"
    ).fetchone()
    assert row["match_type"] == "AMBIGUOUS", "ambiguity must stay visible, not vanish"
