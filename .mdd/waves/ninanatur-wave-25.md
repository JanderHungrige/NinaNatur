---
id: ninanatur-wave-25
title: "Wave 25: Down to the square metre"
initiative: ninanatur
initiative_version: 23
status: planned
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
| 0 | which-tiles-and-whose | — | planned | — |
| 1 | a-tile-not-a-service | — | planned | 0 |
| 2 | a-horizon-for-everyone | — | planned | 0 |
| 3 | every-roof-in-the-country | — | planned | 1 |
| 4 | the-cloud-under-the-crown | — | planned | 1 |
| 5 | the-trees-in-the-other-states | — | planned | 1 |
| 6 | measure-my-own-garden | — | planned | 4 |
| 7 | which-source-said-so | — | planned | 1 |

Three stages:

- **Stage 1 — ground everywhere:** 0, 1, 2.
- **Stage 2 — what stands on it:** 3, 4, 7.
- **Stage 3 — the rest, and the gardener's own measurement:** 5, 6.

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
