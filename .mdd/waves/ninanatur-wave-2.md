---
id: ninanatur-wave-2
title: "Wave 2: The data layer answers questions"
initiative: ninanatur
initiative_version: 2
status: planned
depends_on: ninanatur-wave-1
demo_state: "The API answers 'which plants suit these site conditions' from the ingested open data, every value citing its source"
created: 2026-08-27
hash: 003791bd
---

# Wave 2 — The data layer answers questions

## Why now

The ingest pipeline (doc `01-trait-ingest`) already fills the database. What is
missing is the read side: turning many sources per trait into one answer, and
exposing it. Until that exists no UI wave can be built against anything real.

## Scope

**In:**
- `resolve_trait()` — read-time priority across sources, returning the value
  *and* which source won. Disagreement is displayed, never hidden.
- Flower colour: keep the 527 known values, give the rest an explicit *unknown*
  placeholder. Colour never excludes a species — see the initiative decision.
- German insect checklist from the GBIF occurrence facet (`taxonKey=216`,
  11.6M records), then intersect GloBI relations against it so counts mean
  "visits this in Germany", not "has been studied worldwide". This generalises
  `fetch_german_species_keys()` rather than adding a source.
- FastAPI under `/api/v1/`: plant search by site conditions, plant detail with provenance
- A typed client module as the single frontend/backend contract

**Out:** scoring, garden geometry, shops.

The catalogue is all 3,087 core-complete species — no curated subset. Commercial
availability is a Wave 6 concern.

## Key decisions to make here

- **Source priority order.** EIVE is measured and continuous; GIFT is aggregated
  from literature. When they disagree on the same axis, which wins, and does the
  UI say so?
- **Ellenberg tolerance bands.** A bed is a range, not a point. How wide a band
  around a bed's derived values still counts as "fits"? This single number drives
  how generous every suggestion feels.

## Definition of done

`GET /api/v1/plants?light=7&moisture=4&...` returns ranked species with the
source behind every trait value, and the response shape is what Wave 3 and 4
will consume unchanged.
