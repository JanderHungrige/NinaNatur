---
id: 120-a-roof-casts-as-a-roof
title: A Roof Casts as a Roof — the Shadow of the Planes the Model Already Draws
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-26
wave_status: active
depends_on: [116-no-hull, 117-room-to-compute, 94-which-way-the-ridge-runs]
relates: [93-where-the-roof-came-from, 98-what-the-style-has-not-drawn, 99-paper-bleed-and-a-real-shadow, 119-energy-not-hours]
source_files:
  - ninanatur/garden/casting.py
  - ninanatur/solar/day.py
  - ninanatur/solar/field.py
  - ninanatur/garden/ground.py
  - ninanatur/garden/lightgrid_cost.py
  - ninanatur/garden/lightgrid_load.py
  - scripts/measure_roofs.py
  - scripts/measure_neighbour_cost.py
  - ninanatur/solar/raster.py
  - ninanatur/solar/convex_parts.py
  - ninanatur/garden/roofshape.py
  - ninanatur/garden/roofs.py
  - ninanatur/garden/lightview.py
  - ninanatur/solar/shading.py
  - ninanatur/solar/light.py
  - ninanatur/solar/sweep.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/garden/lightgrid_extent.py
routes: []
models: []
test_files:
  - tests/test_roof_shadow.py
  - tests/test_roof_cells.py
  - tests/test_roof_lines.py
  - tests/test_light_model_version.py
  - tests/test_light_grid_cost.py
  - tests/test_roof_direction.py
data_flow: writes-existing
last_synced: 2026-09-28
status: complete
phase: all
mdd_version: 11
tags: [solar, shadow, roof, gable, hip, pent, convex, raster]
path: Garden/Light/Roofs
integration_contracts:
  - from: 117-room-to-compute
    function: Part as a convex solid the ray is cut against
    when: a caster stops being a prism
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The plan's decorative drop shadow is one offset per object (`api/gardens.py`), so it still uses the block's averaged height; a roof cannot be an offset. The day's playback (`/shadows`) draws the roof exactly — it did not until the review of 2026-09-28 made it cast through `garden.casting`, as the light model does."
  - "A roof's planes come from the smallest enclosing rectangle of the whole footprint (doc 94), so an L-shaped house has one ridge over both wings, not a roof per wing: the walls facing the corner the wings enclose stand up to the roof above them — on the tests' L 9 m along the one under the ridge, falling from 9 m to the eaves along the other — and cells in that corner lose up to 0.84 h a season against the 7 m block (0.5 m cells; the 0.71 h first written here did not reproduce, review of 2026-09-28). Never below the eaves: over the footprint the rectangle's planes cannot fall that low, which is why no eaves 'skirt' is needed."
  - "On a hipped house that is not a rectangle the plan draws each hip to the house's own nearest corner (doc 98, at the owner's request of 2026-09-21), while the model's planes are the rectangle's: there the drawn hip and the crease the light model uses are up to a couple of metres apart. On every rectangle they are the same line."
  - "`RISE_KEPT` still answers for mixed, other and unknown roofs and for a pent whose fall nobody has surveyed — every shape the model cannot place. Their cells stand on a flat roof at the ridge while their shadow keeps the guess, as before this feature."
  - "A garden of many roofed houses drawn *on* its plot can run past the 5 s budget whatever the cell: a plane costs per plane, not per cell (36 hipped houses: 6.6 s at 5 m). The estimate says so rather than promising; houses round the plot, the common case from the map, stay within it."
sister_projects: []
---

# 120 — A Roof Casts as a Roof

## Why

`roofs.RISE_KEPT` is a shape guess: a gable keeps half its rise, a hip four
tenths, a pent six, a mixture eight. The building then casts as a block of
that one height. But a gable's shadow is **ridge height along the ridge and
eaves height across it**, and one number is wrong in both directions — too
tall where the roof has already fallen away, too short under the ridge.

The planes are not missing. `roofshape.surface_of` has built them since Wave
21 and the plan draws their ridges and hips (docs 94, 98). They were only ever
asked what the sun does *to* the roof, never what the roof does to the garden.

## A caster is a convex solid

The raster cuts the ray from a cell towards the sun against each part (doc
117). Parameterised by horizontal distance t, a point on that ray is

    P(t) = (x + sun_x·t, y + sun_y·t, z + t/cot)

going towards the sun (sun_x, sun_y), and a half-space n·X ≤ d cuts it at
t·(n_x·sun_x + n_y·sun_y + n_z/cot) ≤ d − n·P(0): one more bound on the same
interval, whichever way the plane leans. A vertical wall is the case n_z = 0, and the prism's flat top is
n = (0, 0, 1) with d = top — which is exactly the `t_hi` the raster already
computes. So nothing about the sweep changes but the list of planes.

**A tent over a convex footprint is convex**, so a house stays one part: its
walls, its roof's planes, and its base. The parts are what a grid costs (doc
117), and this feature adds planes, not parts.

## Which roofs, and what they are

`roofshape.RoofSurface` is a ridge, a span and two heights. Its planes fall
from the ridge at the pitch (`planes()`):

- **gable** — two planes; the ends are vertical gable walls, which the
  footprint's own walls already are.
- **hip** — four, the end pair rising to the ridge's endpoints; on a square
  the ridge is a point and the roof a pyramid.
- **pent** — one, falling the way the survey said (doc 94). (It carried a
  second, never-binding plane at first, costed like a wall.)
- **gable or hip too shallow to pitch** (under `MIN_PITCH_DEG`) — no planes,
  cast at the ridge: the height its cells stand on.
- **flat** — the top plane, as ever.
- **mix, other, unknown, and a pent without a surveyed fall** — no planes:
  they keep `RISE_KEPT` and cast as prisms, because nobody has said what
  shape they are.

