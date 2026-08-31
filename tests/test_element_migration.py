"""Coming up on a database built by the Wave 10 image.

A fresh volume never has an `obstacle` table to drop or a `planting.bed_id` to
replace, so it proves nothing about this migration. These tests build the old
shape by hand and then run the current schema over it — the cheap stand-in for
the container check that follows.
"""
from __future__ import annotations

import sqlite3

from ninanatur.ingest.db import ELEMENT_RESET_KEY, init_schema


def _wave_10_database() -> sqlite3.Connection:
    """The tables as the Wave 10 image left them."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE garden (garden_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
            latitude REAL, longitude REAL, share_token TEXT, created_at TEXT,
            updated_at TEXT);
        CREATE TABLE bed (bed_id INTEGER PRIMARY KEY, garden_id INTEGER NOT NULL,
            name TEXT NOT NULL, polygon TEXT NOT NULL, soil_type TEXT,
            moisture TEXT, sun_hours REAL, height_above_ground REAL DEFAULT 0);
        CREATE TABLE obstacle (obstacle_id INTEGER PRIMARY KEY,
            garden_id INTEGER NOT NULL, kind TEXT NOT NULL, x REAL, y REAL,
            shape TEXT DEFAULT 'circle', width REAL, depth REAL,
            rotation REAL DEFAULT 0, points TEXT, height REAL,
            label TEXT, height_source TEXT DEFAULT 'user');
        CREATE TABLE planting (planting_id INTEGER PRIMARY KEY,
            bed_id INTEGER NOT NULL REFERENCES bed(bed_id), taxon_id INTEGER,
            raw_name TEXT, quantity INTEGER DEFAULT 1, added_at TEXT);
        INSERT INTO garden VALUES (1,'Alt',52.5,13.4,'tok','','');
        INSERT INTO bed VALUES (1,1,'Altbeet','[[0,0],[4,0],[4,3]]','loam','fresh',6.2,0);
        INSERT INTO obstacle VALUES (1,1,'house',0,0,'rect',10,8,0,NULL,6,NULL,'user');
        INSERT INTO planting VALUES (1,1,1234,NULL,3,'2026-08-30');
        """
    )
    conn.commit()
    return conn


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def test_a_wave_10_database_comes_up() -> None:
    """The whole point. A migration that raises on startup takes the site down
    and no unit test that only ever sees an empty database would notice."""
    conn = _wave_10_database()
    applied = init_schema(conn)
    assert any("element" in line for line in applied), applied
    assert "element" in _tables(conn)


def test_the_replaced_tables_are_gone() -> None:
    conn = _wave_10_database()
    init_schema(conn)
    assert "obstacle" not in _tables(conn)
    assert "bed" not in _tables(conn)


def test_planting_hangs_off_an_element() -> None:
    conn = _wave_10_database()
    init_schema(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(planting)")}
    assert "element_id" in columns
    assert "bed_id" not in columns


def test_gardens_are_cleared_as_agreed() -> None:
    """Decided with the user: still the test phase, so old gardens go rather
    than being migrated."""
    conn = _wave_10_database()
    init_schema(conn)
    assert conn.execute("SELECT count(*) FROM garden").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM planting").fetchone()[0] == 0


def test_it_runs_once() -> None:
    """A reset that fires on every startup deletes the garden somebody made a
    minute ago — the kind of thing that only shows up in production."""
    conn = _wave_10_database()
    init_schema(conn)
    conn.execute(
        "INSERT INTO garden (garden_id, name, latitude, longitude, share_token,"
        " created_at, updated_at) VALUES (9,'Neu',52.5,13.4,'t2','','')"
    )
    conn.commit()
    second = init_schema(conn)
    assert not any("element" in line for line in second), second
    assert conn.execute("SELECT count(*) FROM garden").fetchone()[0] == 1


def test_a_fresh_database_is_marked_without_clearing_anything() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    assert "element" in _tables(conn)
    marker = conn.execute(
        "SELECT value FROM catalogue_meta WHERE key = ?", (ELEMENT_RESET_KEY,)
    ).fetchone()
    assert marker is not None and marker[0] == "fresh"


def test_an_element_carries_geometry_and_site_in_one_row() -> None:
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(element)")}
    # Geometry, plus what a planting site needs — null on a paving slab.
    for column in ("kind", "shape", "x", "y", "points", "width", "constraint_hint"):
        assert column in columns, column
    for column in ("soil_type", "moisture", "sun_hours", "height_above_ground"):
        assert column in columns, column
    # And what Wave 11 took out of storage.
    for gone in ("depth", "rotation"):
        assert gone not in columns, f"{gone} should not be stored any more"
