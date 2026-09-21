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
  - ninanatur/garden/lightgrid_extent.py
  - ninanatur/garden/lightcells.py
  - ninanatur/garden/lightgrid_store.py
  - ninanatur/garden/roofshape.py
  - ninanatur/garden/roofs.py
  - ninanatur/garden/lighting.py
  - ninanatur/api/light.py
routes:
  - GET /api/v1/gardens/{token}/light
  - POST /api/v1/gardens/{token}/light
models: [light_grid, element]
test_files:
  - tests/test_light_grid.py
  - tests/test_light_grid_extent.py
  - tests/test_roof_light.py
  - tests/test_roofshape.py
  - tests/test_shading_is_ray_tracing.py
  - tests/test_roofs.py
  - tests/test_light_api.py
data_flow: mixed
last_synced: 2026-09-21
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

The same computation, asked at many points. The garden is covered with square
cells (see *What the grid covers*) and each one gets its own mean daily sun
hours over the light season (1 March to 31 October, every tenth day, every half
hour above 5° altitude — 1,200 sun positions).

That only became affordable because `solar/field.py` stopped redoing the work
per point. The sun positions and the shadow polygons of a season are the same
for every cell in the garden; they are computed once, kept with their bounding
boxes, and each point is then a run of cheap containment tests. 125 ms per point
became 1.09 ms — 85× — which is what turns 1 point into 600.

Cell size comes off a ladder (0.5, 1, 2, 3, 5 m) and is chosen so the grid fits
a time budget (see *How fine the grid is*). A large plot gets a coarser grid
rather than a long wait. Nothing finer than half a metre is offered, because
most building heights in this model are assumed and a 10 cm grid would claim
more than the model knows.

A bed's own light value is now the mean of the cells its polygon covers, not a
point sample. Raised beds and beds narrower than one cell fall back to the point.
`mean_over` only asks the cells inside the bed's bounding box, widened by one
cell each way (2026-09-21): the answer is the same to the last bit
(`tests/test_light_grid_extent.py` checks it against the old full scan), and a
bed no longer costs a point-in-polygon test for every cell of the garden.

## What the grid covers

**The garden, not the neighbourhood** (`lightgrid_extent.grid_extent_of`, since
2026-09-21). The box is the plot outline (the `garden` element), every bed
wherever it is, and whatever the gardener drew that stands up, with
`GRID_MARGIN_M = 5` around it all. Left out: streets, anything without a height,
and whatever the import or a survey brought.

It used to be `extent_of`, everything on the plan. A garden made from the map
carries its neighbours' houses up to 50 m out (doc 63) and every street at the
full length Overpass sends, so a 25 × 40 m plot became a grid of 200 × 115 m or
more, and the budget answered with 3–5 m cells. The owner's check on 2026-09-21
said so: the raster is too coarse.

The neighbours still cast their shadows. They stay in the obstacles
`compute_grid` is handed; only the cells over their land go, and with them the
painted roofs next door.

**Drawn or brought** is read from where an element's numbers came from. The map
import writes `roof_source = 'osm'` on every house, and a survey writes
`surveyed` or `measured` — only ever over a height the gardener did not type. An
element whose `height_source` and `roof_source` are both still `user` came from
the drawing tools. An accepted tree from the laser survey (`measured`) counts as
found, like the neighbours. The one known miss: a neighbour's house saved
through the element form before Wave 21, which wrote `user` into the height on
every save, reads as drawn and widens the grid as it always did.

**Without a plot** — mostly gardens drawn by hand — nothing tells the garden's
ground from the neighbours', so every standing element counts, imported or not,
still without streets and heightless surfaces, and no margin is added: those
gardens' outermost house or hedge already is the edge, and 5 m more on every
side would have doubled a small garden's cells. A plotless garden of surfaces
alone — a lawn, a path — is covered by its surfaces; only a garden of streets
alone has no grid, and a map stored for a garden that can no longer be covered
is removed on the next press rather than left reading stale for ever (review,
2026-09-21).

`extent_of` is kept, unchanged, for cropping the relief (`GET /terrain`).
`check_extent`, the refusal, is asked about the box the grid actually covers:
streets reaching across the whole ±2 km range no longer make a garden "too
large", while a shed drawn at the far corner still does.

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

## A cell under a building is answered on its roof

Not on the ground beneath it. That ground gets no sun at all — a building shades
its own footprint every hour of every day — and reporting it is true and
useless: a plan shows the roof, and the roof is in the sun.

The surface comes from `garden/roofshape.py`: a ridge running along the long
axis of the footprint's smallest enclosing rectangle, two pitches falling from
it, and the ridge shortened by one span at each end for a hip so its ends slope
too. The ridge direction is the one assumption — nothing in the stored data
carries it — and where it cannot be made honestly it is not made: a pent roof
has one pitch and nothing says which way it falls, so it is left unpitched, and
so is any shape nobody has identified.

The pitch reaches the sun through `slopes.ring_for`, the same function a
hillside uses. A plane of slope *s* climbing towards *a* stands at
`atan(tan(s)·cos(θ−a))` in direction θ; on a roof "uphill" is towards the ridge,
so a point on the north pitch has its own roof between it and the southern sky.
That is precisely why a north pitch is the darker one.

Two consequences worth naming:

- **A building must not shade its own roof.** Its footprint is inside its own
  shadow at every moment of every day, so the query drops that one element —
  `Obstacle.owner` and `halves_at(ignore=)`. Without it every roof came back as
  darkness, which is exactly what the map used to show.
