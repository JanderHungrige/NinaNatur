"""Bringing an existing database up to the current schema.

Every migration here runs against a database that has already been in
production, which is the state a test double never reproduces. They are
ordered, and the order is load-bearing.
"""
from __future__ import annotations

import sqlite3

#: Marks the one-time Wave 10 reset as done.
RESET_KEY = "wave_10_geometry_reset"
#: Marks the one-time Wave 11 merge of bed and obstacle into element.
ELEMENT_RESET_KEY = "wave_11_element_reset"

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


def wave_10_reset(conn: sqlite3.Connection) -> str | None:
    """Clear gardens once, when the plan's geometry changed under them.

    Decided with the user: this is a test deployment, so gardens made against
    the cylinder model go rather than being migrated. Every stored light value
    came from a model in which a house was a circle, and keeping them would mean
    either a compatibility path for circle-shaped houses or numbers that quietly
    mean something else than they did.

    Marked in `catalogue_meta` so it runs **once**. A migration that cleared
    gardens on every startup would delete a garden the moment somebody made one
    — which is the kind of thing that only shows up in production.
    """
    # Just this table, not the whole schema: `executescript(SCHEMA)` creates
    # indexes over columns an existing database may not have yet, which is why
    # the column migrations run before it. Reaching for the marker must not
    # reorder that.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS catalogue_meta"
        " (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    done = conn.execute(
        "SELECT 1 FROM catalogue_meta WHERE key = ?", (RESET_KEY,)
    ).fetchone()
    if done is not None:
        return None
    has_obstacle = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='obstacle'"
    ).fetchone()
    if has_obstacle is None:
        # A brand-new database: nothing to clear, but the marker still goes in
        # so the reset never fires later against real gardens.
        conn.execute(
            "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
            (RESET_KEY, "fresh"),
        )
        conn.commit()
        return None

    columns = {row[1] for row in conn.execute("PRAGMA table_info(obstacle)")}
    if "shape" in columns:
        conn.execute(
            "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
            (RESET_KEY, "already"),
        )
        conn.commit()
        return None

    conn.execute("PRAGMA foreign_keys=OFF")
    present = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    # Only what is there. A half-built database is a state this has to survive,
    # not a reason to refuse to start.
    for table in ("planting", "obstacle", "bed", "garden"):
        if table in present:
            conn.execute(f"DELETE FROM {table}")  # noqa: S608
    conn.execute('DROP TABLE obstacle;')
    conn.execute(
        "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
        (RESET_KEY, "cleared"),
    )
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    return "gardens cleared for the Wave 10 geometry"


def wave_11_reset(conn: sqlite3.Connection) -> str | None:
    """Fold `bed` and `obstacle` into `element`, clearing gardens once.

    Decided with the user: still the test phase, so gardens go rather than being
    migrated. Carrying them over would mean deciding what a bed's polygon becomes
    when a bed stops being its own kind of thing — a decision worth making when
    there are real gardens to lose, not before.

    `planting` goes with them. Its foreign key points at `bed`, and a child table
    whose parent no longer exists is a query that fails at the worst moment.

    Marked in `catalogue_meta` so it runs **once**. A reset that fired on every
    startup would delete the garden somebody made a minute ago.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS catalogue_meta"
        " (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    done = conn.execute(
        "SELECT 1 FROM catalogue_meta WHERE key = ?", (ELEMENT_RESET_KEY,)
    ).fetchone()
    if done is not None:
        return None

    present = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if "bed" not in present and "obstacle" not in present:
        # A database that never knew the old shape. The marker still goes in, so
        # this can never fire later against real gardens.
        conn.execute(
            "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
            (ELEMENT_RESET_KEY, "fresh"),
        )
        conn.commit()
        return None

    conn.execute("PRAGMA foreign_keys=OFF")
    # Only what is there. A half-built database is a state this has to survive,
    # not a reason to refuse to start.
    for table in ("planting", "obstacle", "bed", "garden"):
        if table in present:
            conn.execute(f"DELETE FROM {table}")  # noqa: S608
    for table in ("planting", "obstacle", "bed"):
        if table in present:
            conn.execute(f"DROP TABLE {table}")  # noqa: S608
    conn.execute(
        "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
        (ELEMENT_RESET_KEY, "cleared"),
    )
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()
    return "bed and obstacle folded into element; gardens cleared"


COLOURS_MOVED_KEY = "wave_15_colours_moved"


def move_observed_colours(conn: sqlite3.Connection) -> str | None:
    """Carry per-garden colour notes into the shared catalogue.

    They used to live in `observed_colour` on the volume, one row per garden per
    species, deliberately outside `trait`. The gardener asked for the opposite:
    one general database, the entry marked manual, overridable by any published
    source. These are the notes somebody already made, and dropping them would
    be answering "where should this live" by throwing it away.

    Two gardens that noted different colours for one species cannot both win —
    the catalogue holds one manual value per species. The later note is kept,
    which is the same rule a second answer from one gardener follows.

    Marked in `catalogue_meta` so it runs once. Run twice it would resurrect a
    note somebody has since taken back.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS catalogue_meta"
        " (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    done = conn.execute(
        "SELECT 1 FROM catalogue_meta WHERE key = ?", (COLOURS_MOVED_KEY,)
    ).fetchone()
    if done is not None:
        return None

    present = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='observed_colour'"
    ).fetchone()
    moved = 0
    if present is not None:
        rows = conn.execute(
            "SELECT taxon_id, colour, noted_at FROM observed_colour ORDER BY noted_at"
        ).fetchall()
        for row in rows:
            conn.execute(
                "INSERT INTO trait (taxon_id, trait_key, source, license,"
                " value_text, confidence, retrieved_at)"
                " VALUES (?, 'flower_colour', 'manual', 'user-contributed', ?, 0.4, ?)"
                " ON CONFLICT (taxon_id, trait_key, source) DO UPDATE SET"
                " value_text = excluded.value_text, retrieved_at = excluded.retrieved_at",
                (int(row["taxon_id"]), str(row["colour"]), str(row["noted_at"])),
            )
            moved += 1

    conn.execute(
        "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
        (COLOURS_MOVED_KEY, str(moved)),
    )
    conn.commit()
    return None if moved == 0 else f"moved {moved} noted colour(s) into the catalogue"
