---
id: 81-a-house-with-a-measured-height
title: A House with a Measured Height
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-19
wave_status: active
depends_on: [80-which-models-and-whose, 69-a-window-of-ground]
relates: [80-which-models-and-whose, 63-neighbours-from-the-plot]
source_files:
  - ninanatur/geo/surface.py
  - ninanatur/geo/measure.py
  - ninanatur/geo/terrain.py
routes: []
models: []
test_files:
  - tests/test_surface.py
  - tests/test_measure.py
data_flow: reads-existing
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [ndom, dom, buildings, heights, erosion, statistics]
path: Map/Buildings
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Erosion is towards the centroid rather than a true polygon offset; a long thin building over-erodes and is then refused by the cell count rather than measured badly."
  - "A garage of roughly four metres across is the smallest thing measurable: below a 2.2 m half-width the eroded core keeps fewer than a dozen cells."
  - "Nothing yet uses these heights — the surroundings model still assumes. That is feature 3."
---

# A House with a Measured Height

Feature 1 of Wave 19. Every building height in this model is a guess:
`height` where OSM happens to carry it, `building:levels × 3 m` where it carries
that, and a per-garden assumption where it carries neither. Wave 17 stood those
guesses on measured ground, which is the wrong way round.

## The plan said LoD2 tiles. Feature 0 said otherwise

The wave was planned around downloading CityGML tiles. Feature 0 then found that
**eight states publish a surface model as a bbox coverage service** — the same
eight that publish terrain — while LoD2 is a tile download verified for one.

So height comes from the surface model: one request, no tiles, in every state
that has terrain. LoD2 keeps the job only it can do, which is the roof shape.
That is feature 2.

## Two products, one subtraction, easy to do twice

Nordrhein-Westfalen and Mecklenburg-Vorpommern publish an **nDOM** — already
differenced, so a value is height above ground. The others publish a raw
**DOM** in metres above sea level, and `surface.py` subtracts Wave 17's terrain
window itself.

Subtracting from an already-normalised model gives negative buildings, and a
test asserts it does not happen. The lookup is by **position**, not by index:
NRW's nDOM is half a metre where its DGM1 is one, so the two rasters do not
share a grid and never will.

## Eroding the footprint is the feature

The naive version averages the surface inside an OSM footprint. It does not
work, and the way it fails was measured while this wave was planned: a 30 m²
outbuilding read **17.0 m** because a beech hangs over it, and a 60 m²
kindergarten read 6.5 m median against 12.8 m at the 95th percentile.

An OSM footprint is the building's ground plan. The surface model records
whatever is *above* that ground plan, which on a small building is often
somebody's tree. So:

- **Erode by 2 m** before sampling. A crown overhangs a roof edge by more than
  that often enough; eroding further would eat a garage whole.
- **Require a dozen surviving cells.** Below that the answer swings on which of
  them a branch touched — the garage measured from four cells is exactly the
  case that produced 17 m. Measured: a 2.1 m half-square erodes to 0.69 m and
  keeps nine cells, 2.2 m keeps sixteen, so the smallest measurable building is
  about four metres across.
- **Take the 75th percentile**, not the median and not the maximum. A pitched
  roof spans eaves to ridge across its own footprint, so the median sits halfway
  up it and understates what casts the shadow; the maximum is an aerial, a
  chimney, or the one cell a branch reached.

## And say when something is standing over it

`looks_contaminated()` reports rather than corrects. A roof is flat or evenly
pitched, so its samples cluster; a tree over one corner opens a gap between the
top of the distribution and its middle.

Reported, because the honest response to "something is over this building" is to
keep the assumed height and say why — not to guess which half of the numbers is
the roof.

## Against real data

Cologne-Lindenthal, NRW's 0.5 m nDOM, 126 OSM buildings in the window:

| OSM says | Area | Measured |
|---|---|---|
| `semidetached_house`, `building:levels=4` | 104 m² | **16.1 m** (12 m assumed) |
| `house` | 118 m² | 12.7 m |
| a row of `terrace` | ~40 m² each | 9.8–10.5 m, consistently |
| `terrace` | 47 m² | refused — did not survive erosion |

A row of terraced houses coming back within a metre of each other is the sign
worth having: they are the same houses, and the method says so.

## One test that was wrong first

The cell-count test guessed a 2.6 m half-square would be refused. It is not — it
erodes to 1.19 m and keeps 25 cells. The threshold was then measured rather than
reasoned about, and the test now names both sides of it.
