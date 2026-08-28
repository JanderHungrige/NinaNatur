"""The shippable catalogue.

Plant data and garden data have different lifecycles and were wrongly living in
one file. The catalogue is derived from static sources and belongs with the code
that was built against it; gardens belong to the person who made them and belong
on a volume.

Putting both in one SQLite file meant a fresh deployment came up with an empty
catalogue and answered "0 matching species" to every request — structurally
perfect and completely useless.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# Everything the serving path reads. Deliberately excludes `interaction` (600k
# ingest-time rows, summarised into partner_* above) and `taxon_name` (a
# resolution cache that only the ingest uses).
CATALOGUE_TABLES: tuple[str, ...] = (
    "taxon",
    "trait",
    "partner_summary",
    "partner_totals",
)

DEFAULT_CATALOGUE = Path("ninanatur/data/catalogue.sqlite")


def export_catalogue(conn: sqlite3.Connection, dest: Path) -> dict[str, int]:
    """Write a runtime-only catalogue, returning the row count per table."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()

    out = sqlite3.connect(str(dest))
    out.row_factory = sqlite3.Row
    counts: dict[str, int] = {}
    try:
        for table in CATALOGUE_TABLES:
            schema = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if schema is None or schema["sql"] is None:
                continue
            out.execute(str(schema["sql"]))
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
            if rows:
                placeholders = ",".join("?" for _ in rows[0])
                out.executemany(
                    f"INSERT INTO {table} VALUES ({placeholders})",  # noqa: S608
                    [tuple(r) for r in rows],
                )
            counts[table] = len(rows)
        out.commit()
        out.execute("VACUUM")
    finally:
        out.close()
    return counts


def catalogue_is_empty(conn: sqlite3.Connection) -> bool:
    """Whether this database has no plants at all."""
    row = conn.execute("SELECT COUNT(*) AS n FROM taxon").fetchone()
    return int(row["n"]) == 0


def seed_catalogue(conn: sqlite3.Connection, source: Path) -> dict[str, int]:
    """Copy a shipped catalogue into an empty database.

    Only ever called when `catalogue_is_empty` — seeding over existing plant data
    would silently discard a newer ingest.
    """
    if not source.exists():
        return {}

    counts: dict[str, int] = {}
    conn.execute("ATTACH DATABASE ? AS shipped", (str(source),))
    try:
        for table in CATALOGUE_TABLES:
            present = conn.execute(
                "SELECT 1 FROM shipped.sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if present is None:
                continue
            conn.execute(f"INSERT OR REPLACE INTO {table} SELECT * FROM shipped.{table}")  # noqa: S608
            counts[table] = int(
                conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]  # noqa: S608
            )
        conn.commit()
    finally:
        conn.execute("DETACH DATABASE shipped")
    return counts
