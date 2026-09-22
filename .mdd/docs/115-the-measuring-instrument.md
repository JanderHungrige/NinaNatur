---
id: 115-the-measuring-instrument
title: The Measuring Instrument
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-26
wave_status: active
depends_on: [07-solar-geometry, 38-polygon-shadows, 64-light-across-the-bed]
relates: [71-buildings-stand-on-the-ground]
source_files:
  - scripts/sun_reference.py
  - tests/fixtures/sun_reference.json
routes: []
models: []
test_files:
  - tests/test_sun_reference.py
  - tests/test_concave_ray.py
  - tests/test_light_convergence.py
  - tests/test_shading_is_ray_tracing.py
  - tests/test_concave_shadow.py
  - tests/concave_shapes.py
data_flow: reads-existing
last_synced: 2026-09-22
status: complete
phase: all
mdd_version: 11
tags: [solar, light, validation, pvlib, nrel-spa, ray-tracing, convergence, sampling, concave]
path: Garden/Light/Validation
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The ray instrument knows vertical prisms only. Roof planes (feature 5) and ellipsoid crowns (feature 6) are to be added to it by the features that bring them, before their model code."
  - "The reference table was made with pvlib 0.15.2. SPA does not change between releases, so it is not refreshed with them; `python -m scripts.sun_reference` remakes it byte for byte if it ever has to be."
  - "The convergence suite measures one place (Wuppertal) and five scenes. Most of the sampling error is the days skipped, which depends on the season's shape and the obstacles more than on the place; the bars are the same everywhere."
  - "The marched ray is refined to 2 mm only where it disagrees with the model. A spike thinner than 5 cm that the model also missed would pass unseen; the random stars make such spikes, real outlines rarely do."
sister_projects: []
---

# 115 — The Measuring Instrument

Wave 26 changes the light model in five places. Before any of them, three
instruments that can say whether a change made it more accurate, because
until now the model had been checked against nothing but itself.

## 1. The sun, against NREL (`tests/test_sun_reference.py`)

`solar/position.py` is NOAA's algorithm, tested against physics: the sun is due
south at its highest, overhead at the equator at the equinox. Those tests catch
a dropped equation of time or a flipped sign. An error that stays plausible
passes all eleven of them, as measured:

- an equation of time at half its size puts the sun 1.1° off;
- a moment's seconds ignored puts it 0.4° off, and the drawing's moment
  (`solar/drawing.py`) has seconds in it.

`tests/fixtures/sun_reference.json` holds 200 moments, to the second, and
places in Germany's box, sun above 1°, all twelve months, mornings and
evenings. Each row carries the sun's place as NREL's Solar Position Algorithm
gives it, computed by pvlib (BSD). The elevation is the true one, without
refraction, because the model has none. `scripts/sun_reference.py` made it,
seeded, and says how to run it
(`uv run --no-project --with pvlib python -m scripts.sun_reference`).

**A table, not pvlib in CI.** The plan asked for pvlib as a dev extra. It brings
SciPy and h5py into the dev lock for one test, and a pvlib release could move
the answers under the test. SPA is deterministic: what it said for a moment is
what it will always say.

**Measured:** the model agrees within **0.016°** in altitude and azimuth. The
plan asked for 0.5°. The bar is **0.05°**, and both errors above fail it.

## 2. Concave outlines, against a ray (`tests/test_concave_ray.py`)

`test_shading_is_ray_tracing.py` marches a ray to the sun in three dimensions
and compares it with the projection, but only over rectangles. Rectangles are
the one shape the convex hull was right about, which is how the hull's error
(0 h in every inner corner) survived nineteen waves.

The new file uses random L, U and T shapes at any angle, plus random
star-shaped polygons, one to three per scene (`tests/concave_shapes.py`; 93% of
the outlines are concave: every L, U and T, and about 90% of the stars). Both
ways the model asks are checked:

- `is_shaded`, for a bed's point, on the ground or raised 0.8 m;
- the grid's `ShadowAt.covers_point`, for a cell standing at its own height,
  with houses on ground of their own and swept onto the lowest ground as
  `shadow_field` sweeps them. Half the cells stand on that lowest ground and
  half above it. A concave outline takes the exact reach at every height; only
  a convex one leaves the lowest ground to the polygon.

