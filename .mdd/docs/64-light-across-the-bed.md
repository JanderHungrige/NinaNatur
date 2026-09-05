---
id: 64-light-across-the-bed
title: Light Across the Bed, Not at Its Middle
edition: MDD
initiative: ninanatur
depends_on: []
relates: [65-the-shade-switch, 66-a-tree-is-not-a-wall]
source_files:
  - ninanatur/solar/field.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/garden/roofs.py
  - ninanatur/garden/lighting.py
  - ninanatur/api/light.py
routes:
  - GET /api/v1/gardens/{token}/light
  - POST /api/v1/gardens/{token}/light
models: [light_grid, element]
test_files:
  - tests/test_light_grid.py
  - tests/test_shading_is_ray_tracing.py
  - tests/test_roofs.py
  - tests/test_light_api.py
data_flow: mixed
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [shading, solar, grid, roofs, ellenberg, staleness]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# Light Across the Bed, Not at Its Middle

## What was wrong

The light model asked one question per bed: how much sun reaches the polygon's
centroid. A bed whose northern half sits in the house's shadow all day reported
a single number from its middle — and that number was then used to rank every
suggestion for the whole bed. There was nothing to draw a map from, and nothing
to place a plant by.

## What it does now

The same computation, asked at many points. The garden's extent is covered with
square cells and each one gets its own mean daily sun hours over the light
season (1 March to 31 October, every tenth day, every half hour above 5°
altitude — 1,200 sun positions).

That only became affordable because `solar/field.py` stopped redoing the work
per point. The sun positions and the shadow polygons of a season are the same
for every cell in the garden; they are computed once, kept with their bounding
boxes, and each point is then a run of cheap containment tests. 125 ms per point
became 1.09 ms — 85× — which is what turns 1 point into 600.

Cell size comes off a ladder (0.5, 1, 2, 3, 5 m) and is chosen so the grid stays
under `MAX_CELLS = 600`: roughly half a second of work. A large plot gets a
coarser grid rather than a long wait. Nothing finer than half a metre is offered,
because most building heights in this model are assumed and a 10 cm grid would
claim more than the model knows.

A bed's own light value is now the mean of the cells its polygon covers, not a
point sample. Raised beds and beds narrower than one cell fall back to the point.

## Roofs

A building's shadow is no longer its full height everywhere. The user picks a
roof shape, and the shading height is the eaves plus a kept fraction of the rise:

| Roof | Kept |
|------|------|
| flat | 1.0 |
| gable | 0.5 |
| hip | 0.4 |
| pent | 0.6 |
| unknown | 1.0 |

`unknown` keeps the whole height on purpose. A garden told it has more sun than
it has is the worse error: somebody plants for it and the plant dies. OSM's
`roof:shape` fills this in where it says anything, and where it does not, the
eaves default to 75 % of the height.

## Staleness

The map is expensive enough to store, and a stored map can be wrong. It is
therefore kept next to a **signature** of everything that can move a shadow —
latitude, longitude, and each element's id, kind, height, roof, eaves, height
above ground and outline, plus each planting's species, count and position.
`stale` is that signature disagreeing with the garden as it stands.

A signature rather than a list of actions that ought to invalidate it. A list
has to be remembered at every new endpoint, and the first one somebody forgets
is silent. Renaming a bed does not move a shadow, and the signature knows that
without being told.

`POST .../light` recomputes on demand — belt as well as braces. If the signature
ever misses something, that is how somebody fixes their own map without having
to know why it was wrong.

## Why it is trusted

The model is a projection, not a ray tracer: a footprint swept along the sun
vector by `height / tan(altitude)`, then the convex hull of both. That is fast
and it is an approximation, so it is checked against the thing it approximates.
`tests/test_shading_is_ray_tracing.py` marches a ray in 3D from a point towards
the sun and asks whether anything blocks it, over 263 random scenes, and the two
agree. Overlapping shadows, a tree behind a taller house, and a raised bed
behind a fence are each written out as their own case.
