---
id: 72-the-hill-that-eats-the-morning
title: The Hill That Eats the Morning
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-17
wave_status: active
depends_on: [70-the-horizon-ring, 71-buildings-stand-on-the-ground]
relates: [70-the-horizon-ring, 71-buildings-stand-on-the-ground]
source_files:
  - ninanatur/garden/slopes.py
  - ninanatur/solar/field.py
  - ninanatur/solar/reach.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/garden/lighting.py
routes: []
models: [terrain_horizon]
test_files:
  - tests/test_slopes.py
data_flow: reads-existing
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [terrain, horizon, slope, aspect, solar, performance]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Hours, not energy: a 17° slope at 52°N moves the hours by less than a quarter, while changing the energy per square metre a great deal. The page must not let 12.5 h on a north bank read as 'as good as flat'."
  - "The near field is modelled as a plane through each cell. A concave hollow or a single steep step within the garden is not a plane, and is smoothed."
---

# The Hill That Eats the Morning

Feature 4 of Wave 17. Two scales of land, one answer: the sun is blocked by
whichever reaches higher in its direction — the hills five kilometres out, or
the bank at the end of the garden.

## Two fields, because they are two different questions

The **far field** is the ring from feature 2: 20 m resolution over five
kilometres, measured once for the garden. Five kilometres of terrain does not
change across twenty metres of plot.

The **near field** is the slope under each cell, and no ring could ever see it.
For a plane of slope *s* climbing towards *aspect*, the ground's own angle in
direction θ is `atan(tan(s) · cos(θ − aspect))` — the full slope looking straight
uphill, nothing along the contour, and negative downhill, which is clamped away
because ground below a point does not shade it.

The two are combined per cell by taking the higher in each direction. Not added:
whichever blocks the sun first is the one that blocks it.

A slope gentler than **2°** is not reported at all. A DGM1 states ± 0.3 m, and
across the few metres a slope is measured over that is more than a degree — so a
gentler reading is not a gentle slope, it is the error bar.

## The ring made the model faster

A per-cell horizon computed honestly would be 600 cells × 360 azimuths × 1,200
moments, which is not a computation this app is going to do. Instead each cell's
ring is built once — cached on slope and aspect rounded to half a degree, so a
garden on a uniform hillside builds **one** — and the moments the sun spends
behind the land are dropped once per distinct sky rather than tested per point.

Measured on a 336-cell grid with ten buildings:

| | per cell |
|---|---|
| Flat, no ring | 1.19 ms |
| 10 % slope | 1.45 ms |
| 10 % slope in a 12° valley | 1.27 ms |
| **Flat in a 20° valley** | **0.81 ms** |

A garden in a valley iterates fewer moments than one in the open, so the feature
with the largest effect in hill country is also the only thing in this model that
makes it faster.

## What it actually does to a garden

| | mean sun |
|---|---|
| Flat, open sky | 12.58 h |
| Ground rising to the north (a south-facing garden) | 12.38 h |
| Ground rising to the south (a north-facing garden) | 12.50 h |
| Flat, in a 20° valley | 7.87 h |
| 4° horizon — Potsdam's | **unchanged** |

Two of those need saying out loud.

**Potsdam's horizon changes nothing, on purpose.** It is 4.8°, and the model
already stops counting the sun below 5°. A test asserts the inertness, because a
feature that appears to do nothing is otherwise indistinguishable from a broken
one.

**And a slope barely moves the hours at all** — the sunny aspect actually loses
slightly *more* than the shady one, because the ground behind a south-facing
garden blocks the low northern sun of a midsummer morning. That is geometrically
correct and it is nearly useless as gardening advice on its own. The noon sun at
52°N runs from 38° at the equinox to 61° at midsummer and clears a 17° skyline
easily; what a north bank loses is not hours but **energy per square metre**, and
this model reports hours.

That is why feature 5 names the slope on the page rather than folding it into the
light score. Nobody should read "12.5 h" on a north-facing bank as "as good as
flat", and the number alone would let them.

## One file split, and why

`field.py` reached its length limit, so the reach test moved to
`solar/reach.py`. The seam is real rather than convenient: `field.py` is about
the season's shadows, `reach.py` is about the geometry of one of them — the
observation that a swept hull is a footprint plus a segment, so a point is inside
it exactly when the ray back towards the sun meets the footprint in time.