One rule decides this, `garden.casting.casting`, which the light model and
the day's playback both call — the playback kept a copy of the old rule and
drew a block where the map counted planes, until the review of 2026-09-28.

The surface the sun is asked about *on* the roof becomes the same planes'
lower envelope, so the roof a cell stands on and the roof that casts are one
geometry. Where the ridge is the full length of the building this changes
nothing; at a hip's corners the old distance-to-a-segment surface dipped
conically below the planes — at (4, 4) on the tests' hip it said 5.0 m where
the plane stands at 5.8 — and the planes are what a hip is. The plan draws
the same ridge and, on a rectangle, the same hips (doc 98 bends a hip to the
house's corner on other outlines; known issues).

**The drawn shadow is the counted one** (doc 116). Over each of the
footprint's convex parts — the pieces the model casts — the solid is convex,
so its shadow is the hull of the shadows of its corners, each cast by its
own height, and of its crests: every line where two planes meet, cut to the
part, and the ridge itself, whose ends are a hip's highest points. The first
version cast the corners and the ridge's crossings of the walls alone: an
L's hull filled its notch, and every hip was drawn at its eaves.

**The slow reference** (`solar.field`, doc 117) casts prisms and now refuses
a roof rather than quietly casting it as a block; a roof's own reference is
`shading.is_shaded`, arithmetic written apart from the raster and held to it
on flat ground and on terrain.

## What moved

`python -m scripts.measure_roofs` prints this: a house 12 × 8 m south of the
beds, ridge 9 m, eaves 5 m, running east–west, its north wall at y = −5;
points on its axis north of that wall; Wuppertal, the season. The block's
guess is 7.0 m for the gable, 6.6 for the hip, 7.4 for the pent.

| North of the wall | Gable | Hip | Pent falling north | Pent falling south |
|---|---|---|---|---|
| 1 m | 4.00 → **4.00 h** | 4.00 → **4.00 h** | 4.00 → **4.00 h** | 4.00 → **4.00 h** |
| 3 m | 6.45 → **8.14 h** | 6.57 → **8.14 h** | 6.38 → **8.14 h** | 6.38 → **6.38 h** |
| 5 m | 9.87 → **10.93 h** | 10.06 → **10.93 h** | 9.69 → **10.93 h** | 9.69 → **8.91 h** |
| 8 m | 11.81 → **12.30 h** | 11.94 → **12.35 h** | 11.78 → **12.62 h** | 11.78 → **11.32 h** |

A point three metres behind a gabled house gains an hour and three quarters,
and sees four fifths of the sky where it saw three quarters: the roof has come
down by the time it reaches the wall, and the block stood at 7 m all the way
across. A pent roof whose high edge faces the beds loses instead — 9.69 h
against 8.91 five metres out — which is the same error the other way round,
and the reason a mean was wrong in both directions. (The table's first version
named these distances 2, 4 and 7 m; the numbers were right, the distances were
not.)

**Cost.** A gabled house is still *one* part, with two planes; an L-shaped one
is two, as its footprint always was. But a plane is one more cut of the ray at
every moment its part is asked about, so it costs about what a wall does —
per plane, not per cell: 17 ms a plane on the plot and 10 round it, and
0.0007 ms a cell a plane beside (`lightgrid_cost`), fitted at forced cells from
5 m to 0.5 m on 36 houses as blocks against the same houses as gables and
hips. The first version priced the planes per cell alone, and 36 hipped houses
were estimated at 4.7 s and took 7.1. On houses round the plot — the map's
neighbours — 36 gables take 3.9 s at 0.5 m. Cutting a part's planes all at
once was tried and was slower: with two to four planes, the masks cost more
than the calls they saved.

The claim that the estimate bounded every garden measured did not survive the
review of 2026-09-28: 36 neighbours with their near walls 1 to 9 m past the
grid's edge — blocks as much as gables, a price older than this feature — took
1.8 s at 2 m cells where the far price said 1.0. A neighbour within its own
height of the grid throws its shadow in whenever the sun is below 45°, not
only while shadows are long, so it now adds 35 ms to the far price
(`lightgrid_load`, `REACH_PART_MS`); from 11 m out the far price held and still
stands alone. The same rings, and the crowns' cases, hold now
(`scripts.measure_neighbour_cost`, `scripts.measure_crown_cost`); a garden
from the map with its own gable, 30 neighbours and 22 trees still gets 0.5 m.
And the parts a many-cornered roof is cast through are found by looking each
neighbour up, not by searching every pair: a 500-corner gable's day of
shadows took 18.7 s in the serving process, and takes 0.8 (doc 117).

**The model's older pinned answers do not move** — their houses have no roofs
— and two were added behind the same house with a gable on it, one where its
eaves decide and one where its ridge does: 2 m north, 5.80 h and sky 0.731
where version 26.4's block said 5.71 h and 0.689; 7 m north, 11.75 h and
0.933 where it said 11.60 h and 0.925.

## Business rules

1. One geometry: the roof that casts is the roof the cells stand on, drawn
   in the day's playback as it is counted; the plan draws its ridge and, on a
   rectangle, its hips (doc 98 bends a hip to the corner on other outlines).
2. One rule casts every element, for the light model and the playback alike
   (`garden.casting`).
3. A shape nobody identified keeps its prism and its stated guess, and
   `RISE_KEPT`'s docstring says that is all it is for.
4. Every change to what the model answers raises `MODEL_VERSION`.

## Security

No new route or input. A part gains planes, not parts, and the planes are
priced as what they cost (`lightgrid_cost`), so the budget and the refusal
at four times it still bound a garden's grid.
