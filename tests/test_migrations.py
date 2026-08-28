"""Schema evolution on databases that already exist.

CREATE TABLE IF NOT EXISTS does nothing when the table is there, so a new column
never reaches an existing database — including the production volume, where
startup then fails on the first statement that references it.
"""
import sqlite3
from pathlib import Path

from ninanatur.ingest.db import COLUMN_MIGRATIONS, connect, init_schema


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_a_missing_column_is_added_to_an_existing_table(tmp_path: Path) -> None:
    """Regression: adding insect_group broke startup against any older database."""
    db = tmp_path / "old.sqlite"
    old = connect(db, same_thread=False)
    # A table as an earlier release created it — no insect_group.
    old.executescript(
        "CREATE TABLE insect_de (canonical_name TEXT PRIMARY KEY,"
        " scientific_name TEXT, occurrences INTEGER NOT NULL DEFAULT 0);"
    )
    old.execute("INSERT INTO insect_de (canonical_name) VALUES ('Apis mellifera')")
    old.commit()
    assert "insect_group" not in _columns(old, "insect_de")

    applied = init_schema(old)
    assert "insect_de.insect_group" in applied
    assert "insect_group" in _columns(old, "insect_de")


def test_existing_rows_survive_the_migration(tmp_path: Path) -> None:
    """An ALTER that dropped data would be worse than the crash it replaces."""
    db = tmp_path / "old.sqlite"
    old = connect(db, same_thread=False)
    old.executescript(
        "CREATE TABLE insect_de (canonical_name TEXT PRIMARY KEY,"
        " scientific_name TEXT, occurrences INTEGER NOT NULL DEFAULT 0);"
    )
    old.execute("INSERT INTO insect_de (canonical_name, occurrences) VALUES ('Apis mellifera', 42)")
    old.commit()

    init_schema(old)
    row = old.execute(
        "SELECT occurrences, insect_group FROM insect_de WHERE canonical_name='Apis mellifera'"
    ).fetchone()
    assert row["occurrences"] == 42
    assert row["insect_group"] is None


def test_running_twice_applies_nothing_the_second_time(tmp_path: Path) -> None:
    conn = connect(tmp_path / "fresh.sqlite", same_thread=False)
    init_schema(conn)
    assert init_schema(conn) == [], "a second run must be a no-op"


def test_a_fresh_database_needs_no_migration(tmp_path: Path) -> None:
    """The tables are created with their columns; migrations are for older files."""
    conn = connect(tmp_path / "brand-new.sqlite", same_thread=False)
    assert init_schema(conn) == []
    for table, column, _type in COLUMN_MIGRATIONS:
        assert column in _columns(conn, table)