**Where the points go.** Drawn uniformly, four points in four hundred landed
where the hull and the exact shadow disagree, and a reverted fix passed
(review). Now:

- a third of the points go anywhere;
- a third go in an outline's notches (its own hull, outside it);
- a third go in the hull of the outline and its swept copy.

Each test must count at least 50 samples on which the hull would have been
wrong (measured: 77 and 88 over 800 scenes).

**Edges.** A sample where moving the point 6 cm, in any of eight directions,
changes the model's answer lies on the shadow's edge. It is left out and
counted, and there must be fewer than one in ten. Only the point moves. The
first version also nudged the sun by 0.3°, which moved a low shadow's tip by
metres and hid a 3% error in its length.

Where the 5 cm ray disagrees with the model, it is marched again at 2 mm before
anything is judged. A random star has corners sharper than the step, and the
coarse ray crossed one between two steps and read it as air.

**Mutations, each caught** (made in a scratch copy, 2026-09-22):

| Mutation | Caught by |
|---|---|
| every outline convex (the hull as it was) | both ray tests |
| `near_edge` reading only the first and last crossing (the bug fixed 2026-09-22) | both ray tests |
| the grid's reach saying "shaded" when the ray misses the outline | the cell test, the L-corner grid check, the convergence pin |
| every shadow 3% longer | the point test, the convergence pin |

**The plan's case** (plan 03, E1) is fixed in this file: a 10 × 10 m house,
9 m high, with its north-east quarter open, in Wuppertal. A bed in the open
quarter reads **3.98 h**, by the bed's own sample and by the grid alike, and
**0.00 h** under the hull.

## 3. Is the sampling fine enough? (`tests/test_light_convergence.py`)

`solar/light.py` said of its one day in ten, every half hour, "fine enough that
the answer stops moving". The suite answers each scene twice: at the model's
own sampling, and with the same shading test asked every five minutes of every
day. Five minutes against two moves the answer by less than 0.02 h, so that is
the converged answer.

Five scenes in Wuppertal: open ground, beside and behind a 9 m house to the
south, the corner of the L, and a hedge that takes the morning. Worst errors
(model minus converged):

| Sampling | Season | A month (April, June) |
|---|---|---|
| today: 30 min; the season every 10th day, a month every 5th | **0.22 h** low beside the house, 0.13 h in the open | **0.46 h** (April, beside the house) |
| 10 min, every 5th day (feature 2 as planned) | 0.04 h | 0.34 h — a month already has every 5th day |
| 10 min, a month every 3rd day | — | 0.23 h |
| 10 min, a month every 2nd day | — | 0.10 h |

**Where the error comes from.** Split on the same days, most of it is the
days skipped, not the half-hour steps:

| | Half-hour steps alone | Days skipped alone | Both, as today |
|---|---|---|---|
| Season, open ground | 0.02 h | 0.06 h | 0.13 h |
| April, beside the house | 0.08 h | 0.29 h | 0.46 h |

So feature 2 must move a month to every 2nd day as well as the season to 10
minutes and every 5th day. The wave's plan says so since this review.

**Bars:** 0.1 h for the season, 0.2 h for a month. Both tests over the model's
own sampling fail today. Each is marked as a **strict** expected failure,
limited to an `AssertionError`, that names what makes it pass. A strict
expected failure turns the build red on the day it starts passing, so the
mark comes off with the change that earns it.

**The pin.** A fourth test holds every number the two marked tests compute
against the measured table, ±0.03 h: 5 scenes × (season, April, June). A
first version pinned only 2 of the 15, and a mutant that read the L's corner
5.8 h too dark in June stayed green behind the marks (review). Each value goes
when its mark goes.

The suite costs about 4 s and runs with every change, as the plan asked.

## Business rules

1. Nothing in this wave counts as more accurate unless one of these
   instruments says so.
2. A model feature adds its own geometry to the ray instrument before its code.
3. The convergence bars do not move to fit the model; the sampling moves to fit
   the bars.
4. The reference is an independent implementation, frozen as data, never the
   model's own earlier output.

## Security

Tests only: no route, no stored data, no network. The reference script runs
by hand with pvlib and never in CI.
