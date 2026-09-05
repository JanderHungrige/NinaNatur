---
id: 71-buildings-stand-on-the-ground
title: Buildings Stand on the Ground
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-17
wave_status: active
depends_on: [69-a-window-of-ground]
relates: [64-light-across-the-bed, 69-a-window-of-ground]
source_files:
  - ninanatur/solar/shading.py
  - ninanatur/solar/field.py
  - ninanatur/garden/ground.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/garden/lighting.py
routes: []
models: [terrain_window]
test_files:
  - tests/test_ground.py
  - tests/test_terrain_shading.py
data_flow: reads-existing
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [terrain, shading, slope, performance, ray-tracing]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Terrain does not shade itself in the near field: a bank between a cell and the sun blocks nothing unless a building stands on it. Feature 4 adds the far field; the near field is not modelled."
  - "Hours, not energy. A north-facing slope can gain hours by seeing over southern obstacles while receiving less energy per square metre, and only the hours are reported."
---

# Buildings Stand on the Ground

Feature 3 of Wave 17. Every shadow in this project was computed on a plane at
z = 0. Now each obstacle stands on the ground beneath its own footprint, and
each cell of the light grid stands at its own height.

## What changed

`Obstacle` gains a `base` — the ground it stands on — and a `top` that is
`base + height`. Zero is the flat world, so every garden made before this is
unaffected by construction, and 796 tests said so without a line being touched.

`standing_on` puts each obstacle on the **mean** of the terrain under its
outline rather than on one corner: the ground under a building is interpolated
in the first place, because a laser does not see through a roof, so a corner is
no more truthful than an average and is noisier.

## Keeping Wave 16's speed

Wave 16's grid was fast because each moment's shadow polygons were computed once
and reused for every point — valid only because every point was at zero. With
terrain each point has its own height, so a single swept polygon no longer
serves.

The polygon is now swept onto the garden's **lowest** ground, which makes it a
superset of the shadow reaching any real cell. So the two fast rejections are
unchanged, and only a cell standing higher than the floor pays for an exact
check:

> the swept hull of a footprint is that footprint plus a segment, so a point is
> inside it exactly when the ray back towards the sun meets the footprint within
> the shadow's length

Turned into the frame where the shadow runs along −y, that is one interval
comparison against the footprint's near edge — no second polygon.

Measured on a 336-cell grid with ten buildings:

| | per cell |
|---|---|
| Wave 16, flat | 1.15 ms |
| With terrain | **1.19 ms** |

Three per cent. The budget Wave 16 set — 1.09 ms and under a second per grid —
still holds.

## Proved against a ray marched in three dimensions

The same method that proved Wave 16's projection: two hundred random scenes
answered by the model and by marching a ray to the sun in 3D.

**Two things came out of it, and both were mine rather than the model's.**

The first version of the ray tracer let rays pass *under* a raised obstacle, and
disagreed in eleven scenes. It was wrong: a shed on a bank three metres up is
not a shed floating in air, it is three metres of earth with a shed on top. The
ground under a building is part of the building, for shading purposes, and that
is now written down rather than assumed.

Then two scenes still disagreed, both the same shape: a point standing **inside
a footprint** at the height of its own ridge. The model called it shaded,
because the distance it needed the shadow to travel was negative and so was the
reach. That was a real gap, and the guard is now explicit — *nothing entirely
below a point can shade it*. The remaining case, a point one centimetre inside a
solid, is not a garden point and is skipped, with the test asserting that it
still compares more than 150 scenes so it cannot pass by skipping everything.

## What it still does not know

- **Terrain does not shade itself in the near field.** A bank between a cell and
  the sun blocks nothing unless something is built on it. The far field is
  feature 4's horizon ring; the near field is not modelled, and the wave's plan
  is honest that a per-cell horizon at 600 cells × 360 azimuths × 1,200 moments
  is not a computation this app will do.
- **Hours, not energy.** A slope can gain hours by seeing over the obstacles
  south of it while receiving less energy per square metre, and only the hours
  are reported. Slope and aspect are named in feature 5 and deliberately not
  scored.
- **The terrain is read, never fetched, during a recompute.** A state survey
  answering in eight seconds is not something to do while somebody waits for a
  page. No stored window means the flat world — which is also what a garden in
  one of the nine states without a service gets.
