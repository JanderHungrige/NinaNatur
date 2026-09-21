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
  - ninanatur/geo/tiles.py
  - ninanatur/geo/terrain.py
routes: []
models: []
test_files:
  - tests/test_tiles.py
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
sister_projects: [https://github.com/JanderHungrige/geokachel]
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

## A name the state gave us

Two states put the **flight year** into a raster's name —
`dgm1_32_419_5490_1_rp_2022.tif`, and the tile next door was flown in 2025 —
so no arithmetic reaches it. Both publish a list of everything they hold, and
Rheinland-Pfalz's is a metalink4: 12 MB, **21,160 tiles**, four flight years,
a sha-256 each. Read and parsed in 1.5 s, once for the whole deployment; the
file sits on the volume under the same cap as the tiles.

**An index is remote content, and it is read as data rather than as an
address.** What is taken from it is a *file name* — matched against a strict
character set, and kept only if it carries the grid it claims. The scheme, the
host and the folder stay the registry's own, so a state's list that began
answering with somebody else's URL would change nothing about where this
fetches from. The metalink's own `<url>` element is never read at all.

Doc 102's guarantee survives with one clause added: an address is a template
and two integers, **or a template and a name the state gave us**.

A square the state does not list is not asked for. Its own list saying it has
nothing there — a gap in a flight, a garden near the border — is an answer, and
guessing a name would be a 404 with extra steps.

## An archive that is never fetched

Three states publish no tile at all. Hamburg hands out the whole city as one
archive per product, 0.7–1.4 GB; Saarland hands out a Landkreis at a time,
559 MB for the ground and **12.5 GB** for the point cloud. Doc 102 recorded
that as a packaging decision no index would fix.

It is fixable, because of **where a zip keeps its index**. The central
directory is at the end of the file, so with range requests an archive can be
read as though it were local: the directory says where each member begins and
how long it is, and only those bytes are asked for. Measured against Saarland's
ground archive on **2026-09-20**:

| | |
|---|---|
| archive | 559,134,521 B |
| its directory — 311 members | **3 requests, 34,888 B** |
| one 4 MB tile out of it | 2 more requests |
| **total** | **5 requests, 2,132,040 B — 0.38 % of the archive — in 2.0 s** |

And end to end, a garden near Merzig: the six districts' directories give
**2,775 tiles** across the state in 11.8 s, the window follows in 3.2 s, and
what stays on the volume is one 4 MB tile. 200 × 200 m at one metre, every cell
known, 223.8–241.6 m.

**The parsing is the standard library's.** `zipfile` already knows Zip64 — which
a 12.5 GB archive needs — and data descriptors and every other corner of the
format. What it lacks is a file to read, so `remote_zip` supplies one: a
seekable file whose reads are range requests, buffered a megabyte at a time.
Writing a second zip parser to save an import would be the wrong kind of clever.

An archive's directory **is** the state's index, and its member names are read
the same way a metalink's are: matched against the grid and against a strict
character set, and never used to build a path.

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

**Saarland and Hamburg joined this way** — Saarland whole, with ground,
surface, roofs and a point cloud out of 124 GB of archives it never fetches.

**Rheinland-Pfalz joined too**, through its list rather than by arithmetic,
and it joined whole: ground, surface, roofs and a point cloud. It was the last
fully gapped state of any size.

**Schleswig-Holstein and Bremen closed it**, and with them every state that
publishes an addressable tile is in. Both publish their ground as **XYZ** — a
million lines of `easting northing height` to the square kilometre, twenty-eight
megabytes of ASCII for four of binary — which `geo/xyz.py` now reads into the
same north-up raster a GeoTIFF becomes.

Measured, and each one changed the code:

- **A tile is not always a million lines.** Schleswig-Holstein's border tiles
  carry 730,232, or 829,760, or 999,000, with holes *inside* a row, and there is
  **no NoData token anywhere** — 4.5 million points checked, not one sentinel.
  A cell nobody surveyed is simply an absent line. So values are placed by their
  own coordinates rather than by counting, and a gap stays a gap.
- **Bremen disagrees with itself four ways.** Its city writes bare integer
  eastings; Bremerhaven writes them with the zone glued on (`32466000.5`) and a
  **double underscore** in the terrain model's filename but not the surface
  model's; one of the four is north-first and another south-first; and the city
  puts an `x y z` header line above the grid.
- **Every Schleswig-Holstein download carries a 760-byte HTML footer**, and a
  stale row answers **200 with an HTML apology** rather than a 404.

Its terrain model needs the state's list because the name carries a per-tile
survey year — 2005 in one tile and 2025 in its neighbour. Its *building* model
carries no year and a fixed one in the query, so that one is arithmetic. The
list is GeoJSON rather than metalink, which is one more parser and no new idea:
a name comes out, the address is still built from the registry's own template.

Verified end to end on **2026-09-20**: Kiel, Rendsburg and Bremen all return a
200 x 200 m window at one metre with every cell known. Rendsburg reads 2.2 to
8.3 m against a town about five metres up, and Bremen's ground tops out at
4.8 m where its surface reaches 33.5 — the difference is the houses.
Cross-checked against Copernicus at the same points, which agrees.

## The decoder had never read a whole tile

Found by measuring Hamburg rather than by reading anything: its square
kilometre took **492.9 seconds**. The fetch was three of them.

**Every state in this registry ships LZW** — Bayern, Thüringen, Sachsen,
Rheinland-Pfalz, Hamburg, all of them, checked on 2026-09-20 — and the LZW
decoder was written in Wave 17 for what a *coverage service* answers: a 400 m
window, a quarter of a megabyte. It kept every byte the stream had ever held
in one Python integer, so each shift cost the whole of it and the loop was
**quadratic**. Nobody noticed, because at a quarter of a megabyte quadratic is
fast, and because every test of the tile tier builds its own *uncompressed*
TIFF.

One line — dropping the bits already consumed — and the same tile decodes in
**0.58 s**, an eight-hundred-fold difference. Sachsen's two-kilometre tile is
four times the pixels and would have taken half an hour.

| tile | before | after |
|---|---|---|
| Hamburg 1 km | 492.9 s | 0.58 s |
| Bayern 1 km | — | 0.90 s |
| Thüringen 1 km | — | 1.27 s |
| Sachsen 2 km | — | 0.69 s |
| Rheinland-Pfalz 1 km | — | 0.56 s |

And the heights are right, which is the other half of the check: Munich reads
510.5 to 522.7 m against the 523.8 m doc 104 got from Copernicus at the same
place, and Hamburg reads −0.5 to 8.1 m, which is Hamburg.

**The lesson is the one doc 95 is about.** "Bayern is built" was written on a
green suite whose every fixture was a TIFF this repository wrote to its own
expectations. A tile tier is not tested until a real tile has been through it.

## Known Issues

- **Schleswig-Holstein's surface model is not read.** Its bDOM is 20 cm, which
  is 100 MB of uncompressed float32 per square kilometre, and its download
  script **ignores a Range request** — so a 400 m window costs the whole tile.
  It also needs the list, because the name carries a flight year. No trees in
  Schleswig-Holstein until that trade looks better.
- **Bremen's roofs are not read.** Its LoD2 is a zip inside a zip. The inner one
  is **STORED**, so a doubly-nested range read reaches it for 781 kB of a 403 MB
  archive — measured — and it is not built. Its largest member is a 263 MB
  CityGML whose DOM peaks at 1.9 GB, so that path must use `iterparse`, which
  `lod2.py` already does.
- **Bremen's data is from 2015 and 2017**, and a March 2026 flight has not been
  published. When it is, the archive may be renamed rather than replaced — the
  rest of that download tree has already converted to year-less names — so the
  health check would stay green through a rename. Watch the names, not the bytes.

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

- **The LZW decoder was quadratic** (above), so every tile in the registry
  would have taken minutes. Fixed on 2026-09-20 before any of it reached a
  deployment; the regression test decodes a megabyte and fails if it goes
  slow again.
