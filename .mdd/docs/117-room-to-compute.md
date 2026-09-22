---
id: 117-room-to-compute
title: Room to Compute — the Raster, Finer Sampling, and a Model with a Version
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-26
wave_status: active
depends_on: [64-light-across-the-bed, 115-the-measuring-instrument, 116-no-hull]
relates: [07-solar-geometry, 38-polygon-shadows, 65-the-shade-switch]
source_files:
  - ninanatur/solar/raster.py
  - ninanatur/solar/raster_grid.py
  - ninanatur/solar/convex_parts.py
  - ninanatur/solar/light.py
  - ninanatur/solar/shading.py
  - ninanatur/solar/field.py
  - ninanatur/solar/day.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/garden/lightcells.py
  - ninanatur/garden/lightgrid_extent.py
  - ninanatur/garden/lightgrid_store.py
  - ninanatur/ingest/schema_computed.py
  - ninanatur/ingest/migrations.py
  - ninanatur/api/light.py
  - ninanatur/api/schemas_light.py
  - ninanatur/geo/horizon.py
  - frontend/src/components/ShadeSwitch.tsx
  - ninanatur/solar/sweep.py
  - ninanatur/garden/slopes.py
routes:
  - GET /api/v1/gardens/{token}/light
  - POST /api/v1/gardens/{token}/light
models: [light_grid]
test_files:
  - tests/test_raster.py
  - tests/test_light_convergence.py
  - tests/test_light_model_version.py
  - tests/test_light_grid.py
  - tests/test_light_grid_cost.py
  - tests/test_convex_parts.py
  - tests/fixtures/triangulation_refused.json
  - tests/test_roof_direction.py
  - tests/test_slopes.py
  - tests/test_map_selection.py
  - tests/test_concave_ray.py
  - frontend/src/components/ShadeSwitch.model.test.tsx
data_flow: writes-existing
last_synced: 2026-09-22
status: complete
phase: all
mdd_version: 11
tags: [solar, light, raster, numpy, sampling, convergence, performance, model-version, cost-model]
path: Garden/Light/Raster
integration_contracts:
  - from: 115-the-measuring-instrument
    function: test_light_convergence (season within 0.1 h, a month within 0.2 h)
    when: the sampling changes
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Hours count a grazing sun in full. With the sun counted from 3°, a north roof pitch of under about 30° catches summer sunrise and sunset that the south pitch's own ridge hides, and reads a tenth of an hour brighter; feature 4 (energy, weighted by incidence) is where it counts for what it is worth."
  - "The cost estimate takes a part whose footprint reaches into the grid's box as shading it at every moment, and any other at a fixed share; a neighbour just outside the box with a long shadow costs more than that share says. The budget is a target, not a promise."
  - "A dense import of many-cornered houses costs its parts at every moment whatever the cell size: forty neighbours of twenty-four corners take 6–8 s. The estimate knows it and coarsens the cell, which saves little."
  - "A grid is capped at 100,000 cells. The raster could compute more; the map is a list kept in the database and sent to the page."
  - "Where GEOS refuses to triangulate an outline even snapped and repaired, its parts are approximated from Delaunay triangles and a warning is logged; never reached in tests: 9,000 random tangled 50-corner outlines needed not even the retry, and the one the review found is recovered by it."
sister_projects: []
---

# 117 — Room to Compute

## Why

The field (`solar/field.py`, Wave 16) asked, point after point, whether each
obstacle's shadow covered it at each moment: pure Python per moment × obstacle
× cell. With forty houses, the 5 s budget allowed 3 m cells. And it sampled
every tenth day every half hour, which doc 115 measured: 0.22 h low over the
season and 0.46 h in an April month, mostly from the days skipped.

Wave 26's features 3–6 add sky directions, rays against roof planes and
crowns, and three times the moments. None of them fits in pure Python. This
feature pays for them first.

## The raster (`solar/raster.py`, `solar/raster_grid.py`)

**Convex parts.** The shadow of a union of prisms of one height is the union of
their shadows. So each footprint is split once into convex parts
(`solar/convex_parts.py`): shapely's constrained Delaunay triangulation, then
merged back wherever two neighbours stay convex (Hertel–Mehlhorn). An L becomes
two parts, a 24-corner outline eight. What is split is what the drawn shadow
sweeps too (`solid_of`, doc 116):

