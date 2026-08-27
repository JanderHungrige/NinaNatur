---
id: ninanatur-wave-4
title: "Wave 4: Suggestions and the bloom year"
initiative: ninanatur
initiative_version: 2
status: planned
depends_on: ninanatur-wave-3
demo_state: "A bed shows fitting species plus a bloom calendar for the year, with gaps marked"
created: 2026-08-27
hash: bf9c80f1
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

## Colour, honestly

Colour is known for 527 species and unknown for the rest — that is settled and
will not be closed before this wave. Two rules follow:

- Colour **filters softly**. Selecting "blue" must not silently drop every species
  whose colour merely was never recorded, which is most of the catalogue.
- The timeline renders unknown-colour species in a neutral tone labelled as
  unknown, never in an invented colour. A guessed colour would be the one thing
  in this product a user could not tell apart from a fact.

## Definition of done

Selecting a bed yields a ranked, filterable species list and a bloom calendar
where gaps are visible without explanation.
