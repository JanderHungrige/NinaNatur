-- The schema a fresh NinaNatur database had at a8faf57 (2026-09-28), the last
-- commit before doc 121 added columns. Dumped from sqlite_master by building
-- that commit's schema (git archive a8faf57 ninanatur; init_schema); never edit
-- it by hand. tests/test_schema_upgrade.py upgrades it with today's
-- init_schema and asks for exactly a fresh database's columns.

CREATE TABLE account (
    account_id    INTEGER PRIMARY KEY,
    username      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    email         TEXT,
    -- `scrypt$N$r$p$salt$hash`. The parameters travel with it so they can be
    -- raised later without locking anybody out.
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);

CREATE TABLE canopy_suggestion (
    suggestion_id INTEGER PRIMARY KEY,
    garden_id     INTEGER NOT NULL REFERENCES garden(garden_id) ON DELETE CASCADE,
    x             REAL    NOT NULL,
    y             REAL    NOT NULL,
    radius_m      REAL    NOT NULL,
    height_m      REAL    NOT NULL,
    dismissed     INTEGER NOT NULL DEFAULT 0,
    accepted_id   INTEGER,
    found_at      TEXT    NOT NULL
);

CREATE TABLE catalogue_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE cloud_window (
    place_key       TEXT    PRIMARY KEY,
    cell_m          REAL    NOT NULL,
    cols            INTEGER NOT NULL,
    rows            INTEGER NOT NULL,
    base_m          REAL    NOT NULL,
    ground_cm       BLOB    NOT NULL,
    surface_cm      BLOB    NOT NULL,
    -- Above the ground rather than above sea level: it is a property of the
    -- tree, not of the hill it stands on.
    crown_base_cm   BLOB    NOT NULL,
    source          TEXT    NOT NULL,
    licence         TEXT    NOT NULL,
    attribution     TEXT    NOT NULL,
    -- What the answer is worth: at four points a square metre a half-metre
    -- cell is one measurement, and the window says which it had.
    points_per_m2   REAL    NOT NULL,
    fetched_at      TEXT    NOT NULL
);

CREATE TABLE element (
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
    -- Where the roof shape came from, kept apart from where the height came
    -- from. They arrive together from a 3D building model and separately from
    -- everywhere else: somebody can look out of the window and know the shape
    -- without knowing the height, and a later refresh must not overwrite that.
    -- 'user' | 'surveyed' | 'osm'. The default is the gardener, and every
    -- writer that is not says so.
    roof_source   TEXT NOT NULL DEFAULT 'user',
    -- What shape the roof is, if anybody has said. OSM's `height` is the ridge,
    -- so a building without this is modelled as solid to the ridge — which is
    -- what every building was before Wave 16, and stays the default: one that
    -- quietly shortened them would move every existing garden's light without
    -- anybody asking for it.
    roof          TEXT NOT NULL DEFAULT 'unknown',
    -- Eaves height: from the state's survey, from `building:levels`, or typed.
    -- Null is "nobody has said", and the model then puts the eaves at three
    -- quarters of the ridge.
    eaves_m       REAL,
    -- Who gave the eaves: 'user' | 'surveyed' | 'osm_levels'. Null exactly when
    -- nobody did — or, for a value stored before Wave 21 whose origin the
    -- history cannot tell, until the next recompute says (doc 93).
    eaves_source  TEXT,
    -- Whose outline this is: 'osm' for the streets and houses a garden made from
    -- the map brought with it; null for what the gardener drew. Written by the
    -- server only, and never changed: a reshaped OSM outline is still derived
    -- from OSM, and ODbL asks for the credit wherever it is shown (2026-09-21).
    outline_source TEXT,
    -- The bearing the roof falls towards, from the survey's faces (doc 94): in
    -- [0, 180) for a gable or hip, whose ridge runs at right angles to it, and
    -- in [0, 360) for a pent. Null: not surveyed, and the ridge is assumed to
    -- run along the long side.
    roof_fall_deg REAL,
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
    -- How the ground under this bed falls, in degrees, and the compass
    -- direction it climbs. Named on the page rather than folded into the light
    -- score: a 17° slope at 52°N moves the sun *hours* by a fifth of an hour
    -- while changing the energy per square metre a great deal, and this model
    -- counts hours. Scoring it would be a claim the model cannot support.
    slope_deg   REAL,
    aspect_deg  REAL,
    -- Wave 26, feature 3 (doc 118): the share of the sky the bed sees (crowns
    -- in leaf), its relative illuminance — its light, sun and sky, as a share
    -- of open ground's in its climate — and the sunshine it can expect.
    sky_view    REAL,
    relative_light REAL,
    expected_sun_h REAL,
    light_computed_at TEXT,
    -- A raised bed stands above the low things around it; Wave 9's sightlines
    -- need the same number, which is why it is stored rather than derived.
    height_above_ground REAL NOT NULL DEFAULT 0
);

