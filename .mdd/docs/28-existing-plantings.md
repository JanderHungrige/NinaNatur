---
id: 28-existing-plantings
title: What Already Grows There
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-7
wave_status: complete
depends_on: [27-object-labelling]
relates: [21-german-names, 18-insect-score]
source_files:
  - ninanatur/ingest/db.py
  - ninanatur/garden/store.py
  - ninanatur/garden/models.py
  - ninanatur/data/names.py
  - ninanatur/api/schemas.py
  - ninanatur/api/planning.py
  - frontend/src/components/ExistingPlanting.tsx
routes:
  - POST /api/v1/gardens/{token}/beds/{bed_id}/plantings
models:
  - planting
test_files:
  - tests/test_existing_plantings.py
  - tests/test_migrations.py
  - frontend/src/components/ExistingPlanting.test.tsx
data_flow: writes-existing
last_synced: 2026-08-29
status: complete
phase: all
mdd_version: 11
tags: [plantings, name-resolution, unmatched, german-names, inventory]
path: Garden/Plantings
integration_contracts:
  - function: search_names(conn, query)
    when: a user types a plant they already have
    note: Wave 6's index resolves German and scientific names; an unresolved name is kept, never discarded
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 28 — What Already Grows There

## Purpose

A garden is not empty when someone starts planning it. Until now the only way
into a bed was picking a species from our suggestions, which quietly assumes the
user is starting from bare soil and that we already know every plant they own.

## The rule that shapes this: an unmatched name is kept

Names resolve against the catalogue — German or scientific, through Wave 6's
index. A match feeds the insect score and the bloom timeline exactly like a
planned planting.

**A name we cannot resolve is stored anyway**, marked as not-yet-identified.
Discarding it would tell someone their garden is wrong because our catalogue is
incomplete. The catalogue holds 8,939 German species and no cultivars at all, so
"Bauernhortensie" and "Apfelbaum, Sorte weiß ich nicht" are ordinary answers, not
mistakes.

An unidentified planting:

- appears on the plan and in the bed, as the user's own record;
- is **counted and reported** — "3 Pflanzungen noch nicht zugeordnet" — so the
  score's coverage is visible rather than quietly optimistic;
- contributes **nothing** to the insect score or the timeline, because we have
  no data for it. It does not contribute zero either: those are different facts
  and the UI says which.

## Data Model

`planting.taxon_id` becomes nullable and `planting.raw_name` is added.

- A resolved planting has both: the taxon it matched and the words the user
  typed. Keeping the raw name is not sentiment — it is how someone recognises
  their own entry, and how a later catalogue improvement can re-resolve it.
- An unresolved planting has only `raw_name`.

The `UNIQUE (bed_id, taxon_id)` constraint stays. SQLite treats NULLs as
distinct, so several unidentified plantings can share a bed, which is what
should happen: two unknown roses are two plants.

## Business Rules

- **Resolution is offered, not imposed.** The user types a name, sees what it
  matched, and can accept it or keep their own wording unmatched. A silent
  match is how someone ends up with *Achillea millefolium* when they meant a
  cultivar that behaves nothing like it.
- **Quantity applies to both kinds.** Five unidentified roses are five plants.
- **A re-resolution never overwrites.** If the catalogue later learns a name, the
  raw name stays; the taxon is added beside it.
- **The score says what it could not count.** A number computed over 4 of 7
  plantings must say so, for the same reason the filters report their unknowns.

## Security

`raw_name` is user content: stored parameterised, rendered as text, length
bounded. The search path is Wave 6's `search_names`, which matches in Python
over an indexed load rather than interpolating the query.

## Known Issues

- **Resolution is exact-or-nothing.** A name matching several species resolves to
  none of them rather than guessing, which means "Rose" stays unidentified. A
  chooser that shows the candidates is the right answer and is not built yet.
- **Unidentified plantings are not re-resolved** when the catalogue improves. The
  raw name is stored so they can be, but nothing sweeps them.

## Bugs

**The migration this feature needed does not exist in SQLite.** Making
`planting.taxon_id` nullable is not something `CREATE TABLE IF NOT EXISTS` or
any `ALTER TABLE` can do — the old table survives with its NOT NULL intact. A
fresh deployment would have worked and the production volume would have rejected
every unidentified planting, after the deploy, in front of the user, with a
green suite behind it. Caught by writing the grown-volume test before the code:
`init_schema` now rebuilds the table, copies the rows and swaps the names, and a
test asserts an existing planting survives with its quantity.

**An inner join would have dropped exactly the rows this feature adds.**
`_plantings_for` joined `taxon`, so a planting with no taxon simply vanished
from the garden it was saved into. `mypy --strict` found the rest of that shape
for me: sixteen call sites assumed a planting always has a species, and each one
had to say what it does without one. All of them skip rather than count zero —
"we have no data" and "this plant is worth nothing" are different facts.
