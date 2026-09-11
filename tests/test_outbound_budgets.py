"""Busy, not broken — Wave 20, feature 5, part 3: what a call to somebody else may cost.

Four findings, each reproduced here against a fake `requests.get` — nothing in
this file reaches the network:

- Every failure was retried, a 404 included: three attempts and 1+2+4 s of
  back-off for an answer that was never going to change.
- So a species without a Wikipedia article cost ~7.6 s on every open, and the
  miss was never remembered — the failure path returned before storing it, and
  English was never asked.
- Overpass answers a query it gave up on with HTTP 200, an empty element list
  and a `remark`. That was cached as "no buildings here", for good.
- The cache lived in the container layer (`/app/data/cache`), emptied by every
  roll and bounded by nothing.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import pytest
import requests

from ninanatur.data.species_info import WikipediaClient, species_info
from ninanatur.geo import osm, osm_streets
from ninanatur.ingest import http
from ninanatur.ingest.db import connect, init_schema


class FakeWeb:
    """Answers `requests.get` from a script, and counts."""

    def __init__(self, *answers: tuple[int, Any]) -> None:
        self.answers = list(answers)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, url: str, **kwargs: Any) -> requests.Response:
        self.calls.append({"url": url, **kwargs})
        status, body = self.answers[min(len(self.calls), len(self.answers)) - 1]
        response = requests.Response()
        response.status_code = status
        response.url = url
        response.reason = "scripted"
        response._content = (body if isinstance(body, bytes)
                             else __import__("json").dumps(body).encode())
        return response


@pytest.fixture(autouse=True)
def quiet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No real sleeping, and a cache of this test's own."""
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setenv(http.CACHE_DIR_ENV, str(tmp_path / "cache"))


def _web(monkeypatch: pytest.MonkeyPatch, *answers: tuple[int, Any]) -> FakeWeb:
    web = FakeWeb(*answers)
    monkeypatch.setattr(requests, "get", web)
    return web


# --- retries --------------------------------------------------------------------

def test_a_404_is_asked_once(monkeypatch: pytest.MonkeyPatch) -> None:
    web = _web(monkeypatch, (404, {"title": "Not found."}))
    with pytest.raises(http.HttpError) as refused:
        http.get_json("https://example.test/page")
    assert len(web.calls) == 1
    assert refused.value.status == 404


def test_a_server_error_is_still_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 503 may well be gone in a second. A 404 will not."""
    web = _web(monkeypatch, (503, {}), (503, {}), (200, {"ok": True}))
    assert http.get_json("https://example.test/flaky") == {"ok": True}
    assert len(web.calls) == 3


def test_every_call_has_a_connect_and_a_read_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    web = _web(monkeypatch, (200, {}))
    http.get_json("https://example.test/x")
    connect_s, read_s = web.calls[0]["timeout"]
    assert connect_s <= 10 and read_s <= 60


# --- Wikipedia --------------------------------------------------------------------

@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (1, 'Rara avis', 1)")
    c.commit()
    return c


def test_no_article_in_german_asks_english(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    english = {"title": "Rara avis", "extract": "A rare bird, and a plant.",
               "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Rara_avis"}}}
    _web(monkeypatch, (404, {}), (200, english))
    info = species_info(conn, 1, client=WikipediaClient())
    assert info is not None and info.language == "en"


def test_a_species_without_an_article_is_remembered_as_one(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The finding: seconds on every open, never remembered."""
    web = _web(monkeypatch, (404, {}))
    assert species_info(conn, 1, client=WikipediaClient()) is None
    asked = len(web.calls)
    assert asked == 2, "one question per language, no retries"
    assert species_info(conn, 1, client=WikipediaClient()) is None
    assert len(web.calls) == asked, "the second open asked Wikipedia again"


def test_an_outage_is_not_remembered_as_a_missing_article(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wikipedia being down says nothing about whether the page exists."""
    web = _web(monkeypatch, (503, {}))
    assert species_info(conn, 1, client=WikipediaClient()) is None
    before = len(web.calls)
    species_info(conn, 1, client=WikipediaClient())
    assert len(web.calls) > before


def test_wikipedia_is_given_a_page_loads_worth_of_patience(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    web = _web(monkeypatch, (404, {}))
    species_info(conn, 1, client=WikipediaClient())
    assert all(call["timeout"][1] <= 10 for call in web.calls)


# --- Overpass -----------------------------------------------------------------------

GAVE_UP = {"elements": [], "remark": 'runtime error: Query timed out in "query" '
                                     "at line 1 after 41 seconds."}


def test_an_overpass_timeout_is_a_failure_not_an_empty_street(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _web(monkeypatch, (200, GAVE_UP))
    with pytest.raises(http.HttpError):
        osm.buildings_in(51.0, 7.0, 51.001, 7.001)


def test_an_overpass_timeout_is_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cached, the gap would be permanent: the next import of the same street
    would read "no buildings" from disk without asking."""
    web = _web(monkeypatch, (200, GAVE_UP), (200, {"elements": []}))
    with pytest.raises(http.HttpError):
        osm.buildings_in(51.0, 7.0, 51.001, 7.001)
    assert osm.buildings_in(51.0, 7.0, 51.001, 7.001) == []
    assert len(web.calls) == 2


def test_a_timeout_reported_to_a_caller_of_its_own_is_refused_too() -> None:
    """Whatever fetched it: the answer itself says it is incomplete."""
    with pytest.raises(http.HttpError):
        osm_streets.streets_in(51.0, 7.0, 51.001, 7.001, fetch=lambda _u, _p=None: GAVE_UP)


# --- where the cache lives, and how big it may get ---------------------------------

def test_the_cache_lives_where_it_is_told(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """In the container that is the volume, so a roll no longer empties it."""
    _web(monkeypatch, (200, {"kept": True}))
    http.get_json("https://example.test/kept")
    assert list((tmp_path / "cache").glob("*.json"))


def test_the_cache_forgets_its_oldest_past_its_cap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    for n in range(5):
        old = cache / f"old{n}.bin"
        old.write_bytes(b"x" * 400_000)
        os.utime(old, (1_000_000 + n, 1_000_000 + n))
    monkeypatch.setenv(http.CACHE_MAX_MB_ENV, "1")
    _web(monkeypatch, (200, b"y" * 100_000))
    http.get_bytes("https://example.test/new")
    left = sorted(p.name for p in cache.iterdir())
    total = sum(p.stat().st_size for p in cache.iterdir())
    assert total <= 1_000_000
    assert "old0.bin" not in left, "the oldest goes first"
    assert any(not name.startswith("old") for name in left), "the new file stays"
