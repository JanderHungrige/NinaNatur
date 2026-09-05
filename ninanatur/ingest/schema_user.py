"""The tables that belong to the people using the site, not to the catalogue.

Split out of `schema.py` because the two have different lifecycles — and because
that file had reached the length limit, which was as good a moment as any to
draw the line the project already lives by.

Everything here is made by somebody using the site and lives on the volume.
Everything in `schema.py` is derived from static open sources, ships inside the
image, and is re-synced whenever the build stamp changes. Keeping both in one
file made it easy to stop noticing which was which, and that confusion is what
once produced a structurally perfect deployment answering "0 matching species"
to every request.
"""
from __future__ import annotations

USER_TABLES = """
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
    -- What shape the roof is, if anybody has said. OSM's `height` is the ridge,
    -- so a building without this is modelled as solid to the ridge — which is
    -- what every building was before Wave 16, and stays the default: one that
    -- quietly shortened them would move every existing garden's light without
    -- anybody asking for it.
    roof          TEXT NOT NULL DEFAULT 'unknown',
    -- Eaves height, where OSM carried `building:levels`. The one measured input
    -- in the roof model; everything else about a roof here is a shape ratio.
    eaves_m       REAL,
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
    -- Where the gardener dragged this cluster, relative to the bed's origin.
    -- Null until somebody moves it; the position is derived from the id until
    -- then, so an untouched garden still draws the same way twice.
    x           REAL,
    y           REAL,
    -- One row per species per bed, which makes a planting *be* a cluster.
    -- Adding the same species again raises the count rather than starting a
    -- second patch of it, which is what a gardener means by planting more.
    UNIQUE (element_id, taxon_id)
);

CREATE INDEX IF NOT EXISTS idx_planting_element ON planting(element_id);

-- Sun hours across the garden, cell by cell.
--
-- Derived, and stored anyway: it costs about half a second to produce and every
-- page that draws the map would otherwise produce it again. `signature` is a
-- hash of everything that moves a shadow — where the garden is, every
-- obstacle's outline and height, every planting's species and position — so
-- "is this stale" is a comparison rather than a judgement about which actions
-- ought to have invalidated it.
--
-- `hours` is a JSON array, row-major from the south-west corner. A table of
-- cells would be tidier and would also be six hundred rows per garden to write
-- on every recomputation.
CREATE TABLE IF NOT EXISTS light_grid (
    garden_id   INTEGER PRIMARY KEY REFERENCES garden(garden_id) ON DELETE CASCADE,
    cell_m      REAL    NOT NULL,
    min_x       REAL    NOT NULL,
    min_y       REAL    NOT NULL,
    cols        INTEGER NOT NULL,
    rows        INTEGER NOT NULL,
    hours       TEXT    NOT NULL,
    -- Of those hours, the ones before the sun crosses due south. Afternoon sun
    -- is hotter and harsher, and a total cannot say which four hours a spot
    -- gets — which is the difference between a morning-sun bed and a baking one.
    morning     TEXT    NOT NULL DEFAULT '[]',
    signature   TEXT    NOT NULL,
    computed_at TEXT    NOT NULL
);

-- What the gardener saw, as opposed to what the catalogue says.
--
-- Superseded in Wave 15 and kept empty rather than dropped.
--
-- Hand-entered colours are `trait` rows marked `manual` now — one general
-- database, as the gardener asked, with any published source outranking them.
-- `migrations.move_observed_colours` carried the existing rows across once.
--
-- The table stays because dropping it would take the only copy of those notes
-- with it if the move ever has to be re-examined, and an empty table costs
-- nothing. Nothing writes to it.
CREATE TABLE IF NOT EXISTS observed_colour (
    garden_id INTEGER NOT NULL REFERENCES garden(garden_id) ON DELETE CASCADE,
    taxon_id  INTEGER NOT NULL REFERENCES taxon(taxon_id),
    colour    TEXT    NOT NULL,
    noted_at  TEXT    NOT NULL,
    PRIMARY KEY (garden_id, taxon_id)
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

-- What somebody wrote in the feedback box, kept here as well as filed as a
-- GitHub issue.
--
-- The issue is where it gets acted on, but filing can fail — a missing token, a
-- rate limit, GitHub being down — and a bug report that vanishes because of any
-- of those is worse than one that arrives late. `issue_url` is null until it is
-- actually filed, which is also the list of what still needs sending.
--
-- `sender` is a salted hash of the caller's address, never the address itself:
-- it exists to count how many reports came from one place in an hour, and that
-- is the only question it can answer.
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('bug', 'idea')),
    answers     TEXT NOT NULL,
    version     TEXT,
    sender      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    issue_url   TEXT,
    filed_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);
"""
