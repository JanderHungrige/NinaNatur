---
id: 104-a-horizon-for-everyone
title: A Horizon for Everyone
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [102-which-tiles-and-whose, 103-a-tile-not-a-service]
relates: [07-solar-geometry, 68-terrain-sources]
source_files:
  - ninanatur/geo/far_horizon.py
  - ninanatur/geo/tiff.py
  - ninanatur/geo/tile_sources.py
  - ninanatur/garden/terrain_sync.py
routes: []
models: []
test_files:
  - tests/test_far_horizon.py
  - tests/test_tiff.py
  - tests/test_terrain_sync.py
data_flow: mixed
last_synced: 2026-09-20
status: complete
phase: all
mdd_version: 11
tags: [horizon, copernicus, dem, cog, deflate, shading, open-data]
path: Geo/Far horizon
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 104 — A Horizon for Everyone

## Purpose

A garden in a valley loses the winter sun to the hillside long before the sun
sets. Doc 17's ring says so in 360 numbers — and only for the seven states that
run a coverage service. In the other nine the sun has been setting at the
astronomical hour whatever the hill to the south-west was doing.

Copernicus GLO-30 gives them a ring, and it is the same source everywhere: one
cloud-optimised GeoTIFF per degree of the earth, thirty metres, free, served
anonymously, no key and no state portal. Thirty metres places a ridge and not a
hedge, which is all a ring is for — it is measured at twenty metres, and the
light model already ignores the sun below five degrees.

## Verified, not assumed

**2026-09-20**, the Munich cell, end to end:

| | |
|---|---|
| `Copernicus_DSM_COG_10_N48_00_E011_00_DEM.tif` | 41,906,386 B, fetched in 4.4 s |
| decoded | 3,600 × 3,600 in 0.4 s |
| heights across the cell | 325.4 m to 726.1 m |
| **at Munich's own coordinates** | **523.8 m** |

Munich stands at about 520 m. That last line is the whole check: it says the
URL, the licence, the decoder and the arithmetic that turns a degree cell into
a row and a column all agree.

## What the reader had to learn

Two things, both small and both real:

- **Deflate.** A cloud-optimised GeoTIFF is packed with zlib (tag 8, or 32946
  under its older number); the reader knew none and LZW, which is what the
  state services answer with. One `zlib.decompress`, the existing predictor
  step, and the same bound on what a block may expand to.
- **A whole product is not a window.** `MAX_PIXELS` refuses a header claiming
  more than four million pixels — a guard from Wave 20's feature 8, and the
  right one for a 400 m window. A degree cell is thirteen million. Rather than
  loosen the guard for everybody, `read_raster` takes the limit per call and
  only this path passes `WHOLE_TILE_PIXELS`.

## One ring algorithm

The cell is geographic and the ring is measured in the garden's own frame — UTM
grid north is up to 2.3° off true north here, and a ring built on the wrong
axes is rotated by two of its own bins. So the cell's heights are read onto a
20 m UTM grid around the garden and `ring_from` walks its rays over that,
exactly as it does for a state's coverage answer. Nothing about the ring
changes because the ground arrived as a degree of the earth.

A ring reaches five kilometres, so a garden within five kilometres of a degree
line needs its neighbour's cell as well: `cells_across` says which, up to four,
and a cell that does not arrive stays NaN — which the ring already reads as
*nothing known this way* rather than as flat ground. No cell at all is None,
and the sync leaves the garden without a ring rather than claiming a flat one.

## What it costs, and why that is acceptable

Forty megabytes per degree cell, once. A cell is about 70 km by 110 km, so
every garden in a city shares one, and the cache on the volume (doc 103) means
the second garden asks nobody anything. Germany is about eighty cells; a
deployment holds the handful its gardeners live in, under the same cap.

Reading only the tiles a ring touches — the file is tiled 1,024², and a 10 km
window is one or four of them — would turn forty megabytes into about one, with
HTTP range requests against the COG's own layout. It is the better answer and
it is not built: the whole-cell fetch is four seconds and a tenth of a second
to decode, once per city. Named here so the next person does not have to
rediscover that it is possible.

## Business Rules

1. **A ring where a state has no service**, from one source that covers
   everywhere, rather than nine adapters.
2. **Thirty metres is enough for a ring** and not enough for anything else: the
   window (doc 103) is never built from this.
3. **Every cell the ring reaches**, and a missing one is unknown, not flat.
4. **The horizon carries where it came from** — `Copernicus GLO-30` in
   `terrain_horizon.source`, and the attribution the licence asks for lives in
   the registry (doc 102).
5. **The guard stays tight for every other caller**: a whole-product read says
   so at the call.

## Dependencies

Doc 102 for the source and its attribution, doc 103 for the cache on the
volume, doc 17 for the ring itself, `geo/tiff.py` for the decoder.

## Security

The URL is built from two integers — the floor of the garden's latitude and
longitude — and a fixed template. The cache key is the file's own name. The
decoder refuses a header before it allocates, and this path raises the pixel
limit only for itself.

## Known Issues

- Whole-cell fetch rather than range reads (above): 40 MB where 1 MB would do.

## Bugs
