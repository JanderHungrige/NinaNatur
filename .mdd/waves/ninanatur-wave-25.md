---
id: ninanatur-wave-25
title: "Wave 25: Down to the square metre"
initiative: ninanatur
initiative_version: 23
status: in_progress
depends_on: ninanatur-wave-21
demo_state: "Ein Garten in München, Dresden, Wiesbaden oder Kiel bekommt sein Relief, seinen Horizont und die Nachbarhäuser mit gemessener Höhe und Dachform — und in Nordrhein-Westfalen kennt jeder Baum in der Nachbarschaft seinen Kronenansatz, aus der Punktwolke. Wer mehr will, vermisst seinen eigenen Garten mit dem Telefon. Jede Zahl sagt, woher sie kommt und wie fein sie ist."
created: 2026-09-07
hash: 75f01f33
---

# Wave 25: Down to the square metre

## Demo-State

Ein Garten in München, Dresden, Wiesbaden oder Kiel bekommt sein Relief, seinen
Horizont und die Nachbarhäuser mit gemessener Höhe und Dachform — und in
Nordrhein-Westfalen kennt jeder Baum in der Nachbarschaft seinen Kronenansatz,
aus der Punktwolke. Wer mehr will, vermisst seinen eigenen Garten mit dem
Telefon. Jede Zahl sagt, woher sie kommt und wie fein sie ist.

*(This wave is not complete until this can be manually demonstrated.)*

Detailed plan, in German, with every verified URL and the compute budget:
`.mdd/plans/04-hoehendaten-fuer-die-luecken.md` (sections 2, 3 and 6).

## Why this is a wave

Eight Bundesländer have no entry in either registry — Bayern, Rheinland-Pfalz,
Sachsen, Thüringen, Schleswig-Holstein, Hamburg, Bremen, Saarland — about 36 %
of the population. A garden there gets the flat world of before Wave 17 and
houses at an assumed height. Baden-Württemberg has terrain but a 5 m surface
model, so no measured buildings and no found trees.

Two things changed, or were not found, since Wave 17 was planned, and both
were checked with real requests on 2026-09-07:

1. **Every one of the sixteen states now publishes its DGM1 as open data.**
   The eight missing ones lack a *bbox service*, not the data. Bayern's tile URL
   answers anonymously: `https://download1.bayernwolke.de/a/dgm/dgm1/{E}_{N}.tif`
   — 200, 2.5 MB per km², CC-BY-4.0, with a per-municipality Metalink index
   carrying SHA-256 sums. That is the "secondary tier" the Wave 17 plan named
   and never built.
2. **LoD2 building models are open in nearly every state** — measured height
   *and* roof shape, better than any surface raster for buildings. Bayern's LoD2
   tile answers anonymously: `…/a/lod2/citygml/{E}_{N}.gml`, 200, 161 MB per km².

And the owner's follow-up question — *we want about one square metre* — has
an answer that is not DGM1 at all. DGM1 **is** a 1 m grid (±15–30 cm in
height): for the *ground* the target is met wherever DGM1 exists. What DGM1
cannot hold by definition is what stands on the ground, and that is where a
garden's shade lives. The source for that at one square metre is the **airborne
laser point cloud**: nine states publish it openly, NRW verified (59 MB tile,
35 860 tiles indexed, dl-de/zero-2-0), and from it a 0.5–1 m surface can be
rastered with ground, building and vegetation *told apart* — and with the
**crown base height** per tree, which no raster product carries and which the
shading model needs (Wave 26).

## What the sources are, verified

| Need | Source | Status |
|---|---|---|
| Ground in the 8 states | DGM1 tiles: BY (URL verified), TH (Atom/DLA client), SN (2 km zips, DOM1 alongside), SH (1 km, `-9999` NoData), HH (Transparenzportal), HB (free since 2024-06-09), RP (Geoshop open data), SL (download licence to read — the WCS forbids embedding) | belegt |
| Horizon everywhere | Copernicus DEM GLO-30 — 30 m COG per 1°×1°, anonymous HTTPS, 32 MB per tile (verified 200) | geprüft |
| Horizon, coarser | BKG DGM200 INSPIRE WCS (capabilities verified) | geprüft |
| Buildings with roofs | LoD2: BY (verified), BW, RP, SN, TH, HE, NI, ST, BE, SH, HH, HB; MV, BB, SL and the federal **LoD2-DE** unverified | belegt / zu prüfen |
| Objects at ≤ 1 m | Point clouds: **NW** (verified), BY (CC-BY-4.0, 1–4 pts/m²), BE (10 /m²), BB, HH, HE (4–8 /m²), SN, ST, TH — all dl-de/zero or by; fee-based in BW, NI (opening announced), RP, MV, SL, HB; SH only DGM1 | belegt (gist 2026-06-02) |
| Own plot at ≤ 0.25 m | the gardener's phone: LiDAR scan or AR mesh upload, 5–20 MB | opt-in |

