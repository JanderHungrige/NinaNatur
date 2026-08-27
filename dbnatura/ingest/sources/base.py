"""The contract every source adapter implements."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class TraitRecord:
    """One normalised trait value, before name resolution."""

    name: str
    trait_key: str
    value: float | None = None
    text: str | None = None
    unit: str | None = None


class Source(Protocol):
    """A source adapter fetches, normalises and writes — nothing else."""

    name: str
    license: str

    def run(self, conn: sqlite3.Connection) -> int:
        """Ingest into `conn`, returning the number of rows written."""
        ...


def start_run(conn: sqlite3.Connection, source: str) -> str:
    started = datetime.now(UTC).isoformat(timespec="seconds")
    conn.execute(
        "INSERT OR REPLACE INTO source_run (source, started_at, status) VALUES (?, ?, 'running')",
        (source, started),
    )
    conn.commit()
    return started


def finish_run(
    conn: sqlite3.Connection, source: str, started: str, rows: int, status: str, note: str = ""
) -> None:
    conn.execute(
        "UPDATE source_run SET finished_at = ?, rows = ?, status = ?, note = ?"
        " WHERE source = ? AND started_at = ?",
        (
            datetime.now(UTC).isoformat(timespec="seconds"),
            rows,
            status,
            note,
            source,
            started,
        ),
    )
    conn.commit()
