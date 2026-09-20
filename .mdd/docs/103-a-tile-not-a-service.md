---
id: 103-a-tile-not-a-service
title: A Tile, Not a Service
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [102-which-tiles-and-whose, 68-terrain-sources]
relates: [17-terrain-window, 07-solar-geometry]
source_files:
  - ninanatur/geo/tile_cache.py
  - ninanatur/geo/tiles.py
  - ninanatur/geo/terrain.py
  - ninanatur/geo/tile_sources.py
routes: []
models: []
test_files:
  - tests/test_tile_cache.py
  - tests/test_tiles.py
data_flow: mixed
last_synced: 2026-09-20
status: draft
phase: all
mdd_version: 11
tags: [tiles, terrain, cache, volume, dgm1, mosaic, provenance]
path: Geo/Tile fetch
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 103 — A Tile, Not a Service

## Purpose

Doc 102 says which tiles exist and whose they are. This fetches one.

Wave 17 named three tiers — a coverage service where a state runs one, a tile
download where it does not, nothing where neither exists — and built the first
and the third. This is the second, and with it a garden in Bayern stops living
on a flat world.

## A window is not a tile

The difference that shapes everything here: a service is asked for *the window*
and returns exactly it. A tile is a fixed square of the country, and the garden
is wherever it happens to be inside one.

A window is 200 m across (`WINDOW_M` is its half) and a Bavarian tile is 1 km,
so the window lies inside one tile only when the garden is at least 100 m from
every edge — an 800 m square inside a 1,000 m one, **64 % of the time**. The
rest of the time the window crosses one line or two, and the fetch needs two
tiles or four. Anything else leaves the ground missing on one side of a garden
that happens to sit near a kilometre line, which is not a property of the
garden.

So: `tiles_across(east, north, source, reach_m)` gives every tile the window
touches, each is fetched, and they are pasted into one raster covering their
shared bounding box before a single resample puts it on the garden's axes.
`resample` already takes the raster's north-west corner in UTM; it took it
implicitly from the window's centre, and now takes it as a number, which is the
only change the service path sees.

## The cache is on the volume, and it is capped

A tile is 2.5 MB of GeoTIFF (Bayern) and up to 161 MB of CityGML. It must not
land in the container layer — a rolled image would lose it, and a full disk is
the whole deployment (plan 01, ST-07). It goes under the data volume, beside
the database.

- **Keyed by what it is**, not by who asked: `<product>/<state>/<tile>.<ext>`.
  Two gardens a street apart want the same tile and fetch it once.
- **Capped**, and the oldest file goes first when the cap is passed. Not the
  least recently *used* — that needs a read to write, and a cache that writes
  on every read is a cache that wears the volume. Oldest by modification time
  is enough for a store whose entries never change once written.
- **Written whole or not at all**: to `<name>.part`, then renamed. A half-tile
  that looks like a tile is the failure that costs a day to find.
- **A tile may be dropped the moment it has been read.** The window keeps the
  heights; the tile is just how they arrived. CityGML tiles are deleted after
  parsing rather than cached (doc 104 will say so), because 161 MB per square
  kilometre is not a cache, it is a disk.

## Politeness

These are state surveying offices publishing at their own cost, not an API with
a quota: one tile per place per product, `ingest/http.py`'s delay and its
user-agent, and the cache above so a second garden in the same kilometre asks
nobody anything. A garden near a tile corner costs four requests, once.

## What the page says

`TerrainWindow` already carries `source`, `licence`, `attribution` and
`vertical_step_m`, and the tile path fills them from the registry, so a Munich
garden's plan says *DGM1 Bayern (CC BY 4.0), Datenquelle: Bayerische
Vermessungsverwaltung*. Nothing downstream knows whether the heights came from
a service or a file, which is the point of putting the tier behind
`terrain_for`.

## Order of truth, unchanged

`terrain_for` asks the service registry first and the tile registry second. A
state with both keeps its service: it is one request for exactly the window,
against up to four for the same ground. A state with neither still gets None,
and None is still an answer.

## Business Rules

1. **Every tile the window touches**, or the window is wrong at the edges.
2. **The cache lives on the volume, under a cap, oldest out first**, and a tile
   is written whole or not at all.
3. **One tile per place per product**, through `ingest/http.py`.
4. **The window carries the registry's provenance**, and the page shows it.
5. **A service beats a tile**; neither is still None.

## Dependencies

Doc 102 for the registry, doc 68 for the service tier this sits under,
`geo/tiff.py` for reading a GeoTIFF, `ingest/http.py` for the fetch.

## Security

A tile's path is built from two integers and a template in the registry; the
cache key is built from the same, so nothing a garden carries can reach the
filesystem. The cache root comes from the deployment's data directory, never
from a request.

## What is built, and what is next

Bayern is built: `ground_tiles_for` finds its DGM1, `tiles_across` says which
tiles the window touches, `tile_cache` keeps them on the volume, and
`terrain_sync` reaches for them exactly where it used to log *no terrain
service*. A Munich garden now has ground, and its page says CC-BY-4.0 and the
Bayerische Vermessungsverwaltung.

The other seven DGM1 states hand their tiles out through an index or an Atom
feed rather than a computable URL (doc 102), so each needs its index fetched
and read before it can join the registry. Sachsen also arrives zipped. That is
the rest of this feature, state by state, and each one is a registry entry plus
an offline fixture in the tests.

## Known Issues

## Bugs
