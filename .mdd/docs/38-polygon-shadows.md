---
id: 38-polygon-shadows
title: A House Rarely Casts a Round Shadow
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-10
wave_status: complete
depends_on: [37-object-footprints]
relates: [34-sightlines, 12-bed-light]
source_files:
  - ninanatur/solar/reach.py
  - ninanatur/solar/shading.py
  - ninanatur/garden/sightlines.py
  - ninanatur/garden/store.py
  - ninanatur/api/sightlines.py
routes: []
models: []
test_files:
  - tests/test_concave_shadow.py
  - tests/test_polygon_shadows.py
  - tests/test_shading.py
  - tests/test_sightlines.py
data_flow: reads-existing
last_synced: 2026-09-22
status: complete
phase: all
mdd_version: 11
tags: [shadows, geometry, convex-hull, occlusion, sightlines]
path: Solar/Shadows
integration_contracts:
  - function: shadow_polygon(obstacle, sun)
    when: anything asks what an object shades
    note: sightlines and sunlight share it, so they agree by construction rather than by coincidence
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 38 — A House Rarely Casts a Round Shadow

## Purpose

Every shadow in this product was a circle. That fits a tree and misdescribes
everything else — and it was not a simplification of the geometry so much as a
claim about it.

## How

The shadow of a footprint is that footprint swept along the anti-solar direction
by `height / tan(altitude)`, and the convex hull of the original and the swept
copy. For the shapes a garden contains — rectangles, circles, sketched outlines
— the hull *is* the shadow.

Andrew's monotone chain does the hull. The inputs are tiny: a rectangle's shadow
is eight points before the hull and four to six after.

## The two occlusion models are now one

The data-flow analysis before this wave found `solar/shading.py::is_shaded` and
`garden/sightlines.py::_blocks` each deciding, independently, whether a cylinder
stands between two points. **They agreed only because both assumed a cylinder**,
and nothing would have failed on the day that stopped being true.

A sightline is a shadow cast from an eye. Both now ask the same question of the
same footprint, and a test asserts they answer it the same way.

## What changed in the answers, and why that is right

The near edge of an object is what binds, not its centre:

- **A shadow starts at the wall**, not at the wall's middle. A 4 m wall three
  metres thick used to leave a metre and a half of phantom sunlight.
- **You look over a hedge's front edge.** A 2 m hedge one metre deep at 5 m
  needs 2.6 m of plant at 10 m, not 2.4.

Three Wave 2–9 fixtures encoded the old approximation and were corrected with
the model rather than against it.

## Cost, measured

The wave named this as a risk: point-in-polygon inside a sampler that walks
15-minute steps across eight months. Measured on this hardware, per bed:

| Objects | Circles (16 edges) | Rectangles (4 edges) |
|---|---|---|
| 1 | 19 ms | 7 ms |
| 4 | 48 ms | 15 ms |
| 12 | 80 ms | 24 ms |

Comfortable, because the shadow polygon is built once per obstacle per sun
sample and the containment test then walks four to sixteen edges.

## Business Rules

- **Surfaces cast nothing.** Paving, gravel, lawn, a pond and a bed are filtered
  out before the shading and the sightlines ever see them. A model that shaded a
  terrace would darken every one in the country.
- **The ground under an object is shaded**, which the Wave 7 fix established and
  the polygon form keeps for free: the footprint is part of its own shadow.
- **A concave outline is shaded exactly** since 2026-09-22. The hull still
  draws its shadow (`shadow_polygon`), but whether a point is in it is asked of
  the footprint itself: inside the hull, a point of a concave outline is shaded
  only where the ray towards the sun meets the footprint within the shadow's
  length (`solar.reach.near_edge`, used by `is_shaded` and the grid's
  `ShadowAt`). The hull filled the notch — the inner corner of an L-shaped
  house, a courtyard between two wings — and read it as 0 h all day, on the map
  and in a bed's sample (review, 2026-09-21: a courtyard bed at 0 h reads 3.5 h
  now). A map drawn before, of a garden with such a house, reads stale once:
  the signature marks a concave outline that casts (`lightgrid._exact`).
  Convexity is judged with a point repeated back to back taken once:
  OpenStreetMap closes every way on its first node, and an L closed at its
  inner corner passed as convex until the check of 2026-09-22. The
  price, measured on 40 L-shaped houses round a 25 × 40 m plot (1,836 cells): a
  grid in 7.2 s where it took 5.9 s; convex outlines cost what they did.

## Known Issues

- ~~Concave footprints are over-shaded by the hull.~~ Fixed 2026-09-22 (above);
  the shadow drawn on the plan (`day.py`) is still the hull.
- The shadow polygon is recomputed per sun sample rather than cached. It is fast
  enough; it is not clever.

## Bugs

(none new)
