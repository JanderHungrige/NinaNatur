---
id: 59-osm-streets
title: The Street Outside, From the Map
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-14
wave_status: complete
depends_on: [42-element-model, 31-map-selection]
relates: [32-object-heights]
source_files:
  - ninanatur/geo/osm.py
  - ninanatur/api/geo.py
  - ninanatur/garden/objects.py
  - frontend/src/kinds.ts
  - frontend/src/components/GardenSymbols.tsx
routes: ["/api/v1/gardens/from-map"]
models: [element]
test_files:
  - tests/test_osm_streets.py
  - tests/test_map_selection.py
data_flow: writes-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [osm, overpass, streets, line-elements]
path: Geo/Streets
integration_contracts:
  - from: 42-element-model
    function: line elements
    when: a street is drawn
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Every way in the 50 m margin is drawn; a garden on a corner gets a dozen."
---

# The street outside, from the map

## What this is

The ways around a garden, drawn on its plan, taken from OpenStreetMap when the
garden is made from the map.

## Decisions

### A street is the element Wave 11 already built

A road is a centreline and a width. That is exactly `shape: 'line'`, and
`band_of` already turns it into the footprint everything downstream consumes.
Nobody had to trace a polygon around a road, and no new geometry was written for
this feature at all.

### Its own kind, not "path"

A ten-metre carriageway and a one-metre slab path are not the same thing to look
at. The vocabulary is built to be complete per kind — every kind appears in
every table — so a street gets its own entry, its own tarmac symbol, and a
coarser grain than gravel so the two never read as the same ground.

### It has no height, and that is not zero

A street does not shade a garden. `height` is `None`, which keeps it out of the
light model entirely — a zero would be a measurement nobody took, which is Wave
8's rule and the reason `ObstacleInput.height` is now optional rather than
defaulting to `0.0`.

### `out geom`, not `out center`

The buildings query asks for centres because a building's shape is not needed
for shading. A street's shape is the whole of what makes it useful, so this one
asks for geometry.

### Widths are guessed, and say so

OSM records a width for almost nothing. A table maps `highway` to a plausible
carriageway width, and a recorded `width` always wins. A plan needs a plausible
line, not a surveyed one — and `"ca. 6 m"` falls back to the guess rather than
refusing to draw the street.

### A refusal costs the streets, not the garden

Overpass is free and has the same no-SLA standing as Nominatim. If it will not
answer, the garden is still made and the failure is logged with context.

## What this found in the tests

Adding the call made an existing test reach the network: it stubbed
`buildings_in` and nothing else, so the suite started calling Overpass for real
— and passed, because the disk cache was warm. That is exactly the shape
CLAUDE.md warns about: green here, red in CI, for a reason nobody changed.

Streets are stubbed in the fixture rather than per test, so no test can reach
the network by forgetting to. One test of mine had the same fault and now stubs
both.

## Definition of done

A garden made from the map carries the ways around it as line elements with
plausible widths, none of them casting a shadow, and no test touches Overpass.
