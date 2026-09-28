"""A running database upgrades itself to what a new one is made with.

CLAUDE.md: a new column goes into `COLUMN_MIGRATIONS` *and* into the
`CREATE TABLE`. Only the second is exercised by every other test, which all
start from a fresh database — so leaving out the first passed the suite while
every existing volume would have raised `no such column` on its first garden
(review of doc 121, 2026-09-28). This starts from the schema a real volume has.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema

#: The schema a fresh database had at a8faf57, the last commit before doc 121.
BEFORE = Path(__file__).parent / "fixtures" / "schema_a8faf57.sql"


def _columns(conn: sqlite3.Connection) -> dict[str, set[str]]:
    tables = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
    return {table: {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            for table in tables}


def test_a_database_from_before_the_crowns_upgrades_to_every_column(tmp_path: Path) -> None:
    old = connect(tmp_path / "volume.sqlite")
    old.executescript(BEFORE.read_text(encoding="utf-8"))
    applied = init_schema(old)
    fresh = connect(":memory:")
    init_schema(fresh)

    assert _columns(old) == _columns(fresh), applied
    # And the column that was missing is read without complaint.
    garden_id = create_garden(old, name="G", latitude=51.2562, longitude=7.1508)
    assert load_garden(old, garden_id).garden_id == garden_id


def test_the_fixture_is_the_schema_before_the_crowns() -> None:
    """A fixture that already held the new columns would test nothing."""
    before = BEFORE.read_text(encoding="utf-8")
    assert "CREATE TABLE element" in before and "CREATE TABLE cloud_window" in before
    for column in ("crown_base_m", "crown_base_source", "anchor_lat", "classified"):
        assert column not in before, column
