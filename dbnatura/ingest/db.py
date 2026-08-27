"""SQLite schema and connection handling.

One module owns the schema. Every other module receives an open connection —
nothing else opens a database or issues DDL.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("data/dbnatura.sqlite")

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


def connect(path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a connection with row access by column name and FK enforcement on."""
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create every table and index. Safe to call on an existing database."""
    conn.executescript(SCHEMA)
    conn.commit()
