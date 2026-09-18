"""What is computed about a garden and kept: its light, its ground, its horizon,
and the trees a survey found that nobody has drawn yet.

These live on the volume beside the gardens, but nobody types them: each is
derived from a garden and a public source, stored because producing it again
costs a request or a second, and safe to throw away — the next recompute makes
it again. Split from `schema_user.py` in Wave 21.
"""
from __future__ import annotations

COMPUTED_TABLES = """
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
    -- Which cells are a roof rather than ground. A house's own footprint gets
    -- no sun at all — it is under a building — so the cell is answered on the
    -- roof instead, at its own height and its own pitch. That is a real answer
    -- to a different question, so it is flagged: it must not reach a bed's mean
    -- or the garden's brightest point, and the reader is told which they are
    -- looking at. Empty on a grid computed before roofs were.
    roof        TEXT    NOT NULL DEFAULT '[]',
    signature   TEXT    NOT NULL,
    computed_at TEXT    NOT NULL
);

-- The ground under a garden, fetched once from a state survey.
--
-- Keyed by LOCATION rather than by garden: terrain does not change, and two
-- gardens in the same street stand on the same ground. That is less storage and
-- far fewer requests against services nobody is paying us to use.
--
-- Heights are centimetres above this window's own minimum, as a deflated block
-- of 16-bit integers. As JSON text the same 200x200 window is 202 KB — larger
-- than the GeoTIFF it came from, which rather defeats the point; as a blob it
-- is about 25 KB. Provenance travels with them for the same reason it travels
-- with every trait value: the page has to be able to say where a number came
-- from and how good it is.
CREATE TABLE IF NOT EXISTS terrain_window (
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

-- How high the land stands around a place, one entry per degree of azimuth.
--
-- Its own table rather than a column on terrain_window: the two are fetched
-- separately, at different scales, and either can exist without the other. A
-- shared row would mean saving one silently wiping the other.
--
-- 360 numbers, about two kilobytes, from five kilometres of terrain that is
-- measured and thrown away.
CREATE TABLE IF NOT EXISTS terrain_horizon (
    place_key  TEXT PRIMARY KEY,
    angles     TEXT NOT NULL,
    source     TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);

-- Trees the surface model found and nobody has drawn.
--
-- Suggestions, never objects. A crown, a hedge, a marquee and a badly-mapped
-- building all read as "tall, and not ground" to a laser, so this proposes and
-- the gardener decides — the same standing as Wave 16's misplacement warning.
--
-- `dismissed` rather than a delete: a suggestion refused once must not come
-- back on the next recomputation, and the only way to know that is to remember
-- the refusal.
CREATE TABLE IF NOT EXISTS canopy_suggestion (
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

CREATE INDEX IF NOT EXISTS idx_canopy_garden ON canopy_suggestion(garden_id);
"""
