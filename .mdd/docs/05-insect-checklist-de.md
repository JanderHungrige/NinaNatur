---
id: 05-insect-checklist-de
title: German Insect Checklist and GloBI Intersection
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-2
wave_status: complete
depends_on: [01-trait-ingest]
relates: [06-plants-api]
source_files:
  - ninanatur/ingest/sources/gbif.py
  - ninanatur/ingest/sources/insects_de.py
  - ninanatur/data/interactions.py
routes: []
models:
  - insect_de
  - interaction
test_files:
  - tests/test_insects_de.py
data_flow: mixed
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [globi, gbif, insects, interactions, insect-score]
path: Data/Interactions
integration_contracts:
  - function: german_partner_counts(conn, taxon_id)
    when: any count of a plant's animal partners shown to a user or fed into a score
    note: must never expose the raw global GloBI count — that ranks by research effort, not by German garden value
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 05 — German Insect Checklist and GloBI Intersection

## Purpose

GloBI's 600,131 ingested relations are worldwide. *Achillea millefolium* returns
1,504 flower visitors including New Zealand taxa. Counting those directly would
rank a plant by how thoroughly it has been studied globally rather than by what
actually visits it in a German garden — and that number would then drive the
insect score, which is the product's central claim.

This feature builds the German insect list and intersects against it.

## Architecture

The plant candidate set was derived from GBIF occurrence facets
(`taxonKey=7707728`, vascular plants). Insects are the same query with
`taxonKey=216` — 11.6M records. So this is a **generalisation of existing code**,
not a new integration: `fetch_german_species_keys()` gains a taxon-key parameter
and the insect adapter reuses it.

```
GBIF occurrence facet (taxonKey=216, country=DE)  ->  insect_de
                                                        |
GloBI interactions (already ingested, global)  --intersect--> german partner counts
```

## Data Model

**insect_de** — insect species recorded in Germany
`canonical_name TEXT PK, scientific_name TEXT, occurrences INTEGER NOT NULL`

Keyed by canonical name because that is what the intersection joins on. The names
come from GBIF's `SCIENTIFIC_NAME` occurrence facet — about 19 calls for ~21,000
species, instead of one detail request each — so no backbone key is involved and
inventing one would add a column nothing reads.

**Species only.** A third of the facet's names are higher ranks ("Diptera" is an
order, "Chironomidae" a family) from records identified no further. A GloBI
partner named "Diptera" matching "Germany has Diptera" is vacuously true and
would inflate every plant's count, so single-word names are dropped. 20,994
species remain — the independent species-key facet returns 18,858, which is the
cross-check.

`interaction` is unchanged. The intersection happens on read, by name, so
re-running the checklist never rewrites relation rows.

## Business Rules

- **Matching is by canonical name, and misses are counted.** GloBI partner names
  are free text from many datasets; some will not match the GBIF backbone. The
  count of unmatched partners is reported rather than quietly dropped, because a
  low match rate would invalidate the score and must be visible.
- **The global count stays available but never leads.** Both numbers are stored;
  the API exposes the German one as the count and the global one as context.
- **A plant with zero German partners is not the same as a plant with no data.**
  Species absent from GloBI entirely report `None`, not `0` — the same rule as
  every other unknown in this project.
- **Relations are grouped by kind**, since a larval host relation (`eatenBy`)
  means something different for butterflies than a flower visit does. Wave 5
  weights them differently and needs them separable.

## Dependencies

`01-trait-ingest` — the interaction table and the GBIF facet helper.

## Security

Outbound reads of a public API; all writes parameterised. Partner names arriving
from GloBI are untrusted text and are never interpolated into SQL.

## Known Issues

- Partner matching is by exact canonical name, and 45.6% of GloBI partner records
  do not resolve against the German list. Some of those are genuinely non-German
  taxa — which is the point — but some are name variants that a fuzzier match
  would catch. `match_rate` is exposed so the shortfall stays visible rather than
  reading as a finding.
- Subspecies collapse onto the species. Correct for matching, but it means a
  German subspecies of an otherwise foreign species cannot be distinguished.

## Bugs

(none yet)
