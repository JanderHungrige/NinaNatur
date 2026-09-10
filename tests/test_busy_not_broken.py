"""Busy, not broken — Wave 20, feature 5, part 1: the database under load.

Under SQLite's default rollback journal a writer that is committing locks the
whole file, and every reader waiting behind it for longer than the busy timeout
gets "database is locked" — a 500 that no single-threaded test ever sees. WAL
lets readers read the last committed state while a writer writes.

These tests reproduce the lock rather than assert a PRAGMA: a writer holds the
exclusive lock, and a reader must still be answered.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ninanatur.ingest.db import BUSY_TIMEOUT_MS, DB_PATH_ENV, connect, init_schema
from ninanatur.ops import backup
from ninanatur.web.app import app

NOW = datetime(2026, 9, 10, 3, 17, tzinfo=UTC)


def _garden(conn: sqlite3.Connection, token: str) -> None:
    conn.execute(
        "INSERT INTO garden (share_token, name, latitude, longitude, created_at, updated_at)"
        " VALUES (?, 'G', 51.0, 7.0, '2026-09-10', '2026-09-10')", (token,))


@pytest.fixture
def started(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A database as the running app leaves it: created by its own startup."""
    db = tmp_path / "ninanatur.sqlite"
    monkeypatch.setenv(DB_PATH_ENV, str(db))
    with TestClient(app):
        pass
    return db


def test_startup_puts_the_database_in_wal(started: Path) -> None:
    conn = sqlite3.connect(started)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        conn.close()


def test_every_connection_waits_for_a_lock_rather_than_failing(started: Path) -> None:
    conn = connect(started)
    try:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == BUSY_TIMEOUT_MS
        # NORMAL is safe under WAL (a power cut can lose the last commit, never
        # corrupt) and saves an fsync on every write.
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1
    finally:
        conn.close()


def test_a_reader_is_answered_while_a_writer_holds_the_lock(started: Path) -> None:
    """The failure itself. Under the rollback journal this raises
    'database is locked' after the timeout; under WAL it reads at once."""
    writer = connect(started)
    reader = connect(started)
    try:
        writer.execute("BEGIN EXCLUSIVE")
        _garden(writer, "in-flight")
        reader.execute("PRAGMA busy_timeout = 100")  # fail fast if it would block
        count = reader.execute("SELECT count(*) FROM garden").fetchone()[0]
        assert count == 0, "the reader sees the last committed state, not the write in flight"
    finally:
        writer.rollback()
        writer.close()
        reader.close()


def test_a_backup_holds_what_is_committed_but_not_yet_checkpointed(
    started: Path, tmp_path: Path,
) -> None:
    """Under WAL a commit lands in the -wal file first. A copy of the .sqlite
    file alone would miss it; the online backup must not."""
    conn = connect(started)
    try:
        conn.execute("PRAGMA wal_autocheckpoint = 0")
        _garden(conn, "committed")
        conn.commit()
        assert Path(f"{started}-wal").stat().st_size > 0
        made = backup.create(started, tmp_path / "backups", now=NOW)
    finally:
        conn.close()
    assert backup.verify(made)["garden"] == 1


def test_the_catalogue_connection_is_not_switched(tmp_path: Path) -> None:
    """WAL is set by the app's startup, on its own database — `connect` itself
    changes no file's journal, so the catalogue in the image, and any file the
    ingest CLI opens, stay as they are."""
    db = tmp_path / "other.sqlite"
    conn = connect(db)
    try:
        init_schema(conn)
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    finally:
        conn.close()