- the outline itself if it is simple;
- the shapes it encloses if it crosses itself (`make_valid`, never dropped);
- a band a centimetre wide if its corners all lie on one line, a wall drawn
  as three corners — the old field cast its shadow, so this does too.

Before splitting, corners within 0.1 µm are one corner, and spurs go. A wall
drawn as a line bevels a straight joint into two corners that differ in the
last bit; the edge between them had no direction, its normal was noise, and
its half-plane cut half a hedge out of its own shadow (review, 2026-09-22).
Walls' normals are unit vectors since, so "parallel to the sun" is an angle.
Where GEOS refuses a valid polygon ("unable to find a convex corner", on some
repaired crossing outlines), it is asked again snapped to a micrometre, then
repaired, and only then approximated, logged each time; it used to fail the
whole garden's grid. `tests/test_convex_parts.py` holds every case, and that
the parts of random outlines, crossing ones included, are convex and cover
exactly the shape.

**One part, every cell.** A cell at height z is in a part's shadow when the ray
from it towards the sun enters the part within the shadow's reach there,
(top − z) / tan(altitude). That is a Cyrus–Beck interval against the part's
walls: two bounds, one comparison, exact at any height. Per moment, each part
whose swept box reaches the grid is asked about the cells under that box,
every cell at once. Each wall's distance along the ray is divided through
before the row and the column are broadcast, so each wall costs one
addition of the grid's size.

What passes accumulates multiplicatively, as the field multiplied it: a crown
passes its share, in leaf from May to October and bare outside it. A cell on a
roof leaves its own building out. A cell's sky is its ring, read at the sun's
azimuth the way `moments_under` read it.

**One point, every moment.** The fallback for a raised bed or a bed narrower
than a cell (`bed_light_value`) turns the same test round: one point, all the
moments at once. It used to count any shadow as a wall, trees included; a
crown now passes what it passes, as it does on the map.

**The field stays as the reference.** `tests/test_raster.py` runs the same
random gardens through both — houses of any outline on ground of their own,
two crowns with bare months, terrain under the cells, per-cell skies with a
valley's ring and a hill that takes the afternoon, and a roof that leaves its
building out — and they agree on every cell, exactly (worst difference 0.0 h;
the bar is a third of a sample), in April and October with bare crowns and in
May, the first month in leaf. Leaving out the roof's owner fails it by 4.9 to
7.9 h a cell, ignoring the skies by 1.9 to 2.3 h. Walls drawn as lines — a
bevelled hedge, a wall with the editor's midpoint on it, a bent hedge — and a
shed just outside each edge of the grid are compared too.

What a crown passes is one rule (`shading.passes`), asked by the obstacle, the
grid and the point alike; it was written three times.

A guard on the shape of the computation, carried over from the field: the
parts asked about per moment are the same at 1 m and 0.5 m, and each is one
test of all the cells. It was a timing ratio, which failed on a loaded
machine.

## The cells (`garden/lightcells.py`)

`compute_grid` asks each cell what it stands on (`surface_at`: ground or roof,
its height, its sky, whose roof), and the raster does the rest. Which roof a
cell is on is asked of each roof once, for every cell at once
(`shapely.intersects_xy`). Asked per cell, a garden of forty drawn houses spent
3.6 s finding roofs. A cell on the ground with no terrain under it shares one
surface with the others; on terrain, the cells of one rounded slope and aspect
share one ring. Kept per cell, a hillside's 40,000 cells held a ring of 360
numbers each, half a gigabyte (review). A roof nobody gave a height is
unanswered and stands on the lowest ground: at zero, on a garden 150 m up, it
swept every shadow from 150 m below and tripled the cost.

## Sampling

| | Until now | Since |
|---|---|---|
| Season | every 10th day, every 30 min | every 5th day, every 10 min |
| A month | every 5th day, every 30 min | every 2nd day, every 10 min |
| The sun counted from | 5° | 3° |
| The day's frames (doc 65) | every 30 min | every 30 min, on their own step |

Doc 115's suite at the new sampling: the season within **0.044 h** of the
converged answer, a month within **0.103 h**. Its two strict expected failures
turned red the day this landed, as they were meant to, and came off, along with
the test that pinned the old errors. A month needed every second day: every
fifth, which a month already had, left April 0.34 h off at 10 minutes.

**The cutoff.** 0.71 h a day of the open season's sun lies between 2° and 5°
(plan 03, E6), and the horizon ring now says where hills really block it.
Below about 3° refraction and haze make direct sun irrelevant to a plant.

