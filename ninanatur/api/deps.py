"""Shared API dependencies."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from ninanatur.ingest.db import connect, database_path


def get_connection() -> Iterator[sqlite3.Connection]:
    """One connection per request.

    `same_thread=False` because FastAPI runs sync endpoints in a threadpool, and a
    connection created for one request would otherwise be unusable in the thread
    that serves the next. Overridden wholesale in tests, which is why every
    handler takes it as a dependency rather than opening its own.
    """
    conn = connect(database_path(), same_thread=False)
    try:
        yield conn
    finally:
        conn.close()