Fallbacks with a licence catch: EUBUCCO (heights for 73 % of EU buildings,
**ODbL**, share-alike — usable only as per-garden derived data on the volume,
with attribution, never in the shipped catalogue) and Overture (ODbL, heights
sparse in Germany). Both after the official sources, never instead.

## The shape of the fetch

Wave 17 set the rule: *primary a bbox service, secondary a tile download only
where no service exists, tertiary nothing*. The secondary tier is what this
wave builds, and it follows the LoD2 pattern of Wave 19 — **fetch something
large once, distil it, throw the source away**:

| | |
|---|---|
| Tile name | computable from UTM km, like `lod2.tile_name` — or resolved once from a portal index / Atom feed and cached |
| Fetch | `ingest/http.py::get_bytes`, generous delay, a User-Agent with a real contact (Wave 20) |
| Cache | on the **volume**, size-capped, LRU — never the container layer (Wave 20 finding ST-07) |
| Kept | the 200–300 m window: rasters as `int16` blobs (the `terrain_window` shape), a buildings table for LoD2, a few hundred bytes per building |
| Thrown away | the tile, after distilling |

Point clouds cost more and are budgeted explicitly:

| Step | Cost |
|---|---|
| download a tile | 60–450 MB (NRW mean 104 MB), 10–60 s, once per km² |
| decompress | `laspy` + `lazrs`, 2–5 M points/s → 2–10 s, chunked, < 300 MB RAM |
| clip to the window | ~9 % of a tile, ≤ 1 M points |
| raster | 600×600 cells at 0.5 m: DTM (class 2, min), DSM (max), **nDSM**, building mask (class 6), vegetation height (3–5), **crown base** (5th percentile of vegetation returns above 1 m) — under 2 s |
| store | 3–4 layers × 360 k cells × int16, deflated ≈ 0.5–1 MB per location |
| **per garden** | **1–2 minutes, once, in the background** — in the process pool Wave 20 introduces, never in the request thread |

Honest about resolution: at 4 points/m² a 0.5 m cell holds one point on
average — 1 m is the honest raster there; 0.5 m from about 8–10 points/m²
(Berlin, Hessen, newer NRW flights). Object heights ±0.3–0.5 m: a 1.8 m wall is
certain, a 30 cm raised bed is inside the noise. `vertical_step_m` and a
confidence travel with every window, as they do with every trait value.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | which-tiles-and-whose | 102 | built | — |
| 1 | a-tile-not-a-service | 103 | Bayern built | 0 |
| 2 | a-horizon-for-everyone | 104 | built | 0 |
| 3 | every-roof-in-the-country | 105 | BY, NW built | 1 |
| 4 | the-cloud-under-the-crown | 107 | NRW built | 1, 3 |
| 5 | the-trees-in-the-other-states | — | planned | 1 |
| 6 | measure-my-own-garden | — | planned | 4 |
| 7 | which-source-said-so | 106 | built | 1 |

Three stages:

- **Stage 1 — ground everywhere:** 0, 1, 2.
- **Stage 2 — what stands on it:** 3, 4, 7.
- **Stage 3 — the rest, and the gardener's own measurement:** 5, 6.

## Progress

