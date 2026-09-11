"""The candidate set, held between requests — Wave 20, feature 10.

Measured on 2026-09-07 against a copy of the live database: `load_candidates`
took 238–544 ms of every search, every suggestion list and every improvement,
rebuilding the same 8,939 rows each time. On the preview on 2026-09-11 a 200-row
`/plants` took 1.09–1.97 s.

The set changes in exactly two ways, and both must reach the next request: a new
catalogue build, which startup syncs and stamps, and a colour somebody entered by
hand, which is a trait row in the shared catalogue written while the app runs. A
garden's own observed colours are laid over the set per request and must never
enter it.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import candidate_cache
from ninanatur.api.candidate_cache import candidate_set
from ninanatur.api.candidates import OBSERVED_COLOUR, PlantRow, load_candidates, with_observed
from ninanatur.api.deps import get_connection
from ninanatur.data.traits import MANUAL_SOURCE
from ninanatur.garden.observations import record_colour
from ninanatur.ingest.catalogue import VERSION_KEY, edition, mark_edited
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.web.app import app

#: The one query that reads the whole catalogue. Counting it is counting the cost.
THE_READ = "LEFT JOIN trait"
BUILT = "2026-09-01T00:00:00+00:00"


def _catalogue(path: Path | str, names: dict[int, str]) -> sqlite3.Connection:
    conn = connect(path, same_thread=False)
    init_schema(conn)
    for taxon_id, name in names.items():
        conn.execute(
            "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
            (taxon_id, name),
        )
        upsert_trait(conn, taxon_id, "ellenberg_l", source="EIVE", license="CC-BY-4.0",
                     value_num=7.0)
    conn.execute("INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
                 (VERSION_KEY, BUILT))
    conn.commit()
    return conn


def _reads(conn: sqlite3.Connection) -> list[str]:
    seen: list[str] = []
    conn.set_trace_callback(lambda sql: seen.append(sql) if THE_READ in sql else None)
    return seen


def _names(rows: list[PlantRow]) -> set[str]:
    return {p.canonical_name for p in rows}


def _colour_of(conn: sqlite3.Connection, taxon_id: int) -> str | None:
    return next(p for p in candidate_set(conn) if p.taxon_id == taxon_id).colour()


@pytest.fixture()
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    conn = _catalogue(tmp_path / "n.sqlite", {1: "Salvia pratensis", 2: "Achillea millefolium"})
    yield conn
    conn.close()


# --- read once ---------------------------------------------------------------------------

def test_the_catalogue_is_read_once_not_on_every_request(db: sqlite3.Connection) -> None:
    reads = _reads(db)
    first = candidate_set(db)
    second = candidate_set(db)

    assert len(reads) == 1
    fresh = load_candidates(db)
    assert [(p.taxon_id, p.extras) for p in second] == [(p.taxon_id, p.extras) for p in fresh]
    assert [p.taxon_id for p in first] == [p.taxon_id for p in second]


def test_two_cold_requests_at_once_read_the_catalogue_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The host has two cores. Two requests arriving on a cold set wait for one
    read rather than making two."""
    path = tmp_path / "n.sqlite"
    _catalogue(path, {1: "Salvia pratensis"}).close()
    reads: list[int] = []
    real = candidate_cache.load_candidates

    def slow(conn: sqlite3.Connection) -> list[PlantRow]:
        reads.append(1)
        time.sleep(0.2)
        return real(conn)

    monkeypatch.setattr(candidate_cache, "load_candidates", slow)
    barrier = threading.Barrier(2)
    answers: list[set[str]] = []

    def request() -> None:
        conn = connect(path, same_thread=False)
        barrier.wait()
        answers.append(_names(candidate_set(conn)))
        conn.close()

    threads = [threading.Thread(target=request) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(reads) == 1
    assert answers == [{"Salvia pratensis"}, {"Salvia pratensis"}]


# --- what changes it ---------------------------------------------------------------------

def test_a_new_catalogue_build_reaches_the_next_request(db: sqlite3.Connection) -> None:
    candidate_set(db)
    db.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de)"
               " VALUES (3, 'Knautia arvensis', 1)")
    db.execute("UPDATE catalogue_meta SET value = ? WHERE key = ?",
               ("2026-09-12T00:00:00+00:00", VERSION_KEY))
    db.commit()

    assert "Knautia arvensis" in _names(candidate_set(db))


