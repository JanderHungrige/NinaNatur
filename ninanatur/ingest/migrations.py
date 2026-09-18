"""Bringing an existing database up to the current schema.

Every migration here runs against a database that has already been in
production, which is the state a test double never reproduces. They are
ordered, and the order is load-bearing.
"""
from __future__ import annotations

import sqlite3

COLUMN_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("insect_de", "insect_group", "TEXT"),
    # Existing rows are insects, so the default carries their meaning forward
    # without a data migration. Birds arrive with clade='bird'.
    ("insect_de", "clade", "TEXT NOT NULL DEFAULT 'insect'"),
    # Wave 7. Every existing bed sits on the ground, so the default keeps every
    # stored light value meaning exactly what it meant.
    ("bed", "height_above_ground", "REAL NOT NULL DEFAULT 0"),
    # Free text, and it drives nothing. "Die Buche vom Nachbarn" is worth
    # storing and is not a category.
    ("obstacle", "label", "TEXT"),
    ("bed", "label", "TEXT"),
    # Wave 7. What the user typed, kept beside whatever it matched — that is how
    # someone recognises their own entry, and how a later catalogue improvement
    # can re-resolve it.
    ("planting", "raw_name", "TEXT"),
    # Wave 9. Wave 8 reported where a height came from and then threw it away;
    # a sightline resting on a guessed building height must not be drawn as
    # though it were surveyed. Existing obstacles were entered by hand.
    ("obstacle", "height_source", "TEXT NOT NULL DEFAULT 'user'"),
    # Wave 12. Null on every existing garden, which is right: nobody has been
    # asked yet, and the question is what the feature adds.
    ("garden", "soil_type", "TEXT"),
    ("garden", "moisture", "TEXT"),
    # Wave 15. Where the gardener put this cluster, in metres relative to the
    # bed's own origin. Null means "nobody has moved it": the position is then
    # derived from the planting id, which puts it somewhere sensible inside the
    # bed and puts it in the same place on every render. Defaulting to 0,0
    # instead would stack every existing planting on one corner.
    ("planting", "x", "REAL"),
    ("planting", "y", "REAL"),
    # Wave 16. 'unknown' on every existing element, which is exactly how they
    # have always been treated: solid to the recorded height.
    ("element", "roof", "TEXT NOT NULL DEFAULT 'unknown'"),
    ("element", "eaves_m", "REAL"),
    # Wave 16. Empty on an existing grid, which the reader treats as "not split
    # yet" — the next recomputation fills it.
    ("light_grid", "morning", "TEXT NOT NULL DEFAULT '[]'"),
    # Wave 17. Null on every existing bed and null is the honest value: nobody
    # has fetched the ground yet, and a zero would say "flat" about a garden on
    # a hillside.
    ("element", "slope_deg", "REAL"),
    ("element", "aspect_deg", "REAL"),
    # Wave 19. 'user' on every existing element, which is what they are: every
    # roof in the database today was either picked by somebody or left at the
    # default, and neither should be overwritten by a survey arriving later.
    ("element", "roof_source", "TEXT NOT NULL DEFAULT 'user'"),
    # 2026-09-07. Which cells are a roof rather than ground. Empty on an
    # existing grid, which the reader treats as "computed before roofs were" —
    # every cell is then ground, exactly as it was, until the next rebuild.
    ("light_grid", "roof", "TEXT NOT NULL DEFAULT '[]'"),
    # Wave 21. Null on every existing row until the one-time backfill in
    # `one_time.roof_provenance` marks what the history makes certain.
    ("element", "eaves_source", "TEXT"),
)


def apply_column_migrations(conn: sqlite3.Connection) -> list[str]:
    """Add any missing columns. Returns what was added, for the startup log."""
    applied: list[str] = []
    for table, column, column_type in COLUMN_MIGRATIONS:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists is None:
            continue  # the table itself is about to be created with the column
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column in columns:
            continue
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        applied.append(f"{table}.{column}")
    if applied:
        conn.commit()
    return applied


def relax_planting_taxon(conn: sqlite3.Connection) -> str | None:
    """Let `planting.taxon_id` be NULL on a database that predates Wave 7.

    `CREATE TABLE IF NOT EXISTS` does nothing to an existing table, and no
    `ALTER TABLE` in SQLite removes a NOT NULL. The only way is the documented
    rebuild: make the new table, copy the rows, swap the names.

    Without it a fresh deployment works and the production volume rejects every
    unidentified planting — after the deploy, in front of the user, with a green
    suite behind it. That shape has cost this project five live findings already.
    """
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='planting'"
    ).fetchone()
    if exists is None:
        return None  # about to be created with the right definition
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(planting)")}
    taxon = columns.get("taxon_id")
    if taxon is None or taxon[3] == 0:
        return None  # already nullable

    carried = [
        c for c in ("planting_id", "bed_id", "taxon_id", "quantity", "added_at")
        if c in columns
    ]
    names = ", ".join(carried)
    # Foreign keys off for the swap, or the rename trips over its own references.
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.executescript(
        f"""
        CREATE TABLE planting_new (
            planting_id INTEGER PRIMARY KEY,
            bed_id      INTEGER NOT NULL REFERENCES bed(bed_id) ON DELETE CASCADE,
            taxon_id    INTEGER REFERENCES taxon(taxon_id),
            raw_name    TEXT,
            quantity    INTEGER NOT NULL DEFAULT 1,
            added_at    TEXT    NOT NULL,
            UNIQUE (bed_id, taxon_id)
        );
        INSERT INTO planting_new ({names}) SELECT {names} FROM planting;
        DROP TABLE planting;
        ALTER TABLE planting_new RENAME TO planting;
        """  # noqa: S608
    )
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    return "planting.taxon_id nullable"


