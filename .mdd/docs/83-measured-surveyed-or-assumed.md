---
id: 83-measured-surveyed-or-assumed
title: Measured, Surveyed or Assumed
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-19
wave_status: active
depends_on: [81-a-house-with-a-measured-height, 82-the-roof-it-actually-has]
relates: [81-a-house-with-a-measured-height, 82-the-roof-it-actually-has]
source_files:
  - ninanatur/garden/measured.py
  - ninanatur/garden/building_sync.py
  - ninanatur/geo/surroundings.py
  - ninanatur/ingest/schema_user.py
  - frontend/src/heights.ts
  - frontend/src/components/ElementList.tsx
routes:
  - POST /api/v1/gardens/{token}/light
models: [element]
test_files:
  - tests/test_measured.py
  - frontend/src/heights.test.ts
  - frontend/src/components/ElementList.test.tsx
data_flow: writes-existing
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [provenance, heights, roofs, override, matching]
path: Map/Buildings
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The whole feature fetches at the garden's stored location, which is rounded to 0.1° — see tests/test_anchor_precision.py and Wave 17's doc. Correct code, wrong place."
  - "A building substantially under canopy is measured as the canopy and looks clean; only the official survey is immune, because it measured the building rather than what is over it."
---

# Measured, Surveyed or Assumed

Feature 3 of Wave 19. Features 1 and 2 found the measurements. This is where they
meet a garden, and the rule that governs it is the only part worth arguing about.

## The person in the garden outranks the survey

They can see the house. The model saw it from an aeroplane, some years ago,
through whatever was growing over it. Where they disagree, the gardener is right.

That is enforced twice, on purpose. `measure()` skips any building whose
`height_source` is `user` — an entry is a decision, not a default, and
re-measuring it would undo a correction somebody made deliberately. And the
`UPDATE` carries `AND height_source != 'user'`, so a measurement that reached the
write despite the first check still does not land.

## Six rungs, and a separate one for the roof

| | |
|---|---|
| `user` | somebody typed it |
| `surveyed` | the state's 3D building model, ± 1 m |
| `measured` | this model, from a laser surface raster over the drawn footprint |
| `osm_height` | a `height` tag |
| `osm_levels` | storeys × 3 m |
| `neighbourhood` | one answer for the whole garden |

The roof gets its own column. They arrive together from a 3D model and
separately from everywhere else — somebody can look out of a window and know the
shape without knowing the height, and a later refresh must not overwrite that.

## Matching: overlap, not distance

The wave plan said *"footprint overlap, not centroid distance"*. The first
version took the cheap route and the plan was right: against Cologne, a 47 m²
terraced house was handed the **2.7 m pent roof of the garage beside it**,
because the garage's centre was nearer than the eight-metre tolerance and
nothing else was consulted.

A garage does not overlap a house. The rule is now a third of the drawn
footprint's sampled points falling inside the candidate — a third rather than a
half, because an OSM outline that includes a porch would fail a stricter one.

With overlap matching, ten Cologne buildings matched at **89–100 %**, and the two
independent methods agreed within about a metre on every one of them:

| OSM | Raster | Survey |
|---|---|---|
| `house` 118 m² | 12.7 m | 13.4 m, gable |
| `terrace` 40 m² | 10.4 m | 11.0 m, gable |
| `terrace` 40 m² | 10.1 m | 11.1 m, gable |
| `house` 44 m² | 10.3 m | 11.0 m, mix |
| `yes` 39 m² | 10.5 m | 11.3 m, mix |

Two methods with almost nothing in common — a percentile over an eroded outline,
and a surveyor's own model — landing within a metre is the strongest evidence
either of them is right.

## Two sources also make disagreement visible

Where both answer and differ by more than 15 m, the **match** is what is suspect:
position will occasionally pair a garage with the house behind it, and the tell
is that the numbers are nowhere near each other. Then the raster wins, because it
was measured over the footprint actually drawn on this plan.

With one source a mismatched building would simply be wrong.

## And the page says which

`heights.ts` puts the provenance in words beside each element: *amtlich
vermessen*, *aus Laserdaten gemessen*, *aus Geschosszahl geschätzt*, *für die
Gegend angenommen*. A shading map resting on an assumption must not look like
one resting on a measurement.

The user's own entry is deliberately unlabelled — they know they typed it, and a
badge saying "you said so" on the one value somebody is sure about is noise. A
source the frontend does not recognise is shown verbatim rather than dropped: a
server that starts sending a new one must not quietly look like a user entry,
which is the single state that means *do not overwrite*.

## What this feature cannot fix

It fetches at the garden's stored location, and that is **rounded to 0.1°** — up
to six kilometres away. The code here is correct and the place it asks about is
not. See `tests/test_anchor_precision.py`, which asserts the defect rather than
guarding against it.
