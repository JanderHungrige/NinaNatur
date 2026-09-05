---
id: 67-sun-plant-in-a-shade-spot
title: A Sun Plant in a Shade Spot, and Which Hours It Gets
edition: MDD
initiative: ninanatur
depends_on: [64-light-across-the-bed]
relates: [64-light-across-the-bed, 65-the-shade-switch]
source_files:
  - ninanatur/garden/misplaced.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/solar/field.py
  - ninanatur/api/light.py
  - frontend/src/components/ShadeSwitch.tsx
routes:
  - GET /api/v1/gardens/{token}/light
models: [light_grid, planting, trait]
test_files:
  - tests/test_misplaced.py
  - tests/test_light_grid.py
  - frontend/src/components/ShadeSwitch.test.tsx
data_flow: reads-existing
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [ellenberg, warning, shading, morning, halbschatten]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Species without an EIVE light value are never flagged; EIVE covers a good part of the German flora, not all of it."
---

# A Sun Plant in a Shade Spot, and Which Hours It Gets

## The warning

Suggestions have always ranked by fit, light included, so what goes *into* a bed
is chosen against the site. Nothing ever looked at what was **already there** —
and until the grid existed nothing could: one number per bed can say the bed is
wrong, never the corner. "This bed is too dark" for a bed whose far end is in
full sun is the kind of advice that teaches people to ignore advice.

Each cluster's Ellenberg L is now compared against the light in the cell it
actually stands in, and the difference is reported when it exceeds **two rungs**.
Two rather than one: one rung is inside the noise of a model whose building
heights are mostly assumed, and a warning nobody can act on is a warning people
learn to scroll past.

Both directions are named. `too_bright` is as real as `too_dark` — a fern in the
open is as misplaced as a sedum under a hedge — and only one of the two ever
gets talked about.

**A warning, never a refusal.** The gardener may know something the model does
not: a cultivar bred for shade, a wall that throws light back, or simply that
they want it there. The panel says so in as many words, under the list.

## Which hours

The grid also counts the sun before the azimuth crosses due south, and the panel
reports the share. Afternoon sun is hotter and harsher, and a great many species
sold as *Halbschatten* want the morning specifically — a single total of four
hours cannot say which four.

Grids computed before the split existed keep working: `morning` comes back empty
and the panel leaves the line out until the next rebuild fills it.

## Tests worth keeping

`tests/test_misplaced.py` covers the same species being fine at the far end of
the same bed — which is the whole reason the grid had to come first — as well as
a difference just under tolerance, a species with no EIVE value at all, and a
garden with no grid.

`tests/test_light_grid.py` proves the split against geometry rather than
arithmetic: a wall to the east costs the morning specifically, and the morning
share behind it drops below 0.4.
