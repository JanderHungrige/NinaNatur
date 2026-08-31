"""The database schema, as one script.

Separated from the code that applies it so neither file has to be read to
understand the other: this one says what the tables are, `migrations.py`
says how a database that predates them catches up.
"""
from __future__ import annotations

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
    insect_group    TEXT,
    -- 'insect' or 'bird'. The table kept its name when birds arrived; this
    -- column, not the name, is what every read site must go by.
    clade           TEXT NOT NULL DEFAULT 'insect'
);

CREATE INDEX IF NOT EXISTS idx_insect_group ON insect_de(insect_group);
CREATE INDEX IF NOT EXISTS idx_insect_clade ON insect_de(clade);

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
    updated_at  TEXT    NOT NULL,
    -- Asked once, after the garden is made, and used as the starting point for
    -- every bed drawn afterwards. Null until somebody says: a default here
    -- would be a claim about a place nobody has described.
    soil_type   TEXT,
    moisture    TEXT
);

-- Everything drawn on the plan. Wave 11 merged `bed` and `obstacle`: being a
-- planting site is a property of an element, not a separate kind of thing, and
-- that is what lets the user draw a shape first and say what it is afterwards.
--
-- `width`, `depth` and `rotation` are gone. A rectangle is its four points like
-- any other outline, so a dragged vertex has nothing to convert; rotation is
-- applied to the points, and the float error over a hundred rotations is far
-- below the centimetre an outline is rounded to.
CREATE TABLE IF NOT EXISTS element (
    element_id  INTEGER PRIMARY KEY,
    garden_id   INTEGER NOT NULL REFERENCES garden(garden_id) ON DELETE CASCADE,
    kind        TEXT    NOT NULL,
    -- 'polygon' | 'circle' | 'line'.
    shape       TEXT    NOT NULL DEFAULT 'polygon',
    x           REAL    NOT NULL DEFAULT 0,
    y           REAL    NOT NULL DEFAULT 0,
    -- JSON [[x, y], ...] in metres relative to (x, y). The outline for a
    -- polygon, the centreline for a line, null for a circle.
    points      TEXT,
    -- A circle's diameter, or a line's band width. Null for a polygon.
    width       REAL,
    -- 'rect' when the four points are meant to stay square. Honoured by the
    -- editing tool and by nothing else: it is a promise about how handles
    -- behave, not a second geometry.
    constraint_hint TEXT,
    height      REAL,
    -- 'user' | 'osm_height' | 'osm_levels' | 'neighbourhood'.
    height_source TEXT NOT NULL DEFAULT 'user',
    label       TEXT,
    -- Below here: what a planting site needs. All null on a paving slab, and
    -- that is the point — one table, and being a bed is a property.
    name        TEXT,
    soil_type   TEXT,
    moisture    TEXT,
    ellenberg_l REAL,
    ellenberg_m REAL,
    ellenberg_n REAL,
    ellenberg_r REAL,
    sun_hours   REAL,
    light_computed_at TEXT,
    -- A raised bed stands above the low things around it; Wave 9's sightlines
    -- need the same number, which is why it is stored rather than derived.
    height_above_ground REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_element_garden ON element(garden_id);

-- What is actually growing in an element. One row per species per element, not
-- per individual plant: a timeline asking "does this bed have Salvia" must not
-- have to deduplicate first.
CREATE TABLE IF NOT EXISTS planting (
    planting_id INTEGER PRIMARY KEY,
    element_id  INTEGER NOT NULL REFERENCES element(element_id) ON DELETE CASCADE,
    -- Nullable since Wave 7: a plant the catalogue cannot name is still a plant
    -- in someone's garden. NULLs are distinct in SQLite, so the UNIQUE below
    -- still allows two unidentified roses in one bed, which is correct.
    taxon_id    INTEGER REFERENCES taxon(taxon_id),
    raw_name    TEXT,
    quantity    INTEGER NOT NULL DEFAULT 1,
    added_at    TEXT    NOT NULL,
    UNIQUE (element_id, taxon_id)
);

CREATE INDEX IF NOT EXISTS idx_planting_element ON planting(element_id);

-- What the gardener saw, as opposed to what the catalogue says.
--
-- Deliberately *not* a row in `trait`. The catalogue ships inside the image and
-- is re-synced at startup whenever the build stamps differ, so a user's value
-- there would be overwritten by the next deployment — and until it was, it
-- would change the suggestions of every other garden on the server. This is
-- user data and lives on the volume with the gardens.
CREATE TABLE IF NOT EXISTS observed_colour (
    garden_id INTEGER NOT NULL REFERENCES garden(garden_id) ON DELETE CASCADE,
    taxon_id  INTEGER NOT NULL REFERENCES taxon(taxon_id),
    colour    TEXT    NOT NULL,
    noted_at  TEXT    NOT NULL,
    PRIMARY KEY (garden_id, taxon_id)
);

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

-- German bird partners, counted separately and never folded into the insect
-- numbers. Its own table rather than a clade column on partner_summary: the
-- insect score's queries then keep working untouched, which is the difference
-- between adding a number and silently changing every score already shown.
CREATE TABLE IF NOT EXISTS partner_birds (
    taxon_id INTEGER PRIMARY KEY,
    german   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS partner_totals (
    taxon_id     INTEGER PRIMARY KEY,
    german       INTEGER NOT NULL,
    global_total INTEGER NOT NULL,
    unmatched    INTEGER NOT NULL
);

-- Wave 9. Accounts, with the email deliberately nullable: it is optional, and
-- the consequence (no password reset) is stated where the choice is made.
CREATE TABLE IF NOT EXISTS account (
    account_id    INTEGER PRIMARY KEY,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    email         TEXT,
    -- `scrypt$N$r$p$salt$hash`. The parameters travel with it so they can be
    -- raised later without locking anybody out.
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);

-- Sessions are stored as a *hash* of the token, never the token. A stolen
-- database is then a list of expired-looking strings rather than a drawer full
-- of usable logins — the same reasoning as the password column beside it.
CREATE TABLE IF NOT EXISTS session (
    token_hash TEXT    PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(account_id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    expires_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_account ON session(account_id);

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
