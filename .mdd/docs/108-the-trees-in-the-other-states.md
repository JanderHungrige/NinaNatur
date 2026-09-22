---
id: 108-the-trees-in-the-other-states
title: The Trees in the Other States
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: complete
depends_on: [102-which-tiles-and-whose, 103-a-tile-not-a-service]
relates: [80-surface-sources, 84-canopies-found, 107-the-cloud-under-the-crown]
source_files:
  - ninanatur/geo/tiles.py
  - ninanatur/geo/surface.py
  - ninanatur/garden/building_sync.py
routes: []
models: []
test_files:
  - tests/test_tiles.py
data_flow: mixed
last_synced: 2026-09-20
status: complete
phase: all
mdd_version: 11
tags: [surface-model, dom, ndom, tiles, canopies, bayern, trees, thueringen, sachsen, baden-wuerttemberg]
path: Geo/Surface tiles
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: [https://github.com/JanderHungrige/geokachel]
---

# 108 — The Trees in the Other States

## Purpose

`canopies_in` finds the trees standing around a garden by looking for tall
things in a surface model (doc 84). It has only ever worked in the eight states
that run a coverage service. In the rest — Bayern among them, thirteen million
people — a garden's neighbourhood has no trees in it at all, not because there
are none but because nobody asked.

This is the tile tier (doc 103) pointed at the other product.

## Bayern publishes twenty centimetres

Found by reading the state's own catalogue rather than guessing at paths, on
**2026-09-20**: *Digitales Oberflächenmodell 20cm (DOM20)*, CC BY 4.0, UTM32,
GeoTIFF, one-kilometre tiles, 30–50 MB each. Five times finer than any
coverage service in doc 80's registry, and five times finer than the DGM1 under
it.

The address was read out of the state's own index — the metalink lists every
tile with its hash — rather than guessed:

```
https://download1.bayernwolke.de/a/dom20/DOM/32690_5334_20_DOM.tif
```

Three computed names were checked against the server: 43.7, 48.4 and 51.1 MB,
all 200. The scheme writes the **zone onto the front of the easting**, which
`tile_of` now reads back — and which is only unambiguous because every German
easting is three digits of kilometres.

The same catalogue lists *Laserdaten* and an *Einzelbäume* dataset. Both have
since been asked. The laser is in the registry and is the better source for
trees than any raster (doc 102); *Einzelbäume* is not, because it carries a
position and two heights and no crown base at all.

## A window, not a mosaic

A twenty-centimetre tile is 5,000 × 5,000 pixels. Two things followed.

**The pixel guard had to grow again**, to thirty million: a square kilometre at
20 cm is 25 million, which is a hundred megabytes of float32 — a tile, not a
malformed header. Only the whole-product path passes that limit; every window
keeps the tight one (doc 104).

**And the mosaic had to stop being a mosaic.** Pasting four tiles and then
cutting a window out of them allocates four hundred megabytes for a
four-hundred-metre window. The window itself is five. So the tiles are pasted
straight into the window's own extent, each contributing the part of itself
that overlaps — which is the same arrangement, done once, at the size of the
answer rather than the size of the sources.

## Above the ground, not above the sea

A DOM is metres above sea level; what a garden needs is metres above its own
ground. The subtraction already existed inside `fetch_surface` as a private
helper and is now shared, so the tile path and the service path agree on what
"above the ground" means rather than each having a version.

That makes the ground a **requirement** rather than an option for this path: a
state's surface tiles without its terrain are no answer at all, and returning
None says so.

## Three more states, and a model that was already normalised

**2026-09-20, the second round.** Bremen's `DOM1` is lidar-derived and arrives
as XYZ text out of a whole-city archive; at one place its ground tops out at
4.8 m and its surface at 33.5, which is the houses. Saarland's and Hamburg's
surface models come
out of whole-region archives over ranges (doc 103), so two more cities' trees
are findable. Rheinland-Pfalz's `DOM1` came with its
ground, found through the same metalink (doc 103). Thüringen's `DOM1` and Sachsen's `DOM1` are
1 m surface models whose names are simply the grid — the index they were said
to need does not exist, and the zip around them was the whole obstacle
(doc 103). Both join by being entries.

**Baden-Württemberg is the interesting one.** This wave was planned around its
surface model being 5 m, which is too coarse to find a tree; that stopped being
true. It now publishes `DOM1` at 1 m and, better, **`nDOM1`** — a canopy height
model, already *above the ground* rather than above the sea.

That last word is the catch. Every other surface product here has the garden's
terrain subtracted from it, and doing that to a model that is already relative
would put every tree three hundred metres underground. So a source says whether
it is `normalised`, and the subtraction is skipped where it is. The rule of
this doc — *one rule for "above the ground", shared by both paths* — now has a
second half: **and it is applied once.**

## Business Rules

1. **A service where the state runs one**, its surface tiles where it does not,
   and nothing where it publishes neither.
2. **The window is pasted at the size of the window.**
3. **One rule for "above the ground"**, shared by both paths — and **applied
   once**: a product that is already normalised says so and keeps its heights.
4. **A tile's address is read from the state's own index**, not guessed, and
   the computed name is checked against the server before it is an entry.

## Dependencies

Doc 103 for the tile tier and the cache, doc 80 for the service tier this sits
under, doc 84 for what finds the trees once there is a surface to look at.

## Security

As doc 103: the address is a template and two integers, the cache key the same,
and the reader refuses an image by its header before allocating.

## Known Issues

- **Schleswig-Holstein** is the last state with no trees. Its bDOM is 20 cm,
  which is 100 MB of uncompressed float32 a square kilometre, and its download
  script **ignores a Range request** — so a 400 m window costs the whole tile.
  That is the only reason; the licence and the address are both fine.
- **Bayern's *Einzelbäume* was asked about and declined.** Its attributes are a
  position, the ground height and the tree's height — no species, no crown
  width and **no crown base**, which is the one thing a raster cannot give and
  the point cloud can (doc 107). Forty gigabytes in lots keyed by production
  run, for less than we already have.

## Bugs