- **2026-09-20 — feature 0, which tiles and whose** (doc 102). The fourth
  registry, `geo/tile_sources.py`, and the first one holding *files* rather than
  services. Probed with real requests that day: Bayern's DGM1 tile (200,
  2,558,672 B) and LoD2 tile (200, 161,627,079 B), NRW's LoD2 tile (200,
  20,684,673 B) and laser tile (200, 34,967,590 B) with its JSON index, and
  Copernicus GLO-30 (200, 31,889,167 B) for a horizon anywhere. The plan's
  index URL was on the wrong host — `download1.bayernwolke.de/odd/…` answers
  404, `geodaten.bayern.de/odd/…` serves the metalink with its SHA-256 sums —
  which is the whole argument for a registry of requests rather than citations.

  **Both questions this feature existed to answer are answered, and neither by
  a status code.** The federal **LoD2-DE** exists and its own product page says
  *"nur einem eingeschränkten Kreis Nutzungsberechtigter"*, listed as *"nur für
  Bundesbehörden"*: it does **not** replace the state adapters, so feature 3
  stays per-state. **Niedersachsen** lists LoD1, LoD2, bDOM20, DGM1, DOM1 and
  the maps in its OpenGeoData catalogue and **no laser data at all**, so it is a
  raster state for feature 5 — no crown base there. Both pages are JavaScript
  and had to be read rather than fetched, and the probe script carries the note
  so the next run re-checks them.

- **2026-09-20 — feature 1, a tile not a service** (doc 103), Bayern first. The
  middle tier Wave 17 named and never built: `geo/tiles.py` fetches every tile
  the window touches, `geo/tile_cache.py` keeps them on the volume under a cap
  — oldest out first, written whole or not at all — and `terrain_sync` reaches
  for them exactly where it used to log *no terrain service*. A garden in
  Munich has ground, and its page says CC-BY-4.0 and the Bayerische
  Vermessungsverwaltung.

  The thing a tile changes is where the garden sits in it: a 200 m window fits
  inside a 1 km tile only when the garden is 100 m from every edge, which is
  64 % of the time, so the window is pasted from up to four of them before one
  resample puts it on the garden's axes. `resample` learned to be told the
  raster's corner instead of deriving it from the window's centre; that is the
  only change the service path sees. A tile that does not arrive is NaN — ground
  nobody surveyed — and nothing arriving at all is still None.

  An old test said a Bavarian garden stays flat. It is now two tests: one for a
  state with neither a service nor tiles, and one for Bayern getting its ground
  from the tiles. The first version of that test reached for a real socket,
  which `pytest-socket` blocked and the sync swallowed — passing for the wrong
  reason, which is the failure mode doc 95 was written about.

- **2026-09-20 — feature 2, a horizon for everyone** (doc 104). Nine states had
  no ring at all: the sun set on the plot at the astronomical hour, whatever the
  hill to the south-west was doing. Copernicus GLO-30 gives them one, from a
  source that covers everywhere — and the check that matters was done end to
  end that day: the Munich cell, 41,906,386 B fetched in 4.4 s, decoded
  3,600 × 3,600 in 0.4 s, heights 325–726 m, and **523.8 m at Munich's own
  coordinates**, which is Munich's elevation. URL, licence, decoder and the
  degree-cell arithmetic agree.

  The reader learned two things to get there: **deflate**, which is what a
  cloud-optimised GeoTIFF is packed with and what every state service is not,
  and that **a whole product is not a window** — Wave 20's four-million-pixel
  guard is right for a 400 m window and wrong for a degree of the earth, so
  `read_raster` takes its limit per call and only this path raises it.

  The ring itself is unchanged: the cell's heights are read onto a 20 m UTM grid
  around the garden and `ring_from` walks the same rays, because a ring built on
  grid north rather than true north is rotated by two of its own bins. Cells the
  ring crosses into are fetched too; one that does not arrive is unknown rather
  than flat. **Stage 1 is complete.**

- **2026-09-20 — feature 3, every roof in the country** (doc 105), and it was
  smaller than planned. The wave assumed a dozen adapters — CityGML 2.0
  namespaces, other roof codings, parts. Bayern's tile says otherwise: the same
  CityGML 1.0, the same `bldg:` namespace, `measuredHeight` in metres and AdV's
  Dachform keys, which `ADV_ROOFS` already maps. **The reader built for NRW
  reads a Bavarian building unchanged**, and one real building out of that tile
  is now `tests/fixtures/lod2_bayern_building.gml`, so the claim is checked
  against the state's own file.

  What had to change was plumbing and one guard. `_surveyed` no longer begins
  `if state != "Nordrhein-Westfalen"`; it asks the registry, so a state joins by
  being probed and nothing else. And `MAX_TILE_BYTES` was 150 MB, set when
  Cologne's 38 MB was the largest tile anybody had seen — a square kilometre of
  Munich is 161,627,079 B, so the guard was refusing the data it was meant to
  bound.

