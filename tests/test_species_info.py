"""Descriptions and photos from Wikipedia — fetched, cached, and credited."""
import sqlite3
from typing import Any

import pytest

from ninanatur.data.species_info import (
    HIT_TTL_DAYS,
    LICENCE,
    MISS_TTL_DAYS,
    SpeciesInfo,
    species_info,
)
from ninanatur.ingest.db import connect, init_schema


class FakeWikipedia:
    """Records calls so caching can be proven, not assumed."""

    def __init__(self, *, de: dict[str, Any] | None = None, en: dict[str, Any] | None = None):
        self.responses = {"de": de, "en": en}
        self.calls: list[tuple[str, str]] = []

    def summary(self, title: str, language: str) -> dict[str, Any] | None:
        self.calls.append((language, title))
        return self.responses.get(language)


GERMAN = {
    "title": "Gemeine Schafgarbe",
    "extract": "Die Gemeine Schafgarbe ist eine Pflanzenart aus der Familie der Korbblütler.",
    "thumbnail": {"source": "https://upload.example/achillea.jpg"},
    "content_urls": {"desktop": {"page": "https://de.wikipedia.org/wiki/Gemeine_Schafgarbe"}},
}
ENGLISH = {
    "title": "Achillea millefolium",
    "extract": "Achillea millefolium, commonly known as yarrow, is a flowering plant.",
    "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Achillea_millefolium"}},
}


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    c.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, occurs_de)"
        " VALUES (1, 'Achillea millefolium', 1)"
    )
    c.commit()
    return c


# --- fetching --------------------------------------------------------------

def test_the_german_article_is_returned_with_its_photo(conn: sqlite3.Connection) -> None:
    info = species_info(conn, 1, client=FakeWikipedia(de=GERMAN))
    assert isinstance(info, SpeciesInfo)
    assert info.title == "Gemeine Schafgarbe"
    assert info.language == "de"
    assert info.thumbnail_url == "https://upload.example/achillea.jpg"


def test_the_scientific_name_is_what_gets_looked_up(conn: sqlite3.Connection) -> None:
    """Wikipedia redirects it to the German article, so no name mapping is needed."""
    client = FakeWikipedia(de=GERMAN)
    species_info(conn, 1, client=client)
    assert client.calls[0] == ("de", "Achillea millefolium")


def test_english_is_used_when_there_is_no_german_article(
    conn: sqlite3.Connection,
) -> None:
    info = species_info(conn, 1, client=FakeWikipedia(de=None, en=ENGLISH))
    assert info is not None
    assert info.language == "en"
    assert info.title == "Achillea millefolium"


def test_no_article_in_either_language_is_none_not_an_error(
    conn: sqlite3.Connection,
) -> None:
    assert species_info(conn, 1, client=FakeWikipedia()) is None


# --- licensing -------------------------------------------------------------

def test_every_result_carries_its_licence_and_a_link_back(
    conn: sqlite3.Connection,
) -> None:
    """CC-BY-SA is a condition of use, not decoration. A cached copy does not
    become ours."""
    info = species_info(conn, 1, client=FakeWikipedia(de=GERMAN))
    assert info.licence == LICENCE
    assert info.page_url.startswith("https://de.wikipedia.org/")


def test_a_cached_result_still_carries_attribution(conn: sqlite3.Connection) -> None:
    species_info(conn, 1, client=FakeWikipedia(de=GERMAN))
    cached = species_info(conn, 1, client=FakeWikipedia())
    assert cached is not None
    assert cached.licence == LICENCE
    assert cached.page_url


# --- caching ---------------------------------------------------------------

def test_a_second_view_does_not_call_wikipedia_again(conn: sqlite3.Connection) -> None:
    species_info(conn, 1, client=FakeWikipedia(de=GERMAN))
    second = FakeWikipedia(de=GERMAN)
    species_info(conn, 1, client=second)
    assert second.calls == [], "served from cache"


def test_a_miss_is_cached_so_a_known_gap_is_not_re_asked(
    conn: sqlite3.Connection,
) -> None:
    """Re-asking on every view would hammer a free service for an absent page."""
    species_info(conn, 1, client=FakeWikipedia())
    second = FakeWikipedia()
    species_info(conn, 1, client=second)
    assert second.calls == []


def test_a_cached_miss_expires_sooner_than_a_hit() -> None:
    """Remembering "no article" forever freezes a gap Wikipedia may close."""
    assert MISS_TTL_DAYS < HIT_TTL_DAYS


def test_a_stale_entry_is_refetched(conn: sqlite3.Connection) -> None:
    species_info(conn, 1, client=FakeWikipedia(de=GERMAN))
    conn.execute("UPDATE species_info SET fetched_at = '2000-01-01T00:00:00+00:00'")
    conn.commit()
    refreshed = FakeWikipedia(de=GERMAN)
    species_info(conn, 1, client=refreshed)
    assert refreshed.calls, "an expired entry must be fetched again"


# --- robustness ------------------------------------------------------------

def test_a_failing_lookup_degrades_instead_of_raising(conn: sqlite3.Connection) -> None:
    """A plant list must not break because an external service is down."""

    class Broken:
        def summary(self, title: str, language: str) -> dict[str, Any] | None:
            raise TimeoutError("wikipedia unreachable")

    assert species_info(conn, 1, client=Broken()) is None


def test_an_unknown_taxon_is_none(conn: sqlite3.Connection) -> None:
    assert species_info(conn, 999, client=FakeWikipedia(de=GERMAN)) is None


def test_a_response_without_an_extract_is_treated_as_a_miss(
    conn: sqlite3.Connection,
) -> None:
    """A stub page with a title and no text is not information."""
    assert species_info(conn, 1, client=FakeWikipedia(de={"title": "Leer"})) is None


def test_a_missing_thumbnail_is_none_not_a_broken_url(
    conn: sqlite3.Connection,
) -> None:
    info = species_info(conn, 1, client=FakeWikipedia(de=ENGLISH | {"title": "Ohne Bild"}))
    assert info is not None
    assert info.thumbnail_url is None
