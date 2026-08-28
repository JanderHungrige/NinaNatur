---
id: 17-insect-groups
title: Which Insects Are Which
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-5
wave_status: active
depends_on: [05-insect-checklist-de]
relates: [18-insect-score]
source_files:
  - ninanatur/ingest/sources/insect_groups.py
  - ninanatur/ingest/db.py
  - ninanatur/ingest/summarise.py
  - ninanatur/data/interactions.py
test_files:
  - tests/test_insect_groups.py
routes: []
models:
  - insect_de
  - partner_summary
data_flow: mixed
last_synced: 2026-08-28
status: draft
phase: "1"
mdd_version: 11
tags: [insects, bees, lepidoptera, syrphidae, gbif, groups]
path: Data/Insects
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 17 — Which Insects Are Which

## Purpose

Turn "1,055 partners" into "40 wild bee species, 12 butterflies" — a statement a
gardener can act on, and the difference between a number and an argument.

## Restoring what Wave 2 traded away

Wave 2 built the German insect checklist from GBIF's `SCIENTIFIC_NAME` facet
instead of per-species detail calls: 19 requests instead of 19,000. That was the
right call, but it dropped family and order, and the loss was never written down.

The same trick recovers the groups without undoing the saving — one facet per
clade, eight calls total:

| Group | Clades | Keys |
|---|---|---|
| wild bees | Apidae, Andrenidae, Halictidae, Megachilidae, Colletidae, Melittidae | 4334, 7901, 7908, 7911, 7905, 4345 |
| butterflies & moths | Lepidoptera | 797 |
| hoverflies | Syrphidae | 6920 |

Bees are taken by family because the superfamily key is ambiguous — "Apoidea"
matches only fuzzily, and to a genus. Six exact family matches beat one uncertain
superfamily.

## Data Model

`insect_de` gains `insect_group TEXT` — `bee`, `butterfly`, `hoverfly`, or NULL
for everything else. The membership sets come from the facets, so classification
is a lookup, not a per-insect request.

`partner_summary` gains rows keyed by group alongside the existing relation
kinds, so the score reads counts per group without joining back to raw records.

## Business Rules

- **An unclassified insect still counts.** Beetles, wasps and flies are real
  visitors; they are simply not in a named group. Dropping them would make the
  total disagree with the group breakdown for no defensible reason.
- **Groups are not exclusive by accident.** A species appearing in two clade
  facets would be a data error, not a feature — the ingest asserts it does not
  happen rather than silently taking the last write.
- **Re-running is idempotent**, like every other ingest here.

## Known Issues

(none yet)

## Bugs

(none yet)
