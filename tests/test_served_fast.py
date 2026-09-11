"""What the site sends, and how long a browser may keep it — Wave 20, feature 10.

Measured on the preview on 2026-09-11, before this: a 200-row `/plants` answer
was 115,353 bytes whether or not the browser asked for gzip, the 271,272-byte
bundle likewise, and nothing carried `Cache-Control`. The bundle's name is a
hash of its content, so a browser could keep it for a year — instead it asked
again. The page itself was left to heuristic caching, which can hold an
`index.html` naming a bundle the next deployment no longer ships: a white page
until somebody reloads.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.web.app import app
from ninanatur.web.delivery import IMMUTABLE, REVALIDATE, compress, serve_bundle

GZIP = {"accept-encoding": "gzip"}
PLAIN = {"accept-encoding": "identity"}
SEARCH = "/api/v1/plants?light=7&limit=120"
BUNDLE = "/assets/index-Ab12Cd34.js"
FILM = "/assets/meadow-Ef56Gh78.mp4"


@pytest.fixture()
def many_plants() -> Iterator[sqlite3.Connection]:
    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    for taxon_id in range(1, 121):
        conn.execute(
            "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
            (taxon_id, f"Planta exemplaris {taxon_id}"),
        )
        upsert_trait(conn, taxon_id, "ellenberg_l", source="EIVE", license="CC-BY-4.0",
                     value_num=7.0)
    conn.commit()
    app.dependency_overrides[get_connection] = lambda: conn
    yield conn
    app.dependency_overrides.clear()


@pytest.fixture()
def bundle(tmp_path: Path) -> TestClient:
    """A built front end as Vite leaves it: a page, and hashed assets beside it."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        f'<!doctype html><script type="module" src="{BUNDLE}"></script>' + " " * 2000
    )
    (tmp_path / BUNDLE.lstrip("/")).write_text("console.log('eine Wiese');\n" * 400)
    (tmp_path / FILM.lstrip("/")).write_bytes(bytes(range(256)) * 40)
    site = FastAPI()
    compress(site)
    assert serve_bundle(site, tmp_path)
    return TestClient(site)


# --- compression -------------------------------------------------------------------------

def test_a_large_answer_is_compressed_for_a_browser_that_asks(
    many_plants: sqlite3.Connection,
) -> None:
    client = TestClient(app)
    plain = client.get(SEARCH, headers=PLAIN)
    packed = client.get(SEARCH, headers=GZIP)

    assert plain.status_code == packed.status_code == 200
    assert packed.headers.get("content-encoding") == "gzip"
    assert "accept-encoding" in packed.headers.get("vary", "").lower()
    assert packed.num_bytes_downloaded * 3 < len(plain.content)
    assert packed.json() == plain.json()


def test_a_browser_that_does_not_ask_gets_it_plain(many_plants: sqlite3.Connection) -> None:
    assert "content-encoding" not in TestClient(app).get(SEARCH, headers=PLAIN).headers


def test_a_small_answer_is_left_alone() -> None:
    """Below a kilobyte the header costs more than the compression saves."""
    assert "content-encoding" not in TestClient(app).get("/healthz", headers=GZIP).headers


def test_the_bundle_is_compressed_like_any_answer(bundle: TestClient) -> None:
    assert bundle.get(BUNDLE, headers=GZIP).headers.get("content-encoding") == "gzip"


def test_the_film_is_never_compressed_and_still_seeks(bundle: TestClient) -> None:
    """Already compressed, and played through range requests: gzip on top would
    cost CPU for nothing and break the byte offsets a browser asks for."""
    whole = bundle.get(FILM, headers=GZIP)
    part = bundle.get(FILM, headers={**GZIP, "range": "bytes=100-199"})

    assert "content-encoding" not in whole.headers
    assert part.status_code == 206
    assert part.content == whole.content[100:200]


# --- how long it may be kept -------------------------------------------------------------

def test_a_hashed_asset_may_be_kept_for_a_year(bundle: TestClient) -> None:
    """Its name changes when its content does, so there is nothing to ask again."""
    for path in (BUNDLE, FILM):
        answer = bundle.get(path)
        assert answer.status_code == 200
        assert answer.headers["cache-control"] == IMMUTABLE


def test_the_page_itself_is_asked_for_again_every_time(bundle: TestClient) -> None:
    """The one file that names all the others."""
    for path in ("/", "/index.html"):
        answer = bundle.get(path)
        assert answer.status_code == 200
        assert answer.headers["cache-control"] == REVALIDATE


def test_asking_again_costs_nothing_when_nothing_changed(bundle: TestClient) -> None:
    etag = bundle.get("/").headers["etag"]
    again = bundle.get("/", headers={"if-none-match": etag})

    assert again.status_code == 304
    assert again.headers["cache-control"] == REVALIDATE


def test_a_missing_asset_is_not_remembered_as_missing(bundle: TestClient) -> None:
    """A deployment race — the new page, an asset asked of the old image — must
    not leave a 404 in somebody's cache for a year."""
    answer = bundle.get("/assets/index-Zz99Yy88.js")

    assert answer.status_code == 404
    assert answer.headers.get("cache-control") != IMMUTABLE


def test_without_a_build_nothing_is_mounted(tmp_path: Path) -> None:
    """Vite serves the front end in development; a missing bundle is normal."""
    assert serve_bundle(FastAPI(), tmp_path / "not-built") is False
