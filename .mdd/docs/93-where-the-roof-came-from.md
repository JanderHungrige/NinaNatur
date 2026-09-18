---
id: 93-where-the-roof-came-from
title: Where the Roof Came From
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-21
wave_status: active
depends_on: [82-the-roof-it-actually-has, 83-measured-surveyed-or-assumed]
relates: [81-a-house-with-a-measured-height, 82-the-roof-it-actually-has, 83-measured-surveyed-or-assumed, 88-what-the-selection-shows]
source_files:
  - ninanatur/garden/measured.py
  - ninanatur/garden/overlap.py
  - ninanatur/garden/models.py
  - ninanatur/garden/elements.py
  - ninanatur/garden/store.py
  - ninanatur/garden/element_edits.py
  - ninanatur/api/elements.py
  - ninanatur/api/geo.py
  - ninanatur/api/gardens.py
  - ninanatur/api/schemas.py
  - ninanatur/api/schemas_garden_in.py
  - ninanatur/api/schemas_plants.py
  - ninanatur/api/schemas_map.py
  - ninanatur/api/schemas_accounts.py
  - ninanatur/ingest/migrations.py
  - ninanatur/ingest/one_time.py
  - ninanatur/ingest/db.py
  - ninanatur/ingest/schema.py
  - ninanatur/ingest/schema_user.py
  - ninanatur/ingest/schema_computed.py
  - frontend/src/heights.ts
  - frontend/src/roofs.ts
  - frontend/src/garden/selection.ts
  - frontend/src/components/ElementForm.tsx
  - frontend/src/api/types.ts
  - frontend/src/testing/gardens.ts
routes:
  - PATCH /api/v1/gardens/{token}/obstacles/{obstacle_id}
  - POST /api/v1/gardens/from-map
  - GET /api/v1/gardens/{token}
models: [element]
test_files:
  - tests/test_roof_provenance.py
  - tests/test_roof_provenance_backfill.py
  - tests/test_kind_vocabulary.py
  - frontend/src/components/ElementForm.test.tsx
  - frontend/src/heights.test.ts
  - frontend/src/garden/selection.test.ts
data_flow: .mdd/audits/flow-where-the-roof-came-from-2026-09-18.md
last_synced: 2026-09-18
status: in_progress
phase: 6
mdd_version: 11
tags: [provenance, roofs, eaves, lod2, osm, element-form, migrations]
path: Map/Buildings
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# 93 — Where the Roof Came From

## Purpose

Feature 1 of Wave 21. A house's roof is three numbers and a word — ridge height,
eaves height, pitch, shape — and each of them came from somewhere: the state's
survey, OpenStreetMap, the storey count, the gardener, or nowhere at all. Wave 19
labelled the height. This labels the rest, and makes the gardener's word win
value by value rather than building by building.

## What was wrong (measured 2026-09-18)

| # | Found | Where |
|---|---|---|
| 1 | An eaves height from the survey, from `building:levels`, typed in, or the ¾ assumption look the same on the page. Nothing records which. | `element` has no column for it |
| 2 | The form sends every pre-filled field on save. The PATCH marks a height the user's whenever `height` is in the body — so renaming a surveyed house turns its "amtlich vermessen" into an entry, and no refresh measures it again. | `ElementForm.save`, `api/elements.py` |
| 3 | A roof shape picked in the form never marks `roof_source`, and the survey's UPDATE checks only `height_source`. Doc 83 promises a refresh never overwrites a shape somebody chose; it held only because of 2. | `measured.apply` |
| 4 | An imported house's `roof:shape` is stored with `roof_source = 'user'`, the column default: OpenStreetMap's word recorded as the gardener's. | `api/geo.py` |
| 5 | A client may send `height_source` itself, and so call its own number `surveyed`. | `ObstacleUpdate` |

## Architecture

```
survey (LoD2) ─┐                        ┌─ height  + height_source  (Wave 19)
OSM import ────┼──► element row ────────┼─ roof    + roof_source    (Wave 19, now honoured)
form (PATCH) ──┘                        └─ eaves_m + eaves_source   (new)
                                              │
                          ObstacleOut ◄───────┘ ──► ElementForm notes
```

The server alone writes a `*_source`. The API sets it from what changed; the
survey sets it when it writes; the import sets it when it creates. A client
never names a source.

## Data Model

`element.eaves_source TEXT` — add-only migration, null on every existing row
until the backfill below.

| Column | Values | Meaning of null |
|---|---|---|
| `height_source` | `user` · `surveyed` · `measured` · `osm_height` · `osm_levels` · `neighbourhood` | — (not null) |
| `roof_source` | `user` · `surveyed` · **`osm`** (new value) | — (not null, default `user`) |
| `eaves_source` | `user` · `surveyed` · `osm_levels` | nobody has said: the model puts the eaves at ¾ of the ridge |

`eaves_source` is null exactly when nobody has given the eaves — with one
exception, below: a legacy value whose origin cannot be told apart keeps a null
source beside a number until the next recompute.

### The backfill, once (`wave_21_roof_provenance` in `catalogue_meta`)

Only what the history makes certain. The facts it rests on: until now the form
always sent the pre-filled height, so **any row somebody saved has
`height_source = 'user'`**; the survey writes roof, `roof_source` and eaves
together; the raster never writes a roof or eaves; the import is the only other
writer of eaves.

