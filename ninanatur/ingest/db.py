"""Opening the database, and bringing it up to the current schema.

One module owns this. Every other module receives an open connection — nothing
else opens a database or issues DDL.

The schema itself lives in `schema.py` and the catch-up work in `migrations.py`.
Splitting them was overdue: this file was 495 lines, and the two halves are read
for different reasons — one says what the tables are, the other how a database
that predates them catches up.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from ninanatur.ingest.migrations import (
    ELEMENT_RESET_KEY,
    RESET_KEY,
    apply_column_migrations,
    move_observed_colours,
    relax_planting_taxon,
    wave_10_reset,
    wave_11_reset,
)
from ninanatur.ingest.schema import SCHEMA

DEFAULT_DB_PATH = Path("data/ninanatur.sqlite")
DB_PATH_ENV = "NINANATUR_DB"
#: How long a connection waits for a lock before giving up. Long enough to sit
#: out a commit or a checkpoint, short enough that a genuinely stuck write still
#: surfaces as an error rather than a hung request.
BUSY_TIMEOUT_MS = 5000

#: Re-exported: callers and tests reach for these here, and moving the schema
#: out should not move where the rest of the project imports from.
__all__ = [
    "BUSY_TIMEOUT_MS",
    "DB_PATH_ENV",
    "DEFAULT_DB_PATH",
    "ELEMENT_RESET_KEY",
    "RESET_KEY",
    "SCHEMA",
    "connect",
    "database_path",
    "enable_wal",
    "init_schema",
]


def database_path() -> Path:
    """Where the database lives.

    Configurable because the container mounts its data elsewhere than the repo
    checkout, and because tests need to point at a throwaway file without
    monkeypatching a module constant.
    """
    return Path(os.environ.get(DB_PATH_ENV) or DEFAULT_DB_PATH)


def connect(
    path: str | Path = DEFAULT_DB_PATH, *, same_thread: bool = True
) -> sqlite3.Connection:
    """Open a connection with row access by column name and FK enforcement on.

    `same_thread=False` is for the read-only API, whose sync endpoints run in
    FastAPI's threadpool: a connection would otherwise be unusable in the thread
    that receives the next request. The ingest path keeps the guard, because it
    writes and a connection shared across writing threads corrupts.
    """
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Said explicitly rather than inherited from the driver's default, because
    # it is what stands between a busy moment and a 500.
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    # Per connection, and only meaningful under WAL: a power cut can lose the
    # last commit but never corrupt, and a write saves an fsync.
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def enable_wal(conn: sqlite3.Connection) -> str:
    """Put the database in write-ahead-log mode; returns the mode it is in.

    Under the default rollback journal a writer that is committing locks the
    whole file, and a reader waiting longer than the busy timeout gets
    "database is locked" — a 500 no single-threaded test sees. Under WAL readers
    read the last committed state while a writer writes.

    Called by the app's startup on its own database, not by `connect`: the mode
    is stored in the file, so once is enough, and switching it needs write
    access that the catalogue in the image and a read-only copy do not give.
    """
    return str(conn.execute("PRAGMA journal_mode = WAL").fetchone()[0])


def init_schema(conn: sqlite3.Connection) -> list[str]:
    """Create every table and index, and bring an older database up to date.

    Migrations run first: the schema script includes indexes over columns that an
    existing table may not have yet, and executescript would fail on those before
    reaching anything else.

    Returns the migrations applied, so a deployment can say what it changed.
    """
    applied = apply_column_migrations(conn)
    rebuilt = relax_planting_taxon(conn)
    # After the column work and before the schema script: these resets remove
    # tables, and `executescript` below is what builds their replacements.
    for reset in (wave_10_reset(conn), wave_11_reset(conn)):
        if reset is not None:
            applied.append(reset)
    if rebuilt is not None:
        applied.append(rebuilt)
    conn.executescript(SCHEMA)
    # After the schema script: `trait` must exist before anything is written
    # into it, and on a fresh database it does not exist before this line.
    moved = move_observed_colours(conn)
    if moved is not None:
        applied.append(moved)
    conn.commit()
    return applied
