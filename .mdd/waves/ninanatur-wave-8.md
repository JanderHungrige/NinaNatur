---
id: ninanatur-wave-8
title: "Wave 8: From the map into the garden"
initiative: ninanatur
initiative_version: 10
status: planned
depends_on: ninanatur-wave-7
demo_state: "A user finds their address on a map, outlines the garden, and gets a drawing that already carries the surroundings that shade it — with heights it can defend"
created: 2026-08-28
hash: 3d97ad3d
---

# Wave 8 — From the map into the garden

## Demo-State

A user finds their address on a map, outlines the garden, and gets a drawing that
already carries the surroundings that shade it — with heights it can defend.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | map-selection | 30-map-selection | planned | — |
| 2 | object-heights | 31-object-heights | planned | 30 |
| 3 | imagery-objects | 32-imagery-objects | planned | 30 |

### 1 — map-selection (#2.3)

Search an address (Nominatim, verified working), outline the garden on an OSM
map, and convert the selection into a drawing.

**The margin is the point.** The selection is taken with a configurable border of
extra metres, because what shades a garden is mostly *outside* it — the
neighbour's house, the street trees. A garden cut to its own boundary would model
sunlight as if it stood in open country.

Latitude, orientation and area come from the selection, so Wave 3's manual
coordinate entry becomes a fallback. Latitude is still rounded to 0.1° on the way
into storage — the map knows where the garden is, the database does not need to.

Buildings and trees inside the margin come from OSM via Overpass, verified
working, and land as labelled objects the user can correct.

### 2 — object-heights (#8, corrected)

**Terrain elevation is the wrong data for this.** Open DEMs describe the ground,
and over the twenty metres of a garden the ground barely changes — what shades a
bed is the twelve-metre building next to it. Terrain only matters on a real
slope, and then as context rather than as the shading model.

So heights come from objects, in descending order of confidence:

| Source | Confidence | Measured |
|---|---|---|
| user-entered (Wave 7 labelling) | authoritative | — |
| OSM `height` | high | present on a minority of buildings |
| OSM `building:levels` × storey height | estimated | present on some more |
| type default (tree, hedge, shed) | weak, and labelled as such | — |

Sampled six central Berlin buildings: one carried `height`, two `building:levels`,
three neither. **A shading model that assumed OSM heights would silently
under-shade half the gardens in Germany**, so every height carries where it came
from and the UI asks the user to confirm the estimated ones.

Terrain slope is a later addition, and only for gardens where it is real.

### 3 — imagery-objects (#2.4)

Recognise buildings, trees and paths from aerial imagery and place them in the
drawing for the user to correct.

**This is a sub-project, not a feature, and it has a licensing question before it
has a technical one.** OSM is open data; aerial and satellite imagery generally is
not. Germany's state surveying offices publish orthophotos under Datenlizenz
Deutschland, but coverage, resolution and terms differ per Bundesland, and the
federal WMS refused an anonymous request. **No imagery may be used until its
licence is established** — the same rule that kept this project off NaturaDB, and
it must not bend because the data would be convenient.

If the licence clears, the recognition itself has an obvious starting point: the
DINOv2/v3 pipeline in the sister project `DinoTraining`. Segmentation of roofs and
tree crowns from orthophotos is exactly what it is built for.

If it does not clear, OSM footprints from feature 1 already give buildings and
many trees, and this feature narrows to refining what OSM has.

## Risks

- Imagery licensing may block feature 3 entirely. Features 1 and 2 stand alone,
  which is why they come first.
- Overpass is a shared free service. Cache aggressively and rate-limit, or be a
  bad citizen of infrastructure this project depends on.

## Open Research

- [ ] **Which aerial imagery may we use, under what licence, at what coverage?**
      Must be answered before any work on feature 3.

## Definition of done

Entering an address produces a drawing with the garden outlined, neighbouring
buildings and trees placed with heights, every estimated height marked as such —
and the bed light values change accordingly.