def test_a_colour_entered_by_hand_reaches_the_next_request(db: sqlite3.Connection) -> None:
    """The one edit of the catalogue that comes without a new build stamp."""
    assert _colour_of(db, 1) is None
    record_colour(db, taxon_id=1, colour="violet")

    assert _colour_of(db, 1) == "violet"


def test_taking_a_hand_colour_back_reaches_the_next_request(db: sqlite3.Connection) -> None:
    record_colour(db, taxon_id=1, colour="violet")
    assert _colour_of(db, 1) == "violet"
    record_colour(db, taxon_id=1, colour=None)

    assert _colour_of(db, 1) is None


def test_every_hand_edit_moves_the_edition(db: sqlite3.Connection) -> None:
    before = edition(db)
    record_colour(db, taxon_id=1, colour="violet")
    once = edition(db)
    record_colour(db, taxon_id=1, colour=None)

    assert len({before, once, edition(db)}) == 3


def test_the_edit_mark_is_in_the_database_not_in_this_process(tmp_path: Path) -> None:
    """Each request has its own connection, and a later deployment may run more
    than one process. An edit made anywhere else — here, another connection that
    never calls into this process's cache — must still reach this one."""
    path = tmp_path / "n.sqlite"
    reader = _catalogue(path, {1: "Salvia pratensis"})
    assert _colour_of(reader, 1) is None

    elsewhere = connect(path)
    upsert_trait(elsewhere, 1, "flower_colour", source=MANUAL_SOURCE, license="none",
                 value_text="violet")
    mark_edited(elsewhere)
    elsewhere.commit()
    elsewhere.close()

    assert _colour_of(reader, 1) == "violet"


# --- what must never enter it ------------------------------------------------------------

def test_one_garden_s_colour_never_enters_the_shared_set(db: sqlite3.Connection) -> None:
    """Written into the held set, one gardener's observation would show up in a
    stranger's plan."""
    mine = with_observed(candidate_set(db), {1: "rot"})

    assert next(p for p in mine if p.taxon_id == 1).extras[OBSERVED_COLOUR] == "rot"
    assert all(OBSERVED_COLOUR not in p.extras for p in candidate_set(db))


def test_what_a_caller_does_to_its_list_stays_in_its_list(db: sqlite3.Connection) -> None:
    rows = candidate_set(db)
    rows.clear()

    assert len(candidate_set(db)) == 2


def test_an_in_memory_database_is_never_held() -> None:
    """Every `:memory:` connection is a database of its own, so there is nothing
    to key a shared set on — and the test suite opens hundreds of them."""
    first = _catalogue(":memory:", {1: "Salvia pratensis"})
    second = _catalogue(":memory:", {2: "Achillea millefolium"})

    assert _names(candidate_set(first)) == {"Salvia pratensis"}
    assert _names(candidate_set(second)) == {"Achillea millefolium"}


def test_two_databases_with_the_same_build_do_not_share_a_set(tmp_path: Path) -> None:
    one = _catalogue(tmp_path / "a.sqlite", {1: "Salvia pratensis"})
    other = _catalogue(tmp_path / "b.sqlite", {2: "Achillea millefolium"})

    assert _names(candidate_set(one)) == {"Salvia pratensis"}
    assert _names(candidate_set(other)) == {"Achillea millefolium"}
    assert _names(candidate_set(one)) == {"Salvia pratensis"}


# --- every caller ------------------------------------------------------------------------

def test_search_suggestions_and_improvements_share_one_read(db: sqlite3.Connection) -> None:
    """All three callers go through the held set. Any one still reading the
    catalogue for itself would put the cost back on every open garden."""
    app.dependency_overrides[get_connection] = lambda: db
    try:
        client = TestClient(app)
        token = client.post("/api/v1/gardens", json={
            "name": "G", "latitude": 51.0, "longitude": 7.0}).json()["share_token"]
        garden = client.post(f"/api/v1/gardens/{token}/beds", json={
            "name": "Beet", "polygon": [[0, 0], [3, 0], [3, 2], [0, 2]],
            "soil_type": "loam", "moisture": "fresh"}).json()
        bed = garden["beds"][-1]["bed_id"]
        reads = _reads(db)
        for _ in range(2):
            assert client.get("/api/v1/plants?light=7").status_code == 200
            assert client.get(f"/api/v1/gardens/{token}/beds/{bed}/suggestions").status_code == 200
            assert client.get(f"/api/v1/gardens/{token}/improvements").status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert len(reads) <= 1
