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
    relax_planting_taxon,
    wave_10_reset,
    wave_11_reset,
)
from ninanatur.ingest.schema import SCHEMA

DEFAULT_DB_PATH = Path("data/ninanatur.sqlite")
DB_PATH_ENV = "NINANATUR_DB"

#: Re-exported: callers and tests reach for these here, and moving the schema
#: out should not move where the rest of the project imports from.
__all__ = [
    "DB_PATH_ENV",
    "DEFAULT_DB_PATH",
    "ELEMENT_RESET_KEY",
    "RESET_KEY",
    "SCHEMA",
    "connect",
    "database_path",
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
    return conn


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
    conn.commit()
    return applied
