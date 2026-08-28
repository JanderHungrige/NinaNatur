---
id: 12-planting-model
title: Plantings — What Is Actually In a Bed
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-4
wave_status: complete
depends_on: [08-garden-model]
relates: [13-bed-suggestions, 14-bloom-timeline]
source_files:
  - ninanatur/garden/models.py
  - ninanatur/garden/store.py
  - ninanatur/api/gardens.py
  - ninanatur/api/schemas.py
  - ninanatur/ingest/db.py
routes:
  - POST /api/v1/gardens/{token}/beds/{bed_id}/plantings
  - DELETE /api/v1/gardens/{token}/plantings/{planting_id}
models:
  - planting
test_files:
  - tests/test_plantings.py
data_flow: writes-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [planting, garden, persistence, cascade]
path: Garden/Plantings
integration_contracts:
  - function: add_planting(conn, bed_id, taxon_id, quantity)
    when: a species is placed in a bed
    note: must reject a taxon that is not in the catalogue — a planting pointing at nothing would break every downstream calculation silently
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 12 — Plantings: What Is Actually In a Bed

## Purpose

Link a bed to the species growing in it. Until now a bed carried site conditions
and nothing else, so there was no data a bloom timeline could be drawn from —
this is the missing edge, found while planning Wave 4 rather than while building
it.

## Data Model

**planting**
`planting_id INTEGER PK, bed_id INTEGER FK -> bed ON DELETE CASCADE,
 taxon_id INTEGER FK -> taxon, quantity INTEGER NOT NULL DEFAULT 1,
 added_at TEXT NOT NULL, UNIQUE (bed_id, taxon_id)`

**One row per species per bed, not per individual plant.** Quantity is a number
on the row. Planting the same species twice raises the count rather than creating
a duplicate, because a timeline asking "does this bed have Salvia" must not have
to deduplicate first.

## Business Rules

- **A planting must reference a real taxon.** An unknown `taxon_id` is rejected
  with a `ValueError` → 422. A dangling reference would leave the timeline
  silently short a species rather than failing visibly.
- **Cascade is transitive and must be proven.** Deleting a garden removes its
  beds, and removing a bed must remove its plantings. SQLite only does this with
  `PRAGMA foreign_keys = ON`, which `connect()` sets — so the test asserts the
  whole chain rather than trusting the declaration.
- **Quantity is at least 1.** Zero would be a deletion expressed as an update,
  and the two would then disagree about whether the species is in the bed.
- **Plantings do not affect the light computation.** Beds are shaded by
  obstacles, not by each other — modelling plant-on-plant shading is a different
  and much larger problem, deliberately not started here.

## Security

The share token still governs access; a planting is reached through its garden,
never by a bare id. `taxon_id` is validated against the catalogue before use.

## Known Issues

- Plantings have no position within a bed — a bed is treated as one patch. Fine
  for a bloom timeline, but a layout view would need coordinates per planting.

## Bugs

(none yet)
