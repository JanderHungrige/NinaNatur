"""Data migrations that run exactly once, each marked in `catalogue_meta`.

A column is added by `migrations.py` whenever it is missing; these are different
in kind. Each rewrites what existing rows *mean* — clears gardens made against
an older geometry, folds two tables into one, moves notes into the catalogue,
marks where a roof came from — and running one twice would undo something a
person has done since. So each writes its marker, even on a fresh database with
nothing to do, and returns a line for the startup log only when it changed
anything.

Split from `migrations.py` in Wave 21.
"""
from __future__ import annotations

import sqlite3

#: Marks the one-time Wave 10 reset as done.
RESET_KEY = "wave_10_geometry_reset"


#: Marks the one-time Wave 11 merge of bed and obstacle into element.
ELEMENT_RESET_KEY = "wave_11_element_reset"


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


#: Marks the one-time Wave 21 backfill of where roofs and eaves came from.
ROOF_PROVENANCE_KEY = "wave_21_roof_provenance"

#: What the history makes certain, in order (doc 93). Until Wave 21 the element
#: form sent the pre-filled height on every save, so a row somebody saved says
#: `height_source = 'user'`; the survey wrote a roof, its source and the eaves
#: together; the raster never wrote a roof; the import was the only other writer
#: of eaves. Houses and sheds are spelt out rather than read from `objects`: a
#: migration has to mean what it meant on the day it ran.
_ROOF_PROVENANCE_STEPS = (
    # Saved after the survey: the shape may be theirs, and under-claiming a
    # measurement is the safe way to be wrong.
    "UPDATE element SET roof_source = 'user'"
    " WHERE roof_source = 'surveyed' AND height_source = 'user'",
    # Never saved: the shape came with the import.
    "UPDATE element SET roof_source = 'osm'"
    " WHERE roof_source = 'user' AND height_source != 'user'"
    " AND kind IN ('house', 'shed')",
    # Saved: typed, or seen and kept.
    "UPDATE element SET eaves_source = 'user'"
    " WHERE eaves_m IS NOT NULL AND eaves_source IS NULL AND height_source = 'user'",
    # Never saved and never surveyed: only the import wrote it.
    "UPDATE element SET eaves_source = 'osm_levels'"
    " WHERE eaves_m IS NOT NULL AND eaves_source IS NULL"
    " AND height_source != 'user' AND roof_source != 'surveyed'",
)


def roof_provenance(conn: sqlite3.Connection) -> str | None:
    """Say where existing roofs and eaves came from, where their history can.

    Eaves the survey may or may not have written — its own, or the import's
    that it kept because it had none — are left unmarked rather than guessed
    at. The next recompute says, because the survey now marks what it writes.
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS catalogue_meta"
        " (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    done = conn.execute(
        "SELECT 1 FROM catalogue_meta WHERE key = ?", (ROOF_PROVENANCE_KEY,)
    ).fetchone()
    if done is not None:
        return None
    changed = sum(conn.execute(step).rowcount for step in _ROOF_PROVENANCE_STEPS)
    conn.execute(
        "INSERT OR REPLACE INTO catalogue_meta (key, value) VALUES (?, ?)",
        (ROOF_PROVENANCE_KEY, str(changed)),
    )
    conn.commit()
    return None if changed == 0 else f"marked where {changed} roof value(s) came from"
