---
id: 107-the-cloud-under-the-crown
title: The Cloud Under the Crown
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [102-which-tiles-and-whose, 103-a-tile-not-a-service, 105-every-roof-in-the-country]
relates: [84-canopies-found, 106-which-source-said-so, 07-solar-geometry]
source_files:
  - ninanatur/geo/pointcloud.py
  - ninanatur/geo/tile_zip.py
  - ninanatur/geo/cloud_store.py
  - ninanatur/garden/cloud_sync.py
  - ninanatur/geo/tile_cache.py
  - ninanatur/ingest/schema_computed.py
  - pyproject.toml
routes: []
models: [cloud_window]
test_files:
  - tests/test_pointcloud.py
data_flow: mixed
last_synced: 2026-09-20
status: complete
phase: all
mdd_version: 11
tags: [point-cloud, laz, lidar, crown-base, vegetation, buildings, nrw, bayern, thueringen, sachsen, brandenburg, budget]
path: Geo/Point cloud
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 107 — The Cloud Under the Crown

## Purpose

A surface raster says how tall the thing standing here is. It cannot say what
the thing is, and it cannot see underneath it — doc 84's complaint that "a
marquee and a tree read the same" is a property of that product, not of the
reading.

The points the raster was made from can do better, because a tree lets light
through and a roof does not. A crown returns at its top, in its middle and on
the ground beneath it; a roof returns once. From that this reads three layers —
ground, surface, and **where the canopy starts** — the last of which nothing
else in this project knows and the shading model needs: a crown is not a
cylinder standing on the soil, it is a lamp on a stick.

## What the tile actually contains

The plan's recipe was: buildings from class 6, vegetation from classes 3 to 5,
crown base from the vegetation points. **NRW's tile has none of those classes.**
Measured on the verified tile (`3dm_32_347_5647_1_nw.laz`, 2026-09-20):

| Class | Share | What it is |
|---|---|---|
| 2 | 76.2 % | ground |
| 20 | 15.7 % | reserved, and in this file mostly near the ground — median 0.5 m above it, flat within a cell |
| 1 | 7.2 % | unclassified, and in this file everything tall — median 4.3 m, 83 % above 2 m |
| 9, 17, 18, 24, 26 | < 1 % | water, bridges, noise |

8,294,864 points over a square kilometre — **8.3 points per m²**, at the top of
the range the availability list promised. But no building class and no
vegetation class: what stands is simply unclassified.

So the separation the feature exists for cannot come from the cloud. **It comes
from the building model** (doc 105): a return inside a surveyed LoD2 footprint
is a roof, and everything else that stands is a crown. Wave 25 built that
reader two features ago, which is the reason this one is possible at all — and
it means a state with a cloud and no building model gets heights and no crown
bases, and says so rather than calling every roof a tree.

## The three layers

Binned straight onto the garden's own axes — the points are transformed once,
rather than rastered in UTM and resampled, because UTM grid north is up to 2.3°
off true north here (doc 17):

- **ground**: the lowest class-2 return in each cell.
- **surface**: the highest return of any kind.
- **crown base**: the fifth percentile of the *standing* returns in a cell —
  above a metre, outside every footprint, and only where the cell holds at
  least three of them. The fifth percentile rather than the minimum so one
  stray return under a crown does not put the canopy on the ground; three
  returns rather than one so a single measurement is not a canopy.

**The ground is filled in under the things standing on it.** A laser sees no
ground beneath a roof, so those cells are empty by construction — 4 % of the
verified window. Without filling them a house has no height at all, because its
height is measured against a cell that cannot have a value. Each pass gives an
empty cell the mean of its filled neighbours, so a hole closes from its rim
inwards, and fifty passes close a fifty-metre building.

## The cell is as fine as the density earns

Half a metre needs about eight points per square metre to hold one point per
cell. Below that the honest raster is a metre, and the window records which it
got along with the density it saw. The verified window came out at 7.6 points
per m² over its 300 m — just under — so it is a metre, which is the rule
working rather than a disappointment.

## The budget, measured

The plan's numbers were 1–2 minutes a garden and under 300 MB. On the verified
tile, from the file on the volume:

