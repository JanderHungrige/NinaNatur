"""Schema evolution on databases that already exist.

CREATE TABLE IF NOT EXISTS does nothing when the table is there, so a new column
never reaches an existing database — including the production volume, where
startup then fails on the first statement that references it.
"""
import sqlite3
from pathlib import Path

from ninanatur.ingest.db import COLUMN_MIGRATIONS, connect, init_schema


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_a_missing_column_is_added_to_an_existing_table(tmp_path: Path) -> None:
    """Regression: adding insect_group broke startup against any older database."""
    db = tmp_path / "old.sqlite"
    old = connect(db, same_thread=False)
    # A table as an earlier release created it — no insect_group.
    old.executescript(
        "CREATE TABLE insect_de (canonical_name TEXT PRIMARY KEY,"
        " scientific_name TEXT, occurrences INTEGER NOT NULL DEFAULT 0);"
    )
    old.execute("INSERT INTO insect_de (canonical_name) VALUES ('Apis mellifera')")
    old.commit()
    assert "insect_group" not in _columns(old, "insect_de")

    applied = init_schema(old)
    assert "insect_de.insect_group" in applied
    assert "insect_group" in _columns(old, "insect_de")


def test_existing_rows_survive_the_migration(tmp_path: Path) -> None:
    """An ALTER that dropped data would be worse than the crash it replaces."""
    db = tmp_path / "old.sqlite"
    old = connect(db, same_thread=False)
    old.executescript(
        "CREATE TABLE insect_de (canonical_name TEXT PRIMARY KEY,"
        " scientific_name TEXT, occurrences INTEGER NOT NULL DEFAULT 0);"
    )
    old.execute("INSERT INTO insect_de (canonical_name, occurrences) VALUES ('Apis mellifera', 42)")
    old.commit()

    init_schema(old)
    row = old.execute(
        "SELECT occurrences, insect_group FROM insect_de WHERE canonical_name='Apis mellifera'"
    ).fetchone()
    assert row["occurrences"] == 42
    assert row["insect_group"] is None


def test_running_twice_applies_nothing_the_second_time(tmp_path: Path) -> None:
    conn = connect(tmp_path / "fresh.sqlite", same_thread=False)
    init_schema(conn)
    assert init_schema(conn) == [], "a second run must be a no-op"


def test_a_fresh_database_needs_no_migration(tmp_path: Path) -> None:
    """The tables are created with their columns; migrations are for older files."""
    conn = connect(tmp_path / "brand-new.sqlite", same_thread=False)
    assert init_schema(conn) == []
    for table, column, _type in COLUMN_MIGRATIONS:
        assert column in _columns(conn, table)


def test_the_catalogue_syncs_when_the_shipped_schema_is_a_column_behind(
    tmp_path: Path,
) -> None:
    """Regression: `INSERT ... SELECT *` couples the two schemas positionally.

    Adding `insect_de.clade` made the shipped rows one value short, and the sync
    failed outright with "table insect_de has 5 columns but 4 values". A drop
    would have been worse — the counts would have matched and every value landed
    one field to the left, silently.

    This is the shape this project keeps meeting: the test double gets a fresh,
    complete state, and production always has a grown one. Here the *catalogue*
    is the stale side.
    """
    from ninanatur.ingest.catalogue import VERSION_KEY, sync_catalogue

    shipped = tmp_path / "catalogue.sqlite"
    old = sqlite3.connect(shipped)
    old.executescript(
        """
        CREATE TABLE insect_de (canonical_name TEXT PRIMARY KEY,
            scientific_name TEXT, occurrences INTEGER NOT NULL DEFAULT 0,
            insect_group TEXT);
        INSERT INTO insect_de VALUES ('Apis mellifera', 'Apis mellifera L.', 900, 'bee');
        CREATE TABLE catalogue_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """
    )
    old.execute("INSERT INTO catalogue_meta VALUES (?, '2026-01-01')", (VERSION_KEY,))
    old.commit()
    old.close()

    conn = connect(tmp_path / "live.sqlite", same_thread=False)
    init_schema(conn)  # current schema: insect_de has `clade`
    sync_catalogue(conn, shipped)

    row = conn.execute(
        "SELECT scientific_name, occurrences, insect_group, clade FROM insect_de"
        " WHERE canonical_name = 'Apis mellifera'"
    ).fetchone()
    assert row is not None, "the shipped row never arrived"
    # Every value in its own field, and the column the catalogue never had
    # falling back to its default rather than to NULL or to a shifted value.
    assert row["scientific_name"] == "Apis mellifera L."
    assert row["occurrences"] == 900
    assert row["insect_group"] == "bee"
    assert row["clade"] == "insect"


