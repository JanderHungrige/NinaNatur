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
    occurrences     INTEGER NOT NULL DEFAULT 0,
    -- bee / butterfly / hoverfly, or NULL for everything else. Beetles and wasps
    -- are real visitors; they simply are not in a named group, and dropping them
    -- would make the total disagree with the breakdown.
    insect_group    TEXT
);

CREATE INDEX IF NOT EXISTS idx_insect_group ON insect_de(insect_group);

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

-- What is actually growing in a bed. One row per species per bed, not per
-- individual plant: a timeline asking "does this bed have Salvia" must not have
-- to deduplicate first.
CREATE TABLE IF NOT EXISTS planting (
    planting_id INTEGER PRIMARY KEY,
    bed_id      INTEGER NOT NULL REFERENCES bed(bed_id) ON DELETE CASCADE,
    taxon_id    INTEGER NOT NULL REFERENCES taxon(taxon_id),
    quantity    INTEGER NOT NULL DEFAULT 1,
    added_at    TEXT    NOT NULL,
    UNIQUE (bed_id, taxon_id)
);

CREATE INDEX IF NOT EXISTS idx_planting_bed ON planting(bed_id);

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

-- Interaction counts per plant, computed once at ingest.
--
-- The 600k raw `interaction` rows are ingest-time data: the runtime only ever
-- asks "how many German partners does this plant have". Summarising them cuts
-- the shipped catalogue from 93 MB to 10 MB and turns a scan into a lookup.
CREATE TABLE IF NOT EXISTS partner_summary (
    taxon_id         INTEGER NOT NULL,
    interaction_type TEXT    NOT NULL,
    german           INTEGER NOT NULL,
    PRIMARY KEY (taxon_id, interaction_type)
);

-- Counts per insect group, so "1,055 partners" can become "40 wild bee species,
-- 12 butterflies" — a statement a gardener can act on.
CREATE TABLE IF NOT EXISTS partner_groups (
    taxon_id     INTEGER NOT NULL,
    insect_group TEXT    NOT NULL,
    german       INTEGER NOT NULL,
    PRIMARY KEY (taxon_id, insect_group)
);

CREATE TABLE IF NOT EXISTS partner_totals (
    taxon_id     INTEGER PRIMARY KEY,
    german       INTEGER NOT NULL,
    global_total INTEGER NOT NULL,
    unmatched    INTEGER NOT NULL
);

-- Which build of the shipped catalogue this database currently holds.
--
-- Seeding used to run only when there were no taxa at all, which stopped a newer
-- local ingest being overwritten — and also meant no catalogue improvement ever
-- reached an existing deployment. The insect group breakdown shipped and stayed
-- invisible in production for exactly that reason.
-- German names, so nobody has to know that Sal-Weide is Salix caprea.
--
-- `normalised` is stored rather than computed per query: a LIKE over a computed
-- expression cannot use an index, and this table is what every search touches.
CREATE TABLE IF NOT EXISTS vernacular_name (
    taxon_id     INTEGER NOT NULL REFERENCES taxon(taxon_id),
    name         TEXT    NOT NULL,
    normalised   TEXT    NOT NULL,
    is_preferred INTEGER NOT NULL DEFAULT 0,
    source       TEXT    NOT NULL,
    PRIMARY KEY (taxon_id, name)
);

CREATE INDEX IF NOT EXISTS idx_vernacular_normalised ON vernacular_name(normalised);

-- Wikipedia summaries, cached per deployment.
--
-- Deliberately NOT part of the shipped catalogue: this is derived, refreshable
-- and per-deployment — the same shape as a garden, not the same shape as plant
-- data. Baking it into the image would make it stale on the release cycle and
-- re-inflate something just trimmed to 13 MB.
CREATE TABLE IF NOT EXISTS species_info (
    taxon_id      INTEGER PRIMARY KEY REFERENCES taxon(taxon_id),
    title         TEXT,
    extract       TEXT,
    thumbnail_url TEXT,
    page_url      TEXT,
    language      TEXT,
    found         INTEGER NOT NULL,
    fetched_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS catalogue_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

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


# Columns added to tables that already existed in a shipped release.
#
# CREATE TABLE IF NOT EXISTS silently does nothing when the table is there, so a
# new column never reaches an existing database — including the production
# volume, where startup would then fail on the first statement referencing it.
# Additive migrations are all this project has needed; anything destructive
# should be a deliberate, reviewed script rather than an entry here.
COLUMN_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("insect_de", "insect_group", "TEXT"),
)


def _apply_column_migrations(conn: sqlite3.Connection) -> list[str]:
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


def init_schema(conn: sqlite3.Connection) -> list[str]:
    """Create every table and index, and add columns missing from older databases.

    Migrations run first: the schema script includes indexes over columns that an
    existing table may not have yet, and executescript would fail on those before
    reaching anything else.

    Returns the migrations applied, so a deployment can say what it changed.
    """
    applied = _apply_column_migrations(conn)
    conn.executescript(SCHEMA)
    conn.commit()
    return applied
