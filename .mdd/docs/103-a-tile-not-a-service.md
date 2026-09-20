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
  - ninanatur/geo/tile_zip.py
  - ninanatur/geo/terrain.py
  - ninanatur/geo/tile_sources.py
  - ninanatur/geo/tile_grid.py
routes: []
models: []
test_files:
  - tests/test_tile_cache.py
  - tests/test_tiles.py
  - tests/test_tile_zip.py
data_flow: mixed
last_synced: 2026-09-20
status: complete
phase: all
mdd_version: 11
tags: [tiles, terrain, cache, volume, dgm1, mosaic, provenance, zip, thueringen, sachsen, baden-wuerttemberg]
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

## The wrapper is not a tier

Six states wrap each tile in a zip, and that — not any index — was what kept
them out. The grid is unchanged: the name the registry computes is the
*archive's* name, so `tile_zip.unpack` takes the wrapper off and everything
downstream is as it was.

What is inside was read rather than assumed, on **2026-09-20**:

| State | Beside the tile |
|---|---|
| Thüringen | the same heights again as a 29 MB `.xyz`, and a `.meta` |
| Sachsen | a world file, a GDAL sidecar, a currency CSV |
| Brandenburg | an HTML metadata page |
| Berlin | nothing — but CityGML is `.xml`, where everyone else writes `.gml` |
| Baden-Württemberg | the licence as a PDF, and **three more tiles** |

So members are chosen by extension, and a member's **declared** size is checked
before a byte of it is decompressed — the same order as the TIFF reader's
header check. Thüringen's 29 MB text copy of the heights is never allocated,
because it is never wanted.

**Baden-Württemberg is why members carry their names.** Its two-kilometre
archive holds four one-kilometre tiles, and pasted at the archive's corner all
four would land on top of each other. Each goes where its own name says, which
`corner_in` reads back with the same arithmetic `tile_of` uses.

**And its grid starts on an odd easting.** `513_5404` is a tile and
`514_5404` is a 404, so a scheme that floors to even numbers asks for a tile
that does not exist, every time. `corner_origin` is that parity, and it is the
only state that needs one.

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

**Thüringen and Sachsen are built**, and with them the tier stops being about
Bayern. Both were thought to need an index and neither does: their names are
the grid, exactly, and the zip was the whole obstacle. A garden in Erfurt or
Dresden now has ground, the surface model over it, and the roofs of the houses
next door.

Four more states joined by the same code, for the products their coverage
services never carried: **Brandenburg**, **Berlin** and **Mecklenburg-
Vorpommern** get surveyed roofs, and **Baden-Württemberg** gets both roofs and
`nDOM1` — a 1 m canopy height model, already normalised to the ground, which
closes the gap its 5 m surface service left for finding trees.

Their **point clouds** came with them: Thüringen, Sachsen and Brandenburg wrap
theirs too, so the member is streamed out of the archive to a file and read
from there, and the reader still never holds a tile.

What is left of this feature is two states and one technique:
**Rheinland-Pfalz** and **Schleswig-Holstein**, whose raster names carry a
per-tile flight year and which therefore really do need their index fetched,
cached and parsed; and the **range read into a remote archive** that Hamburg,
Bremen and Saarland would need, none of which publishes a tile at all.

## Known Issues

- **A zipped tile costs the volume twice** where the reader needs a file
  rather than bytes: the point cloud keeps the archive *and* the member
  streamed out of it until the cap drops the older one. The rasters and the
  buildings are unwrapped in memory and cost nothing extra.
- **Coverage is not known before it is asked for.** Every one of these states
  publishes a list of which tiles exist, and none of them is read: a tile that
  is not there answers 404, which the window already reads as ground nobody
  surveyed. That is right for a hole in a flight and wasteful for a garden
  outside the state entirely.

## Bugs