CREATE TABLE feedback (
    feedback_id INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('bug', 'idea')),
    answers     TEXT NOT NULL,
    version     TEXT,
    sender      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    issue_url   TEXT,
    filed_at    TEXT
);

CREATE TABLE garden (
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

CREATE TABLE garden_landcover (
    garden_id  INTEGER PRIMARY KEY REFERENCES garden(garden_id) ON DELETE CASCADE,
    areas      TEXT    NOT NULL,
    placed_by  TEXT    NOT NULL,
    fetched_at TEXT    NOT NULL
);

CREATE TABLE insect_de (
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

CREATE TABLE interaction (
    taxon_id         INTEGER NOT NULL REFERENCES taxon(taxon_id),
    partner_name     TEXT    NOT NULL,
    partner_group    TEXT,
    interaction_type TEXT    NOT NULL,
    source           TEXT    NOT NULL,
    license          TEXT    NOT NULL,
    n_records        INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (taxon_id, partner_name, interaction_type, source)
);

CREATE TABLE light_grid (
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
    -- Which cells are a roof rather than ground. A house's own footprint gets
    -- no sun at all — it is under a building — so the cell is answered on the
    -- roof instead, at its own height and its own pitch. That is a real answer
    -- to a different question, so it is flagged: it must not reach a bed's mean
    -- or the garden's brightest point, and the reader is told which they are
    -- looking at. Empty on a grid computed before roofs were.
    roof        TEXT    NOT NULL DEFAULT '[]',
    -- The light model that computed it (Wave 26); empty before models had a
    -- version, so an old map says it was drawn by the model before them.
    model       TEXT    NOT NULL DEFAULT '',
    -- Wave 26, feature 3 (doc 118), in step with hours: the sky each cell
    -- sees, its relative illuminance, and the sunshine it can expect. Empty on
    -- a map computed before.
    sky         TEXT    NOT NULL DEFAULT '[]',
    relative    TEXT    NOT NULL DEFAULT '[]',
    expected    TEXT    NOT NULL DEFAULT '[]',
    signature   TEXT    NOT NULL,
    computed_at TEXT    NOT NULL
);

CREATE TABLE observed_colour (
    garden_id INTEGER NOT NULL REFERENCES garden(garden_id) ON DELETE CASCADE,
    taxon_id  INTEGER NOT NULL REFERENCES taxon(taxon_id),
    colour    TEXT    NOT NULL,
    noted_at  TEXT    NOT NULL,
    PRIMARY KEY (garden_id, taxon_id)
);

CREATE TABLE partner_birds (
    taxon_id INTEGER PRIMARY KEY,
    german   INTEGER NOT NULL
);

CREATE TABLE partner_groups (
    taxon_id     INTEGER NOT NULL,
    insect_group TEXT    NOT NULL,
    german       INTEGER NOT NULL,
    PRIMARY KEY (taxon_id, insect_group)
);

CREATE TABLE partner_summary (
    taxon_id         INTEGER NOT NULL,
    interaction_type TEXT    NOT NULL,
    german           INTEGER NOT NULL,
    PRIMARY KEY (taxon_id, interaction_type)
);

CREATE TABLE partner_totals (
    taxon_id     INTEGER PRIMARY KEY,
    german       INTEGER NOT NULL,
    global_total INTEGER NOT NULL,
    unmatched    INTEGER NOT NULL
);

CREATE TABLE planting (
    planting_id INTEGER PRIMARY KEY,
    element_id  INTEGER NOT NULL REFERENCES element(element_id) ON DELETE CASCADE,
    -- Nullable since Wave 7: a plant the catalogue cannot name is still a plant
    -- in someone's garden. NULLs are distinct in SQLite, so the UNIQUE below
    -- still allows two unidentified roses in one bed, which is correct.
    taxon_id    INTEGER REFERENCES taxon(taxon_id),
    raw_name    TEXT,
    quantity    INTEGER NOT NULL DEFAULT 1,
    added_at    TEXT    NOT NULL,
    -- Where the gardener dragged this cluster, in garden metres.
    -- Null until somebody moves it; the position is derived from the id until
    -- then, so an untouched garden still draws the same way twice.
    x           REAL,
    y           REAL,
    -- One row per species per bed, which makes a planting *be* a cluster.
    -- Adding the same species again raises the count rather than starting a
    -- second patch of it, which is what a gardener means by planting more.
    UNIQUE (element_id, taxon_id)
);

CREATE TABLE rate_limit (
    bucket TEXT NOT NULL,
    client TEXT NOT NULL,
    at     REAL NOT NULL
);

CREATE TABLE session (
    token_hash TEXT    PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES account(account_id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    expires_at TEXT    NOT NULL
);

CREATE TABLE source_run (
    source      TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    rows        INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL,
    note        TEXT,
    PRIMARY KEY (source, started_at)
);

CREATE TABLE species_info (
    taxon_id      INTEGER PRIMARY KEY REFERENCES taxon(taxon_id),
    title         TEXT,
    extract       TEXT,
    thumbnail_url TEXT,
    page_url      TEXT,
    language      TEXT,
    found         INTEGER NOT NULL,
    fetched_at    TEXT    NOT NULL
);

CREATE TABLE taxon (
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

CREATE TABLE taxon_name (
    raw_name    TEXT    NOT NULL,
    source      TEXT    NOT NULL,
    taxon_id    INTEGER REFERENCES taxon(taxon_id),
    match_type  TEXT,
    confidence  INTEGER,
    PRIMARY KEY (raw_name, source)
);

CREATE TABLE terrain_horizon (
    place_key  TEXT PRIMARY KEY,
    angles     TEXT NOT NULL,
    source     TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);

CREATE TABLE terrain_window (
    place_key       TEXT    PRIMARY KEY,
    min_x           REAL    NOT NULL,
    min_y           REAL    NOT NULL,
    cell_m          REAL    NOT NULL,
    cols            INTEGER NOT NULL,
    rows            INTEGER NOT NULL,
    base_m          REAL    NOT NULL,
    heights_cm      BLOB    NOT NULL,
    source          TEXT    NOT NULL,
    licence         TEXT    NOT NULL,
    attribution     TEXT    NOT NULL,
    -- 0.01 for a DGM1, 1.0 for Baden-Württemberg's INSPIRE coverage. A page
    -- that does not say so is claiming precision it was not given.
    vertical_step_m REAL    NOT NULL,
    fetched_at      TEXT    NOT NULL
);

CREATE TABLE trait (
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

CREATE TABLE vernacular_name (
    taxon_id     INTEGER NOT NULL REFERENCES taxon(taxon_id),
    name         TEXT    NOT NULL,
    normalised   TEXT    NOT NULL,
    is_preferred INTEGER NOT NULL DEFAULT 0,
    source       TEXT    NOT NULL,
    PRIMARY KEY (taxon_id, name)
);

CREATE INDEX idx_canopy_garden ON canopy_suggestion(garden_id);

CREATE INDEX idx_element_garden ON element(garden_id);

CREATE INDEX idx_feedback_created ON feedback(created_at);

CREATE INDEX idx_insect_clade ON insect_de(clade);

CREATE INDEX idx_insect_group ON insect_de(insect_group);

CREATE INDEX idx_interaction_taxon ON interaction(taxon_id);

CREATE INDEX idx_planting_element ON planting(element_id);

CREATE INDEX idx_session_account ON session(account_id);

CREATE INDEX idx_taxon_canonical ON taxon(canonical_name);

CREATE INDEX idx_trait_key ON trait(trait_key);

CREATE INDEX idx_vernacular_normalised ON vernacular_name(normalised);

CREATE INDEX rate_limit_lookup ON rate_limit (bucket, client, at);