def test_an_existing_planting_table_learns_to_hold_unnamed_plants(tmp_path: Path) -> None:
    """Regression in waiting: `CREATE TABLE IF NOT EXISTS` cannot relax NOT NULL.

    Wave 7 made `planting.taxon_id` nullable so a plant the catalogue cannot
    name is still a plant in someone's garden. On a fresh database the new
    schema simply applies; on the production volume the old table survives with
    its constraint intact, and every unidentified planting would fail on insert
    — after the deploy, in front of the user, with green tests behind it.
    """
    db = tmp_path / "grown.sqlite"
    old = connect(db, same_thread=False)
    old.executescript(
        """
        CREATE TABLE taxon (taxon_id INTEGER PRIMARY KEY, canonical_name TEXT NOT NULL,
            occurs_de INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE bed (bed_id INTEGER PRIMARY KEY, garden_id INTEGER NOT NULL,
            name TEXT NOT NULL, polygon TEXT NOT NULL);
        CREATE TABLE planting (
            planting_id INTEGER PRIMARY KEY,
            bed_id INTEGER NOT NULL REFERENCES bed(bed_id) ON DELETE CASCADE,
            taxon_id INTEGER NOT NULL REFERENCES taxon(taxon_id),
            quantity INTEGER NOT NULL DEFAULT 1,
            added_at TEXT NOT NULL,
            UNIQUE (bed_id, taxon_id));
        INSERT INTO taxon VALUES (7, 'Salvia pratensis', 1);
        INSERT INTO bed VALUES (1, 1, 'Altbeet', '[]');
        INSERT INTO planting VALUES (1, 1, 7, 3, '2026-01-01');
        """
    )
    old.commit()
    old.close()

    conn = connect(db, same_thread=False)
    init_schema(conn)

    # The plant that was already there survives the rebuild, quantity and all.
    kept = conn.execute("SELECT * FROM planting WHERE planting_id = 1").fetchone()
    assert kept is not None
    assert kept["taxon_id"] == 7
    assert kept["quantity"] == 3

    # And an unidentified one can now be recorded.
    conn.execute(
        "INSERT INTO planting (bed_id, taxon_id, raw_name, quantity, added_at)"
        " VALUES (1, NULL, 'Bauernhortensie', 2, '2026-08-29')"
    )
    conn.commit()
    assert conn.execute("SELECT COUNT(*) AS n FROM planting").fetchone()["n"] == 2


def test_two_unidentified_plantings_can_share_a_bed(tmp_path: Path) -> None:
    """The UNIQUE stays; SQLite treats NULLs as distinct, which is what should
    happen — two unknown roses are two plants."""
    conn = connect(tmp_path / "fresh.sqlite", same_thread=False)
    init_schema(conn)
    conn.execute("INSERT INTO garden (garden_id, share_token, name, latitude, longitude,"
                 " created_at, updated_at) VALUES (1, 't', 'G', 52.5, 13.4, '', '')")
    conn.execute("INSERT INTO bed (bed_id, garden_id, name, polygon) VALUES (1, 1, 'B', '[]')")
    for name in ("Rose A", "Rose B"):
        conn.execute(
            "INSERT INTO planting (bed_id, taxon_id, raw_name, quantity, added_at)"
            " VALUES (1, NULL, ?, 1, '')",
            (name,),
        )
    conn.commit()
    assert conn.execute("SELECT COUNT(*) AS n FROM planting").fetchone()["n"] == 2


def test_wave_10_clears_gardens_rather_than_migrating_circle_shaped_houses(
    tmp_path: Path,
) -> None:
    """Decided with the user: this is a test deployment, so existing gardens go.

    Every stored light value came from a model in which a house was a cylinder.
    Keeping them would mean either a compatibility path for circle-shaped houses
    or numbers that quietly mean something else than they did — and two shadow
    models living side by side is the double-path shape that has caught this
    project twice already.

    The reset must be *once*: a migration that clears gardens on every startup
    would delete a garden the moment somebody made one.
    """
    db = tmp_path / "grown.sqlite"
    old = connect(db, same_thread=False)
    # The pre-Wave-10 shape, written out rather than produced by the current
    # init_schema — which would already mark the reset as done and make this
    # test pass without testing anything.
    old.executescript(
        """
        CREATE TABLE garden (garden_id INTEGER PRIMARY KEY, share_token TEXT NOT NULL,
            owner_id TEXT, name TEXT NOT NULL, latitude REAL NOT NULL,
            longitude REAL NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE bed (bed_id INTEGER PRIMARY KEY, garden_id INTEGER NOT NULL,
            name TEXT NOT NULL, polygon TEXT NOT NULL);
        CREATE TABLE obstacle (obstacle_id INTEGER PRIMARY KEY, garden_id INTEGER NOT NULL,
            kind TEXT NOT NULL, x REAL NOT NULL, y REAL NOT NULL,
            radius REAL NOT NULL, height REAL NOT NULL);
        INSERT INTO garden VALUES (1, 'alt', NULL, 'Alter Garten', 52.5, 13.4, '', '');
        INSERT INTO bed VALUES (1, 1, 'B', '[]');
        INSERT INTO obstacle VALUES (1, 1, 'house', 0, 0, 5, 7);
        """
    )
    old.commit()
    old.close()

    conn = connect(db, same_thread=False)
    init_schema(conn)
    assert conn.execute("SELECT COUNT(*) AS n FROM garden").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM bed").fetchone()["n"] == 0

    # And a garden made afterwards survives the next startup.
    conn.execute(
        "INSERT INTO garden (garden_id, share_token, name, latitude, longitude,"
        " created_at, updated_at) VALUES (2, 'neu', 'Neuer Garten', 52.5, 13.4, '', '')"
    )
    conn.commit()
    init_schema(conn)
    assert conn.execute("SELECT COUNT(*) AS n FROM garden").fetchone()["n"] == 1


def test_an_obstacle_carries_its_shape(tmp_path: Path) -> None:
    conn = connect(tmp_path / "fresh.sqlite", same_thread=False)
    init_schema(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(obstacle)")}
    assert {"shape", "width", "depth", "rotation", "points"} <= columns
    # `radius` is gone: it was the cylinder assumption in column form, and a
    # column nothing writes is a column somebody will eventually read.
    assert "radius" not in columns
