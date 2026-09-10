"""A copy of everything — Wave 20, feature 4.

Until 2026-09-10 there was no backup of the database that holds every garden,
account and feedback report: 27 gardens and 3 accounts in production, one
`docker volume rm` from gone.

The copy is taken with SQLite's online backup API, so it is consistent while
the app is serving — an uncommitted write in flight is simply not in it — and it
is checked with `PRAGMA integrity_check` before it is kept. A copy that fails is
never left under a name that looks like a good one: it is built in a scratch
directory and renamed into place only once it has passed.

A backup is only a backup once somebody has put it back, so `restore` exists
beside `create`, and the tests restore something and read it.

Run as `python -m ninanatur.ops.backup create|verify|restore` — see
`deploy/backup.sh` for the nightly job and `deploy/SERVER-SETUP.md` for the drill.
"""
from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ninanatur.ingest.db import database_path

SUFFIX = ".sqlite.gz"
#: Two weeks of nights. The host keeps a longer tail of its own.
KEEP_NIGHTLY = 14
#: One per container start, which is one per release — a handful is plenty.
KEEP_PRE_MIGRATION = 5
#: What a restore reports, so a person can see it is the database they meant.
COUNTED = ("garden", "account", "feedback")


class BackupBroken(Exception):
    """A copy that failed its integrity check, or is not a database at all."""


def _stamp(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")


def _integrity(path: Path) -> str:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        conn.close()


def _online_copy(db: Path, target: Path) -> None:
    source = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    copy = sqlite3.connect(target)
    try:
        source.backup(copy)
    finally:
        copy.close()
        source.close()


def _rotate(dest: Path, label: str, keep: int) -> None:
    """Newest `keep` of this label stay. Names sort by time, so sort is enough."""
    for old in sorted(dest.glob(f"ninanatur-{label}-*{SUFFIX}"))[:-keep]:
        old.unlink()


def create(
    db: Path,
    dest: Path,
    *,
    label: str = "nightly",
    keep: int = KEEP_NIGHTLY,
    now: datetime | None = None,
) -> Path:
    """Copy `db` into `dest` as a checked, compressed file; return its path."""
    if not db.exists():
        raise FileNotFoundError(f"no database to back up at {db}")
    dest.mkdir(parents=True, exist_ok=True)
    final = dest / f"ninanatur-{label}-{_stamp(now)}{SUFFIX}"
    # Built beside its destination so the final rename cannot cross a device.
    with tempfile.TemporaryDirectory(dir=dest, prefix=".building-") as work:
        raw = Path(work) / "copy.sqlite"
        _online_copy(db, raw)
        result = _integrity(raw)
        if result != "ok":
            raise BackupBroken(f"the copy of {db.name} failed integrity_check: {result}")
        packed = Path(work) / final.name
        with raw.open("rb") as source, gzip.open(packed, "wb", compresslevel=6) as out:
            shutil.copyfileobj(source, out)
        os.replace(packed, final)
    _rotate(dest, label, keep)
    return final


def _unpack(backup_file: Path, target: Path) -> None:
    try:
        with gzip.open(backup_file, "rb") as source, target.open("wb") as out:
            shutil.copyfileobj(source, out)
    except (OSError, EOFError) as exc:
        raise BackupBroken(f"{backup_file.name} cannot be unpacked: {exc}") from exc


def verify(backup_file: Path) -> dict[str, int]:
    """Check a backup is sound and say what is in it. Raises BackupBroken."""
    with tempfile.TemporaryDirectory(prefix="ninanatur-verify-") as work:
        raw = Path(work) / "check.sqlite"
        _unpack(backup_file, raw)
        try:
            result = _integrity(raw)
        except sqlite3.DatabaseError as exc:
            raise BackupBroken(f"{backup_file.name} is not a SQLite database") from exc
        if result != "ok":
            raise BackupBroken(f"{backup_file.name} failed integrity_check: {result}")
        conn = sqlite3.connect(f"file:{raw}?mode=ro", uri=True)
        try:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            present = {row[0] for row in tables}
            # Table names come from the constant above, never from input.
            return {table: int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
                    for table in COUNTED if table in present}
        finally:
            conn.close()


def restore(backup_file: Path, target: Path, *, replace: bool = False) -> dict[str, int]:
    """Put a backup back at `target`, after checking it. Returns what it holds.

    Refuses an existing target unless `replace` — restoring over the live file
    by accident would destroy exactly what the backup was meant to protect.
    Replacing a live database is for a stopped app; the drill says so.
    """
    counts = verify(backup_file)
    if target.exists() and not replace:
        raise FileExistsError(f"{target} exists; restore into a new file, or pass replace")
    target.parent.mkdir(parents=True, exist_ok=True)
    incoming = target.with_name(target.name + ".restoring")
    _unpack(backup_file, incoming)
    for leftover in ("-journal", "-wal", "-shm"):
        target.with_name(target.name + leftover).unlink(missing_ok=True)
    os.replace(incoming, target)
    return counts


def snapshot_before_migration(db: Path, dest: Path, *, now: datetime | None = None) -> Path | None:
    """The copy taken at startup, before migrations run. None for a fresh volume."""
    if not db.exists() or db.stat().st_size == 0:
        return None
    return create(db, dest, label="pre-migration", keep=KEEP_PRE_MIGRATION, now=now)


def default_dest(db: Path) -> Path:
    """`/data/backups` in the container — inside the volume, beside the database."""
    return db.parent / "backups"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ninanatur.ops.backup")
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("create", help="copy the database, check it, keep it")
    make.add_argument("--dest", type=Path)
    make.add_argument("--keep", type=int, default=KEEP_NIGHTLY)
    check = commands.add_parser("verify", help="check a backup and say what it holds")
    check.add_argument("file", type=Path)
    back = commands.add_parser("restore", help="put a backup back")
    back.add_argument("file", type=Path)
    back.add_argument("target", type=Path)
    back.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "create":
        db = database_path()
        made = create(db, args.dest or default_dest(db), keep=args.keep)
        print(f"holds: {verify(made)}")
        print(made)  # last line: what deploy/backup.sh copies off the volume
    elif args.command == "verify":
        print(f"{args.file.name}: ok, holds {verify(args.file)}")
    else:
        print(f"restored {args.target}: {restore(args.file, args.target, replace=args.replace)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