- **2026-09-20 — feature 7, which source said so** (doc 106), the API half.
  Feature 2 had created a licence gap the moment it shipped: a Bavarian garden
  got a Copernicus horizon and nobody was named, while the terms ask for DLR,
  Airbus and ESA. `GET /gardens/{token}/sources` is the list a page owes —
  ground, horizon, buildings — built from what a garden *used* and costing no
  request: naming the building model needs a state, and the stored ground
  window already says which one measured it.

  That rests on an invariant — every state publishing LoD2 also publishes its
  ground — and the test written for it **failed on its first run**, in NRW:
  the terrain services are registered under *Nordrhein-Westfalen* and the tiles
  under *NW*, so each registry answered to one spelling and returned None for
  the other. `STATES`, `key_of` and `name_of` are now the one table both go
  through.

  And `signature_of` learned about the ground. Bayern is why: yesterday a
  Bavarian garden had no terrain and its light map was computed flat; today its
  tiles are read, and without the ground in the signature that map would have
  stayed flat for ever, quietly — the exact failure the signature exists to
  prevent.

  The page half followed: `SourceCredits` prints the list last in the garden's
  details, under the numbers it is about — what each survey decided in the
  gardener's words, how fine it is, and the credit word for word. Fetched with
  everything else the server derives, because a garden that shows numbers must
  show their credits at the same time and not a moment later. **Stage 2 is
  complete but for feature 4**, the point cloud.

- **2026-09-20 — feature 4, the cloud under the crown** (doc 107), NRW. The
  plan's recipe was buildings from class 6, vegetation from 3–5, crown base
  from the vegetation points. **NRW's tile has none of those classes**: 8.3
  points/m², 76 % ground, and everything standing is unclassified. So the
  separation comes from the building model instead — a return inside a surveyed
  LoD2 footprint is a roof, everything else that stands is a crown — which is
  only possible because feature 3 landed two features earlier.

  Three layers on the garden's own axes: ground, surface, and the crown base
  nothing else in this project knows. A laser sees no ground under a roof, so
  those cells are empty by construction (4 % of the window) and are filled from
  the rim of each hole inwards; without that a house has no height at all.

  Measured rather than budgeted: tile 35 MB in 4.0 s, window in 0.8 s, **186 MB
  peak**, ground 100 % after filling, crown base in 2.7 % of cells (median
  2.9 m), stored window **66 kB**. Two things brought the memory in: the tile is
  streamed from the volume rather than held — the largest is 445 MB — and the
  reader takes a quarter of a million points at a time, where a million cost
  226 MB and was no faster.

  `laspy` and `lazrs` are the first new dependencies since Wave 20. The
  supply-chain test earned its keep immediately: the image would have shipped a
  library CI never installed. **Stage 2 is complete.**

## What each one is

### 0. which-tiles-and-whose

The fourth registry, after orthophotos, terrain and surface models, and the same
rule: read from the source, confirm with a real request, a state with nothing
gets no entry, a licence that forbids this use is a state without an entry.

`geo/tile_sources.py`: per state and product (`dgm1`, `dom1`, `lod2`, `laz`) —
`url_for(east_km, north_km)` or an index resolver, tile size (1 or 2 km),
format (GeoTIFF / zip / GML / LAZ), licence, attribution, `vertical_step_m`,
point density. A **dated probe script** (not the test suite) confirms every
entry against the network and writes the date into the doc, as doc 68 did.

Two questions decide the shape of feature 3 and are answered here first:
**does the federal LoD2-DE exist as an open, tileable product** (its BKG
documentation returned 404 on 2026-09-07) — if so it replaces a dozen adapters;
and **are Niedersachsen's point clouds open now** (the availability list says
"planned 2024").

Tests: no entry may be chargeable; every entry carries an attribution; the
tile-name function round-trips for every state's scheme.

### 1. a-tile-not-a-service

The tier itself, and Bayern first (URL verified, largest state, 13 million
people): fetch, cache on the volume with a cap, clip the 1 km tile to the
window with the existing `read_raster`/`resample`, store as `terrain_window`.
Then the other seven DGM1 states — zips (SN) unpacked in memory, Atom feeds and
download clients (TH, SH, HH, HB, RP) resolved once from their index, Saarland
only after its download licence text is read.

Tests: an offline fixture tile per state format; the cache cap evicts oldest
first; a garden in Munich gets a window whose provenance names Bayern and
CC-BY-4.0.

