"""Wave 20, feature 4: a copy of everything.

On 2026-09-10 there was no backup of the volume holding every garden, account
and feedback report — 27 gardens and 3 accounts in production, all of them one
`docker volume rm` from gone. A backup is only a backup once somebody has put
it back, so most of these tests restore something and read it.
"""
from __future__ import annotations

import gzip
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import DB_PATH_ENV, connect, init_schema
from ninanatur.ops import backup
from ninanatur.web.app import app

T0 = datetime(2026, 9, 10, 3, 17, tzinfo=UTC)


def _database(path: Path, gardens: int = 3) -> list[str]:
    """A real database with gardens in it; returns their share tokens."""
    conn = connect(path)
    init_schema(conn)
    ids = [create_garden(conn, name=f"Garten {i}", latitude=51.2564, longitude=7.1501)
           for i in range(gardens)]
    tokens = [load_garden(conn, gid).share_token for gid in ids]
    conn.close()
    return tokens


def _kept(dest: Path) -> list[Path]:
    return sorted(dest.glob("*.sqlite.gz"))


# --- it holds what it should ----------------------------------------------------

def test_a_backup_holds_every_garden(tmp_path: Path) -> None:
    db = tmp_path / "ninanatur.sqlite"
    _database(db, gardens=3)

    made = backup.create(db, tmp_path / "backups", now=T0)

    assert made.name.endswith(".sqlite.gz") and made.exists()
    assert backup.verify(made)["garden"] == 3


def test_it_is_taken_while_the_app_is_writing(tmp_path: Path) -> None:
    """The online backup API copies a consistent state without stopping the
    app: an uncommitted write in flight is simply not in the copy."""
    db = tmp_path / "ninanatur.sqlite"
    _database(db, gardens=2)
    writer = sqlite3.connect(db, isolation_level=None)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("INSERT INTO garden (share_token, name, latitude, longitude, created_at,"
                   " updated_at) VALUES ('t', 'halb', 0, 0, '', '')")
    try:
        made = backup.create(db, tmp_path / "backups", now=T0)
    finally:
        writer.execute("ROLLBACK")
        writer.close()
    assert backup.verify(made)["garden"] == 2


def test_a_broken_copy_is_never_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A backup that fails its integrity check must not sit under a name that
    looks like a good one — that is the backup somebody restores at 3 a.m."""
    db = tmp_path / "ninanatur.sqlite"
    _database(db)
    monkeypatch.setattr(backup, "_integrity", lambda _path: "*** row 3 missing from index")

    with pytest.raises(backup.BackupBroken):
        backup.create(db, tmp_path / "backups", now=T0)
    assert list((tmp_path / "backups").glob("*")) == []


def test_something_that_is_not_a_backup_is_refused(tmp_path: Path) -> None:
    fake = tmp_path / "ninanatur-nightly-20260910T031700Z.sqlite.gz"
    fake.write_bytes(gzip.compress(b"not a database at all"))
    with pytest.raises(backup.BackupBroken):
        backup.verify(fake)


# --- rotation -----------------------------------------------------------------------

def test_rotation_keeps_the_newest_and_only_the_newest(tmp_path: Path) -> None:
    db = tmp_path / "ninanatur.sqlite"
    _database(db, gardens=1)
    dest = tmp_path / "backups"
    made = [backup.create(db, dest, now=T0 + timedelta(days=d), keep=14) for d in range(20)]

    kept = _kept(dest)
    assert len(kept) == 14
    assert made[-1] in kept, "the one just made is never rotated away"
    assert made[0] not in kept


def test_nightly_rotation_leaves_pre_migration_copies_alone(tmp_path: Path) -> None:
    db = tmp_path / "ninanatur.sqlite"
    _database(db, gardens=1)
    dest = tmp_path / "backups"
    before = backup.snapshot_before_migration(db, dest, now=T0)
    for d in range(1, 20):
        backup.create(db, dest, now=T0 + timedelta(days=d), keep=3)
    assert before is not None and before.exists()


# --- putting it back ------------------------------------------------------------------

def test_a_restore_brings_every_garden_back(tmp_path: Path) -> None:
    db = tmp_path / "ninanatur.sqlite"
    tokens = _database(db, gardens=3)
    made = backup.create(db, tmp_path / "backups", now=T0)
    db.unlink()  # the volume is gone

    restored = tmp_path / "restored" / "ninanatur.sqlite"
    backup.restore(made, restored)

    conn = connect(restored)
    init_schema(conn)
    names = sorted(r[0] for r in conn.execute(
        "SELECT name FROM garden WHERE share_token IN (?, ?, ?)", tokens))
    assert names == ["Garten 0", "Garten 1", "Garten 2"]


def test_a_restore_will_not_overwrite_a_live_database_by_accident(tmp_path: Path) -> None:
    db = tmp_path / "ninanatur.sqlite"
    _database(db, gardens=2)
    made = backup.create(db, tmp_path / "backups", now=T0)
    _database(db, gardens=1)  # something newer has happened since

    with pytest.raises(FileExistsError):
        backup.restore(made, db)
    backup.restore(made, db, replace=True)
    assert backup.verify(made)["garden"] == 2


# --- before a migration ----------------------------------------------------------------

def test_startup_takes_a_copy_before_it_migrates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A migration that fails halfway has to leave something to go back to."""
    db = tmp_path / "ninanatur.sqlite"
    _database(db, gardens=2)
    monkeypatch.setenv(DB_PATH_ENV, str(db))

    with TestClient(app):
        pass

    copies = sorted((tmp_path / "backups").glob("*pre-migration*.sqlite.gz"))
    assert len(copies) == 1
    assert backup.verify(copies[0])["garden"] == 2


def test_a_fresh_volume_has_nothing_to_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(DB_PATH_ENV, str(tmp_path / "brand-new.sqlite"))
    with TestClient(app):
        pass
    assert list(tmp_path.glob("backups/*")) == []


def test_pre_migration_copies_rotate_too(tmp_path: Path) -> None:
    db = tmp_path / "ninanatur.sqlite"
    _database(db, gardens=1)
    dest = tmp_path / "backups"
    for d in range(9):
        backup.snapshot_before_migration(db, dest, now=T0 + timedelta(hours=d))
    assert len(list(dest.glob("*pre-migration*"))) == backup.KEEP_PRE_MIGRATION


# --- the command the host's cron runs ----------------------------------------------------

def test_the_command_prints_the_new_file_last(tmp_path: Path) -> None:
    """deploy/backup.sh reads the last line to know what to copy off the volume."""
    db = tmp_path / "ninanatur.sqlite"
    _database(db, gardens=1)
    out = subprocess.run(
        [sys.executable, "-m", "ninanatur.ops.backup", "create", "--dest", str(tmp_path / "b")],
        env={"NINANATUR_DB": str(db), "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, check=True,
    )
    last = out.stdout.strip().splitlines()[-1]
    assert last.endswith(".sqlite.gz") and Path(last).exists()
