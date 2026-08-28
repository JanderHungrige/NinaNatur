---
id: 08-garden-model
title: Garden, Bed and Obstacle Model
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-3
wave_status: complete
depends_on: [07-solar-geometry]
relates: [09-garden-api]
source_files:
  - ninanatur/garden/__init__.py
  - ninanatur/garden/models.py
  - ninanatur/garden/store.py
  - ninanatur/garden/soil.py
  - ninanatur/ingest/db.py
routes: []
models:
  - garden
  - bed
  - obstacle
test_files:
  - tests/test_garden_store.py
  - tests/test_soil.py
data_flow: mixed
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [garden, persistence, share-token, soil, ellenberg]
path: Garden/Model
integration_contracts:
  - function: create_garden(conn, ...)
    when: any garden is created
    note: the share token is the only access control — it must come from `secrets`, never a sequence or a timestamp
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 08 — Garden, Bed and Obstacle Model

## Purpose

Persist a garden plan: where it is, what beds it has, what casts shadows on them,
and what each bed's derived site vector is.

## Data Model

**garden**
`garden_id INTEGER PK, share_token TEXT UNIQUE NOT NULL, owner_id TEXT NULL,
 name TEXT NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL`

**bed**
`bed_id INTEGER PK, garden_id INTEGER FK, name TEXT NOT NULL, polygon TEXT NOT NULL,
 soil_type TEXT, moisture TEXT,
 ellenberg_l REAL, ellenberg_m REAL, ellenberg_n REAL, ellenberg_r REAL,
 sun_hours REAL, light_computed_at TEXT`

**obstacle**
`obstacle_id INTEGER PK, garden_id INTEGER FK, kind TEXT NOT NULL,
 x REAL, y REAL, radius REAL NOT NULL, height REAL NOT NULL`

### Two decisions worth stating

**`owner_id` is nullable and present from this first migration.** Accounts are
not being built — access is by share token. But adding the column later would
mean migrating live plans, and it costs one empty column now. This is the
initiative decision made concrete.

**The share token is the capability.** Anyone holding it can edit the garden, so
it is generated with `secrets.token_urlsafe`, never from a sequence, a timestamp,
or a hash of the name. A guessable token is not a weaker lock, it is no lock.

## Soil as gardeners describe it

The user never sees an Ellenberg number. They pick from what they can observe,
and the mapping lives in one table:

| Soil type | R (reaction) | N (nutrients) |
|---|---|---|
| sand | 4.0 | 2.5 |
| loam | 6.5 | 5.5 |
| clay | 7.0 | 6.0 |
| humus | 6.0 | 7.5 |

| Moisture | M |
|---|---|
| dry | 2.5 |
| fresh | 5.0 |
| moist | 7.0 |
| wet | 8.5 |

Like the sun-hours mapping, this is a **convention** — a stated starting point
that can be argued with, not a measurement.

## Business Rules

- **Light is computed on save, not per request.** Sampling a season for several
  beds is far too slow to repeat on every page load. `light_computed_at` records
  when, so a stale value is detectable rather than invisible.
- **A bed's site vector is stored alongside the inputs it came from.** A light
  value must be traceable to the obstacles that produced it.
- **A garden always has a location**, because without one there is no sun path.
  It is rounded to 0.1° by the `Location` type before it is ever stored.
- **Deleting a garden deletes its beds and obstacles.** Foreign keys are declared
  `ON DELETE CASCADE` and enforcement is already on in `connect()`.
- **Polygons are stored as JSON**, validated on the way in. SQLite has no
  geometry type and this project does not need one.

## Security

The share token is the entire access-control model, so its generation is the
security-critical line in this feature. Every query is parameterised; polygon
JSON is parsed, never evaluated.

Storing a garden's location is the only personal data here, and it is
deliberately coarse — 0.1° is about 11 km.

## Known Issues

- A bed's light is computed at its polygon centroid, so a long bed running past a
  wall is partly shaded in reality and uniformly scored here. Carried over from
  `07-solar-geometry`; sampling several points per polygon is the upgrade.
- `recompute_light` walks every bed even when only one obstacle moved. Fine at
  ~4 ms per bed, worth revisiting if gardens get large.

## Bugs

(none yet)
