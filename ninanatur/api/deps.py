"""Shared API dependencies."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from ninanatur.ingest.db import DEFAULT_DB_PATH, connect


def get_connection() -> Iterator[sqlite3.Connection]:
    """One read-only-in-practice connection per request.

    Overridden wholesale in tests, which is why every handler takes it as a
    dependency rather than opening its own.
    """
    conn = connect(DEFAULT_DB_PATH, same_thread=False)
    try:
        yield conn
    finally:
        conn.close()