## What moved (Wuppertal)

| | Before | Since |
|---|---|---|
| Open ground | 12.48 h | 13.08 h |
| Beside a 9 m house to the south | 10.84 h | 11.56 h |
| 6 m behind it | 5.04 h (EIVE 6.90) | 5.71 h (EIVE 7.32) |
| The corner of the L (plan 03, E1) | 3.98 h | 4.35 h |

A quarter to two fifths of each change is the old sampling's bias (doc 115),
the rest the sun between 3° and 5°. Beds in the 2–6 h band read up to half a light
value brighter; above 8 h nothing changes (EIVE 9.0 either way).

**A demo that was noise.** Wave 21's test had the north pitch of a 27° roof
darker than the south by more than 0.2 h. Sampled until the answer stops
moving, the two differ by 0.09 h. With the sun from 3°, the north pitch is
0.15 h brighter at the model's sampling (0.10 h converged): it catches summer
sunrise and sunset, which the south pitch's own ridge hides. A 27° pitch loses
the noon sun only in late October, so the old 0.2 h came from the sampling. A
38° roof, as doc 65 measured, loses it in the first three weeks of March and
from late September on: north 10.8 h against south 11.9 h. The test uses that
roof now.

## A model with a version

`solar.light.MODEL_VERSION` is "26.2". It enters every map's signature
(`grid_model`), so a map an older model drew reads stale, and the button offers
the new one. That is plan 03's decision 3: *values will move, and the page must
say so, not quietly*. It is stored with the map (`light_grid.model`, an
add-only column; empty for a map from before versions) and sent with it.
The page says *Berechnet am …, Lichtmodell 26.2.* — and on a map that is out of
date, which is when it matters most, *Gezeichnet mit Lichtmodell …* or *mit
einem älteren Lichtmodell*. Every model change raises it, and
`tests/test_light_model_version.py` pins what each version answers (open
ground, behind a house, the corner of the L): change the answers without
raising the version and it fails.

## What it costs, and the cell it buys (`garden/lightgrid_extent.py`)

Measured end to end on 2026-09-22 (`compute_grid`, season, plot 25 × 40 m and
5 m of margin unless said):

| Garden | Parts on / off the grid | Cells | Time |
|---|---|---|---|
| 40 rectangular neighbours from the map, 0.5 m | 0 / 40 | 7,171 | 1.1 s |
| 40 L-shaped neighbours, 0.5 m | 2 / 78 | 7,171 | 2.2 s |
| 40 neighbours of 24 corners, 0.5 m | 6 / 352 | 7,171 | 7.8 s |
| the same, 1 m | 6 / 352 | 1,836 | 6.3 s |
| 20 rectangular houses drawn on it, 1 m | 20 / 0 | 9,600 | 2.4 s |
| 20 L-shaped houses drawn on it, 1 m | 40 / 0 | 8,342 | 4.6 s |

The field took five seconds for 1 m cells on the first garden.

What costs is each convex part asked about at every moment — a part on the
grid at all of them, one outside it only while its long shadows reach in — and
far less, the cells under its shadow. The estimate (`estimate_ms`), fitted to
those runs and rounded up:

    230 ms + 95 ms × parts on the grid + 15 ms × parts off it
           + cells × (0.008 + 0.002 × on + 0.0008 × off [+ 0.01 on terrain]) ms

It counted obstacles in the first version, which put forty neighbours of
twenty-four corners at 1.9 s; they take 7.8 (review). `cell_size_for` gives
the finest rung that fits 5 s and 100,000 cells, which is 0.5 m for an
ordinary garden. The cap on cells applies to the grid that is built: in the
first version it was only checked at 5 m, and a plain 480 m plot was given
923,000 cells, 16 MB a page load (review). `check_extent` refuses a garden
four times over the budget, or with more than 100,000 cells even at 5 m.

The constants enter the signature, as they always have.

## Business rules

1. The raster and the field agree on every cell at the same sampling; the
   field is kept to say so.
2. The sampling meets doc 115's bars: 0.1 h for the season, 0.2 h for a month.
3. Every change to what the model answers raises `MODEL_VERSION`, and the page
   names the model that drew the map it shows.
4. The cell size is the finest the budget allows, estimated from what was
   measured, never guessed down.

## Security

No new input or route. The grid's size is bounded by `check_extent` — now in
cells as well as in time — before anything is computed, and the computation
runs in the light worker's process (Wave 20).
