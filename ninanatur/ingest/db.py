"""SQLite schema and connection handling.

One module owns the schema. Every other module receives an open connection —
nothing else opens a database or issues DDL.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/ninanatur.sqlite")
DB_PATH_ENV = "NINANATUR_DB"


def database_path() -> Path:
    """Where the database lives.

    Configurable because the container mounts its data elsewhere than the repo
    checkout, and because tests need to point at a throwaway file without
    monkeypatching a module constant.
    """
    return Path(os.environ.get(DB_PATH_ENV) or DEFAULT_DB_PATH)

SCHEMA = """
CREATE TABLE IF NOT EXISTS taxon (
    taxon_id        INTEGER PRIMARY KEY,
    scientific_name TEXT,
    canonical_name  TEXT NOT NULL,
    rank            TEXT,
    status          TEXT,
    family          TEXT,
    genus           TEXT,
    accepted_id     INTEGER,
    occurs_de       INTEGER NOT NULL DEFAULT 0
);

-- Deliberately NOT unique: a taxonomic backbone contains homonyms, and the same
-- canonical name legitimately appears under several usage keys (accepted plus
-- synonyms). Uniqueness here crashes the ingest partway through.
CREATE INDEX IF NOT EXISTS idx_taxon_canonical ON taxon(canonical_name);

CREATE TABLE IF NOT EXISTS taxon_name (
    raw_name    TEXT    NOT NULL,
    source      TEXT    NOT NULL,
    taxon_id    INTEGER REFERENCES taxon(taxon_id),
    match_type  TEXT,
    confidence  INTEGER,
    PRIMARY KEY (raw_name, source)
);

CREATE TABLE IF NOT EXISTS trait (
    taxon_id     INTEGER NOT NULL REFERENCES taxon(taxon_id),
    trait_key    TEXT    NOT NULL,
    value_num    REAL,
    value_text   TEXT,
    unit         TEXT,
    source       TEXT    NOT NULL,
    license      TEXT    NOT NULL,
    confidence   REAL,
    retrieved_at TEXT    NOT NULL,
    PRIMARY KEY (taxon_id, trait_key, source)
);

CREATE INDEX IF NOT EXISTS idx_trait_key ON trait(trait_key);

CREATE TABLE IF NOT EXISTS interaction (
    taxon_id         INTEGER NOT NULL REFERENCES taxon(taxon_id),
    partner_name     TEXT    NOT NULL,
    partner_group    TEXT,
    interaction_type TEXT    NOT NULL,
    source           TEXT    NOT NULL,
    license          TEXT    NOT NULL,
    n_records        INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (taxon_id, partner_name, interaction_type, source)
);

CREATE INDEX IF NOT EXISTS idx_interaction_taxon ON interaction(taxon_id);

-- Insects actually recorded in Germany, from the same GBIF occurrence facet used
-- for the plants. GloBI's relations are worldwide; without this list a plant's
-- partner count ranks it by global research effort rather than garden value.
-- Keyed by canonical name, because that is what the GloBI intersection joins on.
-- The names come straight from GBIF's SCIENTIFIC_NAME occurrence facet (19 calls
-- for ~19k species, versus one detail request each), so no backbone key is
-- involved and inventing one would only add a column nothing reads.
CREATE TABLE IF NOT EXISTS insect_de (
    canonical_name  TEXT PRIMARY KEY,
    scientific_name TEXT,
    occurrences     INTEGER NOT NULL DEFAULT 0
);

-- A garden plan. `owner_id` is nullable and present from this first migration:
-- accounts are not being built (access is by share token), but adding the column
-- later would mean migrating live plans, and it costs one empty column now.
CREATE TABLE IF NOT EXISTS garden (
    garden_id   INTEGER PRIMARY KEY,
    share_token TEXT    NOT NULL UNIQUE,
    owner_id    TEXT,
    name        TEXT    NOT NULL,
    latitude    REAL    NOT NULL,
    longitude   REAL    NOT NULL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS bed (
    bed_id            INTEGER PRIMARY KEY,
    garden_id         INTEGER NOT NULL REFERENCES garden(garden_id) ON DELETE CASCADE,
    name              TEXT    NOT NULL,
    polygon           TEXT    NOT NULL,
    soil_type         TEXT,
    moisture          TEXT,
    ellenberg_l       REAL,
    ellenberg_m       REAL,
    ellenberg_n       REAL,
    ellenberg_r       REAL,
    sun_hours         REAL,
    light_computed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_bed_garden ON bed(garden_id);

CREATE TABLE IF NOT EXISTS obstacle (
    obstacle_id INTEGER PRIMARY KEY,
    garden_id   INTEGER NOT NULL REFERENCES garden(garden_id) ON DELETE CASCADE,
    kind        TEXT    NOT NULL,
    x           REAL    NOT NULL,
    y           REAL    NOT NULL,
    radius      REAL    NOT NULL,
    height      REAL    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_obstacle_garden ON obstacle(garden_id);

CREATE TABLE IF NOT EXISTS source_run (
    source      TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    rows        INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL,
    note        TEXT,
    PRIMARY KEY (source, started_at)
);
"""


def connect(
    path: str | Path = DEFAULT_DB_PATH, *, same_thread: bool = True
) -> sqlite3.Connection:
    """Open a connection with row access by column name and FK enforcement on.

    `same_thread=False` is for the read-only API, whose sync endpoints run in
    FastAPI's threadpool: a connection would otherwise be unusable in the thread
    that receives the next request. The ingest path keeps the guard, because it
    writes and a connection shared across writing threads corrupts.
    """
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create every table and index. Safe to call on an existing database."""
    conn.executescript(SCHEMA)
    conn.commit()