### 2. a-horizon-for-everyone

Copernicus GLO-30 as the horizon ring wherever no state DGM exists — nine states
get a horizon for the first time. Either HTTP range reads on the COG (the
project's TIFF reader has handled tiled TIFFs since Sachsen-Anhalt; `http.py`
gains a `get_range`) or one 32 MB tile per degree cell on the volume, fetched on
demand — Germany is at most about eighty of them. 30 m is enough for a 5 km ring
sampled at 20 m: it places hills, not hedges. Attribution text taken from the
Copernicus DEM terms at feature 0.

### 3. every-roof-in-the-country

LoD2 adapters: BY (verified), then BW (which closes the 5 m gap for buildings),
RP, SN, TH, SH, HH, HB, then NI, HE, BB, BE, ST, MV — or LoD2-DE for all of
them if feature 0 finds it. `buildings_from` reads NRW's CityGML 1.0 with
`measuredHeight`, `roofType` as AdV keys and `BuildingPart`s; other states differ
(CityGML 2.0 namespaces, roof-shape coding, parts). One small fixture fragment
per state in the tests, never a tile. A 161 MB tile is streamed with the
existing `iterparse` and only the buildings table is kept.

This is also the rest of Wave 21: eaves and ridge direction from the roof
surfaces, for every state that has them.

### 4. the-cloud-under-the-crown

Point clouds, NRW first: tile → clip → rasters at 0.5 m or 1 m by density →
nDSM, building mask, vegetation height, **crown base** → stored as new layers of
the surface window. Then BY, HE, SN, ST, TH, BB, BE, HH, one portal adapter
each, one shared rasteriser. Runs in the background with a visible state
(*wird vermessen*) and the budgets above as tests: RAM under 300 MB, window
under 1 MB, and a hard cap on cached tiles.

What it gives the model beyond height: buildings and vegetation **told apart**
(doc 84's "a marquee and a tree read the same" ends here), hedges as bodies, and
the crown base Wave 26 needs for crowns that are not cylinders.

### 5. the-trees-in-the-other-states

DOM tiles for RP, SN (DOM1 ships beside the DGM1), TH, SH, HH, HB, SL — the
same tile tier pointed at a surface product — so `canopies_in` finds trees in
states with no coverage service. Bayern's image-based bDOM is the same shape
and a candidate for the same adapter.

### 6. measure-my-own-garden

Inside the fence there is no official source at one square metre. The gardener's
phone is: an ARKit/ARCore scan or LiDAR mesh (1–5 cm at close range, drifting
across a garden), uploaded (≤ 20 MB), rastered to 0.25 m on the server in
seconds, georeferenced by two or three control points the user clicks on the
plan (house corners). One window per garden, about 1 MB, on the volume like the
garden itself, opt-in. **Not** server-side photogrammetry from photos —
10–30 minutes of GPU per garden is not a plan.

### 7. which-source-said-so

Provenance on the page: which state's DGM1, which LoD2, which point cloud, at
what resolution and with which attribution — a garden may carry three credits.
`signature_of` reacts to a newly available source so the map goes `stale` rather
than quietly staying on the old one; `vertical_step_m` and the confidence are
shown beside the numbers, as `height_source` already is.

## What the model will not know

- **Under a closed canopy.** A laser does not see the ground or the shed
  beneath a dense crown; the window says NaN there, never a guess.
- **Small things.** Below ~0.5 m and below ~4 m across, objects are noise at
  4 points/m². The raised bed is the gardener's to type or to scan.
- **Age.** Point clouds are flown every 5–6 years; trees grow. The acquisition
  year is stored and shown.
- **Saarland's terms.** The WCS forbids embedding; the download has its own
  licence, and only that one is used, only once read.

## Open Research

- LoD2-DE: one federal product or fifteen portals.
- Niedersachsen and Baden-Württemberg point clouds: open by the time this wave
  runs?
- The right density threshold for 0.5 m versus 1 m rasters, measured on NRW and
  Berlin tiles.
- Volume growth: cap per product and a global cap, with eviction that never
  touches a garden's own scan.

## Deliberately not in this wave

- Using the new heights in the shading model beyond what it already consumes —
  crown base, roof planes and the rest are Wave 26.
- Any fee-based source, and any ODbL source in the shipped catalogue.
- Server-side photogrammetry.
