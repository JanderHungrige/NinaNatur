---
id: 66-a-tree-is-not-a-wall
title: A Tree Is Not a Wall, and in March It Is Barely There
edition: MDD
initiative: ninanatur
depends_on: [64-light-across-the-bed]
relates: [64-light-across-the-bed]
source_files:
  - ninanatur/garden/canopies.py
  - ninanatur/solar/shading.py
  - ninanatur/solar/field.py
  - ninanatur/garden/lighting.py
  - ninanatur/ingest/sources/gift.py
routes: []
models: [trait]
test_files:
  - tests/test_canopies.py
  - tests/test_planted_shade.py
data_flow: mixed
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [shading, canopy, gift, deciduous, traits]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "GIFT trait 2.4.1 covers 452 of 954 German woody species (47 %); the rest are assumed broadleaf in leaf."
---

# A Tree Is Not a Wall, and in March It Is Barely There

## What was wrong

Every obstacle was opaque. A spruce, a lime tree and a garage cast the same
shadow, and — the part that actually mattered — **a deciduous tree was modelled
as masonry in March**. The light season starts on 1 March, so the two months in
which somebody is deciding what to plant were the two months the model was most
wrong about.

## What it does now

A shadow carries a transmission, and the field multiplies the transmissions of
everything a ray passes through. Full darkness still short-circuits the loop, so
a garden full of buildings costs what it always did.

| State | Passes |
|-------|--------|
| evergreen | 8 % |
| broadleaf in leaf (May–October) | 20 % |
| broadleaf bare (March, April) | 75 % |

Rules of thumb rather than measurements, and named constants in one module so
that somebody who disagrees has one place to argue.

The leaf state comes from **GIFT trait 2.4.1**, ingested as `deciduousness`
through the ordinary provenance path. It covers 452 of 954 German woody species
— 47 %, measured before this was planned. Where it is missing the crown is
treated as a broadleaf in leaf, which is what most of a German garden's trees
are; the alternative was to go on calling them walls.

GIFT gives a third answer — `variable`, for six German woody species. It is
treated as evergreen for shading purposes: a plant that keeps some of its leaves
keeps some of its shade, and rounding it the other way would make a garden
brighter than it is.

## Leaf-out is an assumption, and says so

May to October. Leaf-out runs through April and leaf-fall through late October,
both varying by species and by year. This is a stated assumption in the same way
the assumed building heights are, not a measurement.

## Tests

`tests/test_canopies.py` puts a spruce and an oak in the same spot and shows the
oak's bed gets more light; puts a crown and a wall of equal height and footprint
side by side and measures 1.64 h of difference at a point 8 m north of them.

Both measurements are taken **north** of the obstacle. An earlier version of one
of these tests sampled a point to the south, where at 52.5°N no shadow ever
falls, and would have passed against any model at all.
