"""The candidate set, held between requests.

Every search, every bed's suggestions and every improvement starts from the same
8,939 species, and `load_candidates` built them afresh each time: 238–544 ms of
each of those requests against a copy of the live database, more on the host.
They change far less often than that, and in two ways only:

- **a new catalogue build**, which startup syncs and stamps
  (`catalogue_built_at`), and
- **a colour somebody entered by hand**, a trait row written while the app runs,
  which `record_colour` counts in the same transaction (`catalogue_edits`).

Both are read from the database on every call — one primary-key lookup — so an
edit made through another connection, or one day by another process, is seen at
once. Nothing is invalidated by hand; the key simply stops matching.

What is held is the catalogue's answer and nothing else. A garden's own observed
colours are laid over it per request by `with_observed`, which replaces rows
rather than mutating them, and every caller gets a list of its own, so what one
request does with its copy cannot reach the next.

An in-memory database is never held: each `:memory:` connection is a database of
its own, with nothing to name it by.
"""
from __future__ import annotations

import sqlite3
import threading

from ninanatur.api.candidates import PlantRow, load_candidates
from ninanatur.ingest.catalogue import edition

#: Which database, which build, how many edits since.
Key = tuple[str, str | None, str | None]


class _Held:
    """One set at a time: a deployment serves one database."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.key: Key | None = None
        self.rows: list[PlantRow] = []


_HELD = _Held()


def candidate_set(conn: sqlite3.Connection) -> list[PlantRow]:
    """The whole German candidate set, read once per state of the catalogue.

    Two requests arriving on a cold set wait for one read rather than making
    two: the host has two cores, and the read is the expensive part.
    """
    key = _key(conn)
    if key is None:
        return load_candidates(conn)
    with _HELD.lock:
        if _HELD.key != key:
            _HELD.rows = load_candidates(conn)
            _HELD.key = key
        return list(_HELD.rows)


def _key(conn: sqlite3.Connection) -> Key | None:
    file = _file_of(conn)
    if not file:
        return None
    built, edits = edition(conn)
    return file, built, edits


def _file_of(conn: sqlite3.Connection) -> str:
    """The file behind this connection's main database; "" when there is none."""
    for row in conn.execute("PRAGMA database_list").fetchall():
        if row[1] == "main":
            return str(row[2] or "")
    return ""


__all__ = ["candidate_set"]
