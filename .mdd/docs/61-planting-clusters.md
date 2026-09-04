---
id: 61-planting-clusters
title: Every Planting as a Patch
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-15
wave_status: complete
depends_on: []
relates: [56-bloom-dots, 60-feedback-box]
source_files:
  - ninanatur/bloom/palette.py
  - ninanatur/garden/plantings.py
  - ninanatur/api/planning.py
  - frontend/src/canvas/clusters.ts
  - frontend/src/canvas/useClusterDrag.ts
  - frontend/src/components/ClusterLayer.tsx
  - frontend/src/components/BedPlantings.tsx
routes:
  - PATCH /api/v1/gardens/{token}/plantings/{planting_id}
models: [planting]
test_files:
  - tests/test_planting_clusters.py
  - frontend/src/canvas/clusters.test.ts
  - frontend/src/components/ClusterLayer.test.tsx
  - frontend/src/components/BedPlantings.test.tsx
data_flow: writes-existing
last_synced: 2026-09-04
status: complete
phase: all
mdd_version: 11
tags: [plantings, clusters, bloom, canvas, drag, clipboard]
path: Plan/Plantings
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - ninanatur/api/planning.py::_owned_planting
known_issues: []
---

# Every planting as a patch

## What this is

Each planting is drawn as a clump of dots in its bed: grey when it is not in
flower, in its colour when it is. Click one for its name and an info button,
drag it about inside the bed, copy it into another bed.

## Decisions

### A planting is a cluster — no new table

`planting` has carried `UNIQUE (element_id, taxon_id)` since Wave 4: one row per
species per bed. So cluster identity was already there, and a position is two
nullable columns rather than a table of its own.

The consequence is worth stating because it is a design choice and not an
accident: **pasting a species into a bed it is already in raises the count**
rather than starting a second patch of it a metre away. That is what a gardener
means by planting more of something.

Null, not `0,0`, for a position nobody has set. Defaulting to the origin would
stack every existing planting in one corner of its bed. Null lets the plan
derive a place from the planting id — stable across renders and browsers,
without pretending to be a decision somebody made.

A position outside the bed is accepted by the server. The plan clamps a drag to
the outline, but a bed can be reshaped afterwards and a position that was inside
ends up outside; refusing it would mean a bed could not be made smaller without
first moving everything in it.

### Grey is the point, not the fallback

The bands and the hatch are gone. A colour band said a bed was half yellow and
half blue when what is true is that some of the flowers are; the hatch — the
"Farbstreifen" that was still being seen — filled a whole bed when its colours
were unrecorded.

Drawing every planting all year is what answers the question the plan is
actually for. Before this, a bed out of season and an empty bed looked exactly
alike.

### The size is a guess, and must not look like a measurement

Cluster radius comes from `space_m2 × quantity`. That number is estimated from
height by `canopy.py`, and the catalogue records **no spread at all** — height
is known for 3,952 of 8,939 species, so most clusters fall back to a default of
0.33 m² per plant.

So a cluster is a soft blob with no area printed anywhere. `canopy.py` states
the rule: a derived number that looks measured is worse than no number.

### The clamp had to survive rounding

`keepInside` puts a dragged cluster back inside its bed's outline — not its
bounding box, because the notch of an L-shaped bed is not in the bed.

Two things went wrong before it worked, and both are recorded because both were
invisible to the obvious test:

1. **Exactly on the line is outside.** A point-in-polygon test answers "outside"
   for a point on the boundary, so a clamped cluster failed the very check that
   had clamped it. It needs an inset.
2. **A millimetre is not an inset.** The first one was 0.001 m. Every unit test
   passed and the app put the cluster exactly on the corner of the bed: stored
   positions are rounded to centimetres, and the inset was rounded away. It is
   2 cm now — larger than the rounding step it passes through. Found by dragging
   a real cluster in a real garden, not by a test.

The inset direction is the edge's normal, then a fan of sixteen. "Towards the
centroid" is the obvious choice and is wrong for a concave bed — from the inner
edge of an L's arm the centroid lies *across* that edge. And when the nearest
point is a corner, no single edge normal points inwards at all.

### What the pointer actually hits

A dot is two centimetres across in garden metres. Each cluster carries an
invisible `cluster__reach` circle, at least 0.35 m, because chasing a dot that
size with a mouse is not a gesture anybody can perform.

The name is drawn on the plan rather than in a panel across the page, sized from
the grid spacing: the viewBox is in metres, so a fixed font size would be a
fixed number of *metres* tall — unreadable zoomed out, enormous zoomed in.