| Rows | Becomes | Because |
|---|---|---|
| `roof_source = 'surveyed'` and `height_source = 'user'` | `roof_source = 'user'` | saved after the survey: the shape may be theirs, and under-claiming is the safe error |
| house or shed, `roof_source = 'user'`, `height_source != 'user'` | `roof_source = 'osm'` | never saved: the shape came with the import |
| `eaves_m` set, `height_source = 'user'` | `eaves_source = 'user'` | saved: typed or accepted |
| `eaves_m` set, `height_source != 'user'`, `roof_source != 'surveyed'` | `eaves_source = 'osm_levels'` | never saved, never surveyed: only the import wrote it |
| `eaves_m` set, survey-written roof | stays null | the survey's eaves or the import's that the survey kept — the next recompute says |

## API Endpoints

- `PATCH /api/v1/gardens/{token}/obstacles/{obstacle_id}` — unchanged body,
  minus `height_source`, which the server now ignores. The server marks:
  - `height` given → `height_source = 'user'` (as before);
  - `roof` given → `roof_source = 'user'`;
  - `eaves_m` given → `eaves_source = 'user'`, or null when `eaves_m` is null
    ("nobody has said" again, so the next refresh may answer).
- `POST /api/v1/gardens/from-map` — an imported house is `roof_source = 'osm'`,
  and its eaves `eaves_source = 'osm_levels'` where `building:levels` gave them.
- `GET /api/v1/gardens/{token}` and every response carrying a garden —
  `ObstacleOut` gains `roof_source: str` and `eaves_source: str | null`.

## Business Rules

1. **The gardener outranks the survey, per value.** The survey skips a building
   whose *height* is the user's (Wave 19, unchanged). Where it measures, it
   writes the shape unless `roof_source = 'user'` and the shape is not
   `unknown`, and the eaves unless `eaves_source = 'user'`.
2. **"Weiß nicht" is nobody's answer.** A roof the user set to `unknown` is
   theirs to leave open, and the survey may fill it. An eaves box emptied is the
   same.
3. **A survey without eaves leaves them alone.** No eaves in the survey keeps the
   stored value and its source — the `COALESCE` rule, now with its source.
4. **Only what changed is sent.** The form sends `kind` and `label` always (the
   toast names the kind) and `height`, `roof`, `eaves_m` only when they differ
   from what the form opened with.
5. **The page says it.** Under the roof shape: `amtlich vermessen` or `aus
   OpenStreetMap`. Under the eaves: `amtlich vermessen`, `aus der Geschosszahl
   geschätzt`, `Herkunft nicht vermerkt` (legacy), or — with no eaves — `Nicht
   bekannt: gerechnet wird mit drei Vierteln der Firsthöhe, 6,8 m`. The user's
   own entry says nothing, as heights already do (`heights.ts`). A note belongs
   to the stored value: once the field is changed, it disappears.
6. **One fraction.** The ¾ lives in `roofs.DEFAULT_EAVES_FRACTION`; the frontend
   mirrors it in `roofs.ts`, and the existing roof guard test compares them.

## Data Flow

See the audit. In short: the survey (`lod2._one` → `measured.apply`), the import
(`surroundings` → `api/geo.py` → `store.add_obstacle`) and the form (PATCH →
`api/elements.py` → `update_obstacle`) are the three writers; `to_out` carries
all three sources; `selection.formValues` hands them to `ElementForm`, which
turns them into words through `heights.ts`.

## Housekeeping in the same branch

Four files this feature must touch were already over the 300-line limit, and the
hook refuses edits to them: `api/schemas.py` (735), `garden/store.py` (380),
`ingest/migrations.py` (315), `ingest/schema_user.py` (310). They are split by
concern first, in a commit that changes no behaviour, with every old import still
working:

| From | To |
|---|---|
| `api/schemas.py` | `schemas_plants.py` (catalogue), `schemas_garden_in.py` (what a caller sends), `schemas_map.py`, `schemas_accounts.py`; `schemas.py` keeps the garden's answers and re-exports the rest |
| `garden/store.py` | `element_edits.py` (updating elements and the garden's soil) |
| `ingest/migrations.py` | `one_time.py` (the once-only data migrations, marked in `catalogue_meta`) |
| `ingest/schema_user.py` | `schema_computed.py` (light grid, terrain, canopy — what is computed about a garden and kept) |
| `garden/measured.py` (297) | `overlap.py` (how much of one outline another covers), so the per-value guard fits |

Every importer points at the new home directly; nothing is re-exported. Two
existing tests changed their setup, not their assertions:
`test_sightlines_api.py` gave a house a guessed height through the PATCH, which
no longer takes a source, and now writes it the way the import does;
`test_measure_is_bounded.py` counts polygon tests in `overlap` rather than in
`measured`.

## Dependencies

- 82 — the survey's eaves (`Lod2Building.eaves_m`).
- 83 — the matching and `apply`, whose guard this refines.

## Security

Input boundary: the PATCH body. The change narrows it — `height_source` is no
longer read from the client, and the two new sources are never accepted from it.
No new endpoint, no new external call. The backfill writes only provenance
columns, runs once, and is marked before it can run twice.

## Known Issues

- `roofs.ts` has said since Wave 16 that a pytest guard held its list to the
  server's. Nothing did — the only check compared two Python lists — so the
  guard written here (`test_kind_vocabulary.py`) passed on its first run: the
  lists had not drifted. It is the guard, not a fix.

- A house drawn from the palette carries `height_source = 'user'` with the
  palette's default height, so the survey never measures a hand-drawn house.
  Pre-existing (Wave 19), and a separate question: whether the palette's default
  counts as somebody's word.
- Legacy eaves on survey-written rows keep a null source until the garden's
  light is next recomputed.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