- **A roof is flagged, not folded in.** `mean_over` and `max_hours` skip roof
  cells: nothing is planted up there, and a sunny roof would otherwise set the
  scale for the garden below it.

`hours` is `null` only for a building whose height nobody has recorded — skipped
by the shading model since Wave 8, and with no surface to stand on.

Only roofs. A tree is not roofed: there is real ground under it getting real
dappled sun, and somebody planting under an apple tree is asking about that.

## How fine the grid is

`cell_size_for` picks the finest cell whose grid fits `GRID_BUDGET_S`, five
seconds. It was a flat 600-cell cap, from when every write recomputed the light;
nothing recomputes on a write any more, so the limit can be a time rather than a
count — which is the right shape, because a cell costs what the obstacles around
it cost. Measured: 0.24 ms with three buildings, 1.9 ms with forty.

What the budget buys depends on the box, quadratically: half the cell is four
times the cells. From the code's own cost model, for a 25 × 40 m plot made from
the map with 25 houses around it and three streets of 200 m
(`cells × (0.1 + 0.05 × obstacles) ms`, 26 obstacles):

| Grid covers | Box | Cell | Cells | Estimate |
|---|---|---|---|---|
| everything (before 2026-09-21) | 200 × 115 m | 3 m | 2,613 | 3.7 s |
| the plot and 5 m | 35 × 50 m | 1 m | 1,836 | 2.6 s |
| the plot and 5 m, at 0.5 m | 35 × 50 m | 0.5 m | 7,171 | 10.0 s |

With 600 m streets the old box was 600 m wide and got 5 m cells; with 40 houses,
5 m as well. Both now get 1 m. A garden drawn by hand without a plot keeps the
box it had, minus streets and surfaces — a 24 × 33 m one with three obstacles
stays at 0.5 m.

The estimate is low for a plot among many houses: every cell in it sits under
somebody's shadow for part of the day, where the old box had cheap cells at its
edges. Timed on a busy machine (load 20–30 on eight cores), the 25-house case
took 4.6 s at 1 m against 5.4 s at 3 m before, and a 40-house one 6.2 s at 1 m
against 3.4 s at 5 m. The model's constants were measured over whole
neighbourhoods on 2026-09-07; re-measuring them inside plots is open.

## One month instead of the season

`GET .../light?month=3` narrows the average from the whole March-to-October
season to one month, computed on the spot and never stored. The season is
sampled every tenth day and a month every fifth, so a month costs about a
quarter of a season — cheap enough to answer live, and far cheaper than storing
eight grids per garden would be to keep up to date.

Winter is a 422. The whole light model stops at October: a plant's December does
not decide where it can live, and a December map would drag every German garden
into shade.

## Staleness

The map is expensive enough to store, and a stored map can be wrong. It is
therefore kept next to a **signature** of everything that can move a shadow —
latitude, longitude, and each element's id, kind, height, roof, eaves, height
above ground and outline, plus each planting that casts a shadow, by species,
count and position. Since 2026-09-21 (owner's check #9) that is only the species
`lightview.shading_taxa` returns — those `canopy.shades` makes crowns of, the same
plants `_planted_obstacles` shades with — so a perennial planted from the list
leaves the map current and a shrub makes it stale
(`tests/test_light_signature_plantings.py`). All three places that make a
signature pass that set: `lighting.recompute_light`, `light_state` and, through
it, `api/light.py`.
`stale` is that signature disagreeing with the garden as it stands.

Since 2026-09-21 it also carries the grid's own shape: `grid_model()` — the
extent rule's number (`EXTENT_RULE`), the margin, the ladder, the budget and the
cost constants — and the box `grid_extent_of` gives. A map laid over another box
is out of date even where no shadow moved, so every map stored before the grid
shrank to the garden now reads stale, and the button gives the finer one. The
box is in it rather than implied by the outlines because it also reads where an
element came from: a neighbour's house the gardener makes their own joins the
box, and the map says so. Whoever next changes what the grid covers raises
`EXTENT_RULE`; a changed margin, ladder or budget stales the maps by itself.

A signature rather than a list of actions that ought to invalidate it. A list
has to be remembered at every new endpoint, and the first one somebody forgets
is silent. Renaming a bed does not move a shadow, and the signature knows that
without being told.

`POST .../light` recomputes on demand. It began as belt as well as braces — a
way for somebody to fix their own map without knowing why it was wrong — and is
now the **only** path.

Writes stopped relighting the garden on 2026-09-07. Every mutation used to do
it, so the plan could never disagree with its own obstacles, and that was right
while a garden was a handful of shapes. Wave 19 gave buildings measured heights
and the gardens people draw got big: 40 houses across 150 m costs **2.5 s** a
relight, against **3 ms** to store the bed. Drawing five beds meant thirteen
seconds of waiting for an answer nobody had asked for yet.

The signature is what makes that safe rather than sloppy. A map that is quietly
out of date is worse than one that admits it — and this one admits it, without
anybody having to remember which endpoints ought to have invalidated it. The
flag was already built and merely decorative; it is now load-bearing.

## Why it is trusted

The model is a projection, not a ray tracer: a footprint swept along the sun
vector by `height / tan(altitude)`, then the convex hull of both. That is fast
and it is an approximation, so it is checked against the thing it approximates.
`tests/test_shading_is_ray_tracing.py` marches a ray in 3D from a point towards
the sun and asks whether anything blocks it, over 263 random scenes, and the two
agree. Overlapping shadows, a tree behind a taller house, and a raised bed
behind a fence are each written out as their own case.
