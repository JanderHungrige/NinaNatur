---
id: ninanatur-wave-4
title: "Wave 4: Suggestions and the bloom year"
initiative: ninanatur
initiative_version: 1
status: planned
depends_on: ninanatur-wave-3
demo_state: "A bed shows fitting species plus a bloom calendar for the year, with gaps marked"
created: 2026-08-27
hash: 93724ba3
---

# Wave 4 — Suggestions and the bloom year

## Scope

**In:**
- Match a bed's site vector against the candidate pool, ranked
- Design filters on top: height band, flower colour, desired flowering window
- Bloom timeline: per bed and per garden, flowering area by half-month
- Gap detection: stretches between March and October below a coverage threshold

## Design notes

Phenology is stored as half-month intervals, which is as precise as the source
data honestly supports — month-level data rendered as exact dates would invent
precision the user would then trust.

Bloom gaps are the feature that sells the product: they turn an abstract "plant
more natives" into one concrete, actionable sentence ("nothing flowers in your
garden between mid-March and April").

## Risk

Flower colour covers only ~13% of candidates unless Wave 2 closed it. The colour
simulation degrades to "flowering / not flowering" for the rest — decide whether
that ships or whether colour becomes a hard filter that shrinks the pool.

## Definition of done

Selecting a bed yields a ranked, filterable species list and a bloom calendar
where gaps are visible without explanation.