| | |
|---|---|
| tile | 34,967,590 B, fetched in 4.0 s |
| window | 0.8 s |
| peak memory | **186 MB** (44 MB of interpreter, numpy and laspy; 142 MB of reading) |
| ground known after filling | 100 % |
| crown base found | 2.7 % of cells, median 2.9 m, p90 6.2 m |
| stored window | **66 kB** for three layers |

Two things brought the memory inside the budget. The tile is **streamed from
the file on the volume** rather than handed over as bytes — the largest tile in
the index is 445 MB, and holding it would be the whole budget before a point is
read. And the reader hands over a quarter of a million points at a time: a
million cost 226 MB of peak for the same tile, and 250,000 is no slower.

## What it costs to keep

Three layers of a 300×300 window as 16-bit centimetres, deflated: 66 kB per
place, keyed by place like the terrain so a street shares one. The tile itself
is not kept — the cache may drop it the moment the window exists, which is what
the cap is for (doc 103).

## laspy and lazrs

LAZ is LAS packed with an arithmetic coder, which is not a thing to
reimplement. `laspy` (BSD-3) reads the format, `lazrs` (Apache-2.0) unpacks it,
both permissive, and the Rust backend is what makes eight million points 0.4 s
rather than a minute. They are pinned with hashes in `requirements.txt` **and**
in `requirements-dev.txt` — the supply-chain test caught that the image would
otherwise ship a library CI never tested.

## Four more clouds, and one that classifies itself

**2026-09-20.** Bayern, Thüringen, Sachsen and Brandenburg join Nordrhein-
Westfalen. Three of the four arrive zipped, so the member is streamed out of
the archive to a file beside it and read from there — the reader still never
holds a tile, which is what kept the budget at 186 MB.

**Bayern's cloud is classified where NRW's is not**: class 6 for buildings and
class 20 for plants, on the published scheme and on two decoded tiles. Twenty
is not the ASPRS vegetation class, so a reader looking for 3, 4 and 5 finds
nothing — which is exactly the sort of thing this doc exists to record. Munich
measures 20.4 points per m² against the state's guaranteed 4, so the cell
there is the half-metre one.

The reader **does not use those classes yet**, and that is deliberate. The
footprint rule works in every state with a building model, Bayern included,
and one rule that holds everywhere beats two that disagree at the seam. What
the classification buys is the states that publish a cloud and *no* LoD2, and
there are none of those in the registry today.

Brandenburg is flown over about 44 % of its area, so a missing tile there is a
place nobody has flown rather than a portal having a bad day. The cloud path
already reads that as "no window", which is the right answer either way.

## Business Rules

1. **The classification is not trusted to say what a thing is.** Ground is
   ground; everything else is decided by the building model or by geometry.
2. **A tile is streamed from the volume**, never held, and never kept once the
   window exists.
3. **The cell size follows the density**, and the window says which it got.
4. **A crown base is only claimed where there is a canopy to measure** — three
   standing returns, outside a footprint.
5. **The laser is a credit like any other** (doc 106), even under
   dl-de/zero-2-0, which asks for nothing.

## Dependencies

Doc 102 for the source, doc 103 for the cache, doc 105 for the footprints that
tell a roof from a crown, doc 84 for what this replaces.

## Security

The tile's address is the registry's template and two integers; the cache key
is the same. The reader is given a path under the cache root, and the window it
returns is arithmetic over numbers.

## Known Issues

- **One tile per garden.** A window reaches 150 m and a tile is a kilometre, so
  a garden within 150 m of a tile line loses what lies beyond it. At up to
  445 MB a tile, fetching the other three is not the trade the terrain's is.
- **Nothing reads the crown base yet.** It is stored, credited and tested; the
  shading model starts using it in Wave 26, which is what it was asked for.
- **Bayern's own classification is not used** (above): the footprint rule
  covers it, and a second rule would only differ at the seam.
- A zipped cloud costs the volume twice for a while — the archive and the
  member written out of it — until the cap drops the older of the two.
- **Five clouds are in the registry**, and the rest have been asked. Hessen
  charges for its; Berlin's is nine bundles of up to 50 GB packed with
  deflate64; Sachsen-Anhalt publishes two areas rather than a state;
  Mecklenburg-Vorpommern's tiles answer 401; Niedersachsen, Baden-Württemberg,
  Bremen and Saarland sell theirs or publish nothing per tile (doc 102).
  Rheinland-Pfalz's is verified at 338 MB a tile and waits on its ground.

## Bugs
