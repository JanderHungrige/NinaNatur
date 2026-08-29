---
id: 32-object-heights
title: Heights the Model Can Defend
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-8
wave_status: complete
depends_on: [31-map-selection]
relates: [27-object-labelling]
source_files:
  - ninanatur/geo/surroundings.py
  - ninanatur/api/schemas.py
  - frontend/src/components/MapPicker.tsx
  - frontend/src/App.tsx
routes:
  - POST /api/v1/gardens/from-map
models: []
test_files:
  - tests/test_surroundings.py
  - tests/test_map_selection.py
data_flow: reads-existing
last_synced: 2026-08-29
status: complete
phase: all
mdd_version: 11
tags: [heights, osm, provenance, estimate, shading, neighbourhood]
path: Garden/Heights
integration_contracts:
  - function: surroundings_from(anchor, buildings, neighbourhood)
    when: the map places objects around a garden
    note: every height carries where it came from; an assumed height presented as measured would be the same lie as a filter that hides what it dropped
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 32 — Heights the Model Can Defend

## Purpose

A shading model needs heights. This is where they come from, and — more
importantly — where they say they came from.

## Terrain elevation is the wrong data for this

Open DEMs describe the ground, and over the twenty metres of a garden the ground
barely changes. What shades a bed is the twelve-metre building next to it.
Terrain matters on a real slope, and then as context rather than as the model.
This corrects the original feature request, which asked for elevation data.

## What OSM actually has, measured

| Area | Buildings | `height` | `building:levels` | neither |
|---|---|---|---|---|
| Kleinmachnow | 2,098 | **0%** | 12% | 88% |
| Berlin-Zehlendorf | 1,505 | **0%** | 22% | 78% |
| Münster-Gievenbeck | 1,309 | **0%** | 25% | 75% |
| Berlin-Mitte | 298 | 2% | 66% | 32% |

**Zero `height` tags across 4,912 suburban buildings.** The first plan sampled
central Berlin and built a confidence ladder whose top two rungs are empty
exactly where gardens are.

## One question per garden

So the bottom rung is the normal case, and it is asked for rather than assumed
silently: *"Wie hoch ist die Nachbarbebauung typischerweise?"* — detached ≈ 7 m,
terrace ≈ 9 m, apartment ≈ 14 m. One answer fills every building with no
recorded height; individual buildings stay correctable on the plan afterwards.

The alternative was confirming each one, which in the measured example is **13
confirmations before the first plant suggestion** — a wall at the moment
somebody has just arrived.

The ladder, in order: a height the user typed, then OSM `height`, then
`building:levels` × 3 m, then the neighbourhood answer.

## Every height says where it came from

`HeightSource` travels with the value and the creation response reports the
split — *"2 aus der Karte übernommen — 0 gemessen, 2 aus Geschossen, 0
angenommen"*. **An assumed height presented as a measured one is the same lie as
a filter that hides what it dropped**, and this project has already made that
mistake once with the flowering-month filter.

## Business Rules

- **A height in feet is refused, not believed.** OSM permits units, and `30'`
  read as 30 metres is a ten-storey shadow over somebody's vegetable patch. Only
  a bare number is accepted.
- **Implausible values are refused**: over 200 m for a height, over 60 storeys.
- **The neighbourhood answer never overrides a recorded height.**
- **The distance used is to the building's edge**, not its centre: a large
  building's wall is what stands next to the garden.

## Known Issues

- **A storey is assumed to be 3 m.** A rounded number for German residential
  building; it decides only the `building:levels` rung. Whether it holds well
  enough, or needs its own value per building type, is unanswered.
- **The neighbourhood answer is one number for 75–88% of the buildings around a
  garden.** The honest option available, not a good measurement.

## Bugs

(none new)
