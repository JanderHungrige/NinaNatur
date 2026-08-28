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
from datetime import UTC, datetime
from pathlib import Path

# Everything the serving path reads. Deliberately excludes `interaction` (600k
# ingest-time rows, summarised into partner_* above) and `taxon_name` (a
# resolution cache that only the ingest uses).
CATALOGUE_TABLES: tuple[str, ...] = (
    "taxon",
    "trait",
    "partner_summary",
    "partner_totals",
    # Wave 5: the group breakdown, and the checklist it is derived from — the
    # score needs both, and a catalogue missing them would serve a product that
    # cannot explain its own number.
    "partner_groups",
    "insect_de",
)

DEFAULT_CATALOGUE = Path("ninanatur/data/catalogue.sqlite")
VERSION_KEY = "catalogue_built_at"


def export_catalogue(conn: sqlite3.Connection, dest: Path) -> dict[str, int]:
    """Write a runtime-only catalogue, stamped with a build time.

    The stamp is what lets a deployment tell a shipped catalogue apart from the
    one it already has, so an improvement actually reaches an existing volume.
    """
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
        out.execute("CREATE TABLE IF NOT EXISTS catalogue_meta (key TEXT PRIMARY KEY,"
                    " value TEXT NOT NULL)")
        out.execute("INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
                    (VERSION_KEY, datetime.now(UTC).isoformat(timespec="seconds")))
        out.commit()
        out.execute("VACUUM")
    finally:
        out.close()
    return counts


def catalogue_is_empty(conn: sqlite3.Connection) -> bool:
    """Whether this database has no plants at all."""
    row = conn.execute("SELECT COUNT(*) AS n FROM taxon").fetchone()
    return int(row["n"]) == 0


def _version_of(conn: sqlite3.Connection, prefix: str = "") -> str | None:
    table = f"{prefix}catalogue_meta" if prefix else "catalogue_meta"
    present = conn.execute(
        f"SELECT 1 FROM {prefix}sqlite_master WHERE type='table' AND name='catalogue_meta'"  # noqa: S608
    ).fetchone()
    if present is None:
        return None
    row = conn.execute(
        f"SELECT value FROM {table} WHERE key = ?", (VERSION_KEY,)  # noqa: S608
    ).fetchone()
    return str(row["value"]) if row else None


def sync_catalogue(conn: sqlite3.Connection, source: Path) -> dict[str, int]:
    """Bring the database's catalogue up to the shipped build.

    Runs whenever the stamps differ, not only on an empty database. The old
    emptiness check meant a shipped improvement never reached an existing volume
    — the insect group breakdown was live in the image and absent in production
    for exactly that reason.

    Rows are upserted rather than replaced: `taxon` is referenced by `planting`,
    so deleting it would either fail on the foreign key or take someone's garden
    with it. A species dropped upstream therefore lingers, which is harmless — it
    simply stays suggestible until the next full rebuild.
    """
    if not source.exists():
        return {}

    conn.execute("ATTACH DATABASE ? AS shipped", (str(source),))
    try:
        shipped_version = _version_of(conn, "shipped.")
        current_version = _version_of(conn)
        if shipped_version is not None and shipped_version == current_version:
            return {}

        counts: dict[str, int] = {}
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
        if shipped_version is not None:
            conn.execute(
                "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
                (VERSION_KEY, shipped_version),
            )
        conn.commit()
        return counts
    finally:
        conn.execute("DETACH DATABASE shipped")
