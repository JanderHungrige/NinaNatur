---
id: 21-german-names
title: German Names, and Finding a Plant by One
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-6
wave_status: active
depends_on: [01-trait-ingest]
relates: [23-catalogue-filters, 22-species-info]
source_files:
  - ninanatur/ingest/sources/vernacular.py
  - ninanatur/ingest/db.py
  - ninanatur/data/names.py
  - ninanatur/api/plants.py
routes:
  - GET /api/v1/plants (name= parameter)
models:
  - vernacular_name
test_files:
  - tests/test_vernacular.py
data_flow: mixed
last_synced: 2026-08-28
status: draft
phase: "1"
mdd_version: 11
tags: [names, german, search, gbif, vernacular]
path: Data/Names
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 21 — German Names, and Finding a Plant by One

## Purpose

The catalogue holds 3,087 usable species and shows them as Latin binomials.
Nobody browses that. A user should never have to know that *Sal-Weide* is
*Salix caprea*.

## The source

GBIF's vernacular names, checked before planning: 10–20 German names per species,
and — usefully — **including spellings with and without umlauts**.
`Frühlings-Schlüsselblume` and `Fruehlings-Schluesselblume` both appear, which is
exactly what a search box needs and would otherwise have to be generated.

## Data Model

**vernacular_name**
`taxon_id INTEGER FK, name TEXT NOT NULL, normalised TEXT NOT NULL,
 is_preferred INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL,
 PRIMARY KEY (taxon_id, name)`

`normalised` is what search matches against: lowercased, umlauts folded, hyphens
and spaces removed. Stored rather than computed per query, because a `LIKE` over
a computed expression cannot use an index.

**One preferred name per species for display**, all of them searchable. Preference
goes to the shortest name that is not an abbreviation — *Sal-Weide* over
*Salweide (Artengruppe)* — because a display name is read, not parsed.

## Business Rules

- **Search matches German and scientific names alike.** A user typing "Salix"
  and a user typing "Weide" are both looking for the same thing.
- **Folding is symmetric.** Searching `Schlusselblume`, `Schlüsselblume` or
  `schluesselblume` finds the same species. Users type what their keyboard makes
  easy, not what the botanist wrote.
- **A species without a German name keeps its scientific one.** No placeholder,
  no empty string — the binomial *is* its name.
- **Matching is prefix-based, not fuzzy.** Fuzzy matching on 3,000 species
  produces confident nonsense; a prefix match that finds nothing is honest and
  the user can shorten their query.

## Security

Outbound reads of a public API. Names are untrusted text: parameterised on the
way in, and the search parameter is bound, never interpolated.

## Known Issues

(none yet)

## Bugs

(none yet)
