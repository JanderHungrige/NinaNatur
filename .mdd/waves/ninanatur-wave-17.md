---
id: ninanatur-wave-17
title: "Wave 17: The ground is not flat"
initiative: ninanatur
initiative_version: 20
status: complete
depends_on: ninanatur-wave-16
demo_state: "Ein Garten am Hang bekommt ein Höhenprofil aus öffentlichen Daten, und die Schattenkarte rechnet damit: ein Nachbarhaus bergauf verschattet mehr als eines auf gleicher Höhe, eines bergab weniger. Ein Hügel im Süden frisst die Wintersonne, bevor sie im Garten ankommt. Woher die Höhen stammen, wie alt sie sind und wie genau, steht neben dem Ergebnis — und wo es keine gibt, steht das auch."
created: 2026-09-04
hash: 65ea97d2
---

# Wave 17: The ground is not flat

## Demo-State

Ein Garten am Hang bekommt ein Höhenprofil aus öffentlichen Daten, und die
Schattenkarte rechnet damit: ein Nachbarhaus bergauf verschattet mehr als eines
auf gleicher Höhe, eines bergab weniger. Ein Hügel im Süden frisst die
Wintersonne, bevor sie im Garten ankommt. Woher die Höhen stammen, wie alt sie
sind und wie genau, steht neben dem Ergebnis — und wo es keine gibt, steht das
auch.

*(This wave is not complete until this can be manually demonstrated.)*

## Why this is a wave and not a detail

Every shadow in this project is computed on a plane at z = 0. The word *terrain*
does not appear in the code. A garden below a slope gets an answer that is
confidently wrong, and nothing on the page says so.

Wave 16 is what makes that urgent. A shade map invites somebody to trust it cell
by cell, which a single number per bed never did. The moment the map is
believable, being silently flat becomes the largest error in it.

## The data question, settled before planning

The obvious plan — compute a height model for Germany and serve from it — does
not survive its own arithmetic, and the arithmetic is worth writing down because
it decides the whole architecture.

**What Germany costs.** The BKG's own DGM1 documentation (Stand 28.04.2026)
states the national volume: **1 TB**, as LZW-compressed GeoTIFF, 1 m grid,
1 × 1 km tiles. At 20 cm that is twenty-five times as much — about 25 TB. There
is no version of this that ships in a container image, and no version that is
worth holding for a few thousand gardens in the Rhineland.

**What a garden actually needs.** Two things, and neither of them is a national
raster:

| | window | native | stored |
|---|---|---|---|
| The ground the garden stands on | 200 × 200 m at 1 m | 160 KB GeoTIFF | **24–31 KB** int16 cm, deflated |
| The horizon around it | 10 × 10 km at 20 m | 1 MB GeoTIFF | **1.4 KB** — 360 angles |

Both figures are measured, not estimated. Brandenburg's WCS was asked for a
200 m window on 2026-09-05 and answered with a 200 × 200 float32 GeoTIFF of
160,432 bytes in one request; the same service answered a 10 km window scaled
server-side to 500 × 500 in 8.2 s and 1,001,062 bytes. Stored as centimetres
above the window's own minimum, row-differenced and deflated, the garden window
is 24 KB. Ten thousand gardens are then a quarter of a gigabyte — and most of
that dedupes, because two gardens in the same street share the same ground.

**So: nothing is precomputed, and nothing national is stored.** The height data
is fetched per location, on demand, once, and only the derived window and the
horizon ring are kept. This is the same shape as the light grid from Wave 16 —
expensive to compute, small to keep, stored next to the garden on the volume and
never in the image.

### The three requests

1. **The garden window.** A bbox request to the state's WCS, 200 m around the
   anchor, native 1 m. One HTTP call, ~160 KB.
2. **The horizon.** The same service, a 10 km box, downscaled *server-side* to
   20 m via `SCALESIZE`. Without that parameter the same box would be 400 MB;
   with it, 1 MB. The raster is then reduced to 360 horizon angles and thrown
   away.
3. **Nothing else.** Terrain does not change. A fetched window is valid until
   somebody moves the garden, and is shared with every garden within 100 m.

### Why a registry, and why the primary must be a bbox service

The per-region registry the question proposes is right, and it already exists in
this codebase for imagery: `geo/orthophotos.py`, one entry per Bundesland, each
read from that service's own GetCapabilities rather than from a summary of it.
Wave 17 builds the same thing for elevation.

But the important part is *what kind* of source is primary. A tile download and
a bbox service are not two routes to the same place:

| Route | Per garden | Notes |
|---|---|---|
| **WCS bbox subset** | ~160 KB, 1 request | the 1 TB never leaves the server |
| 1 km² tile download | 4–20 MB, then clip and discard 99 % | politeness problem, cache problem |
| National precompute | 1 TB | not a plan |

So: **primary = a service that subsets by bbox** (WCS, or an equivalent HTTP
API). Secondary = tile download, only for states with no such service, and only
with the tile cached on disk through `ingest/http.py` like every other fetch in
this project. Tertiary = none; *"für diese Adresse gibt es keine Höhendaten"* has
to stay a permitted answer, exactly as it is for orthophotos.

### Two states are already proven

Probed on 2026-09-05, capabilities read directly:

| State | Endpoint | Coverage | Licence | Attribution |
|---|---|---|---|---|
| Brandenburg (+ Berlin) | `https://isk.geobasis-bb.de/ows/dgm_wcs` | `bb_dgm` | dl-de/by-2-0 | © GeoBasis-DE/LGB — plus © Geoportal Berlin for Berlin data |
| Nordrhein-Westfalen | `https://www.wcs.nrw.de/geobasis/wcs_nw_dgm` | `nw_dgm` | dl-de/zero-2-0 | none required; given anyway |

Both answer anonymous WCS 2.0.1, both return `image/tiff`, neither host serves a
`robots.txt`. NRW caps a request at 2000 × 2000 px, which is above everything
this wave asks for. The federal service `sgx.geodatenzentrum.de/wcs_dgm1`
answers **403** to anonymous requests — the same wall the BKG orthophoto
endpoint put up in Wave 8, and the same conclusion: there is no federal shortcut,
the states are the source.

`hoehendaten.de` lists all sixteen states as open — dl-de/by-2-0 or CC-BY-4.0
throughout — and is a good map of the territory. It is a **discovery aid, not a
dependency**: a third-party aggregator is one person's server between this app
and public infrastructure, and the licences it reports still have to be read at
the source.

### Why not 20 cm

The wish is reasonable and the answer is no — not because of size, but because
the data does not contain it.

- **Grid.** The national product is DGM1: point spacing **1 m**. No Bundesland
  publishes a finer statewide terrain model as open data.
- **Vertical accuracy.** The BKG documentation states **< ± 0,3 m**,
  terrain-dependent. Across 20 cm of ground, even a 30 % slope rises 6 cm — a
  fifth of the model's own noise. A 20 cm grid would be interpolation presented
  as measurement.
- **The point cloud underneath.** Airborne laser scanning delivers ≥ 4 points/m²
  since 2012 and 1 point/m² before that. Four points per square metre is a mean
  spacing of 50 cm — and that is *all* returns; ground points after filtering
  vegetation and roofs are fewer. There is nothing at 20 cm to resample from.

**So 1 m is the honest floor, and it is stated as such next to the result.** The
sub-metre relief of a garden — the raised bed, the retaining wall, the terrace,
the step down to the lawn — is not in any public dataset and never will be. It
is in the objects the user draws, which this app already models with heights.
That is the right division: surveyed data for the shape of the land, the user's
own drawing for the shape of the garden.

A "Feinmodus" from LAZ point clouds stays in the backlog: 100–500 MB per km²,
`laspy` or PDAL as a dependency, per-state classification schemes that are
explicitly not standardised — a wave of its own, if ever, and not the one that
makes gardens on slopes work.

### Terrain or surface — and why nothing is counted twice

The question that has to be settled before any of this is built: does the height
data already contain the buildings? If it did, every house would be counted
twice — once as the ground, once as the obstacle the user drew.

**It does not, and this is the evidence rather than the assurance.** Geobasis
NRW's user information for the 3D-Messdaten (Stand 02/2020) sorts the laser
returns into nine classes and marks each one DGM-relevant or DOM-relevant:

| Class | What it is | Counts as |
|---|---|---|
| 2 | Geländepunkte / Bodenpunkte — the natural relief, with building, vegetation and other points excluded | **DGM** |
| 26 | aufgefüllte Bodenpunkte (synthetisch) — interpolated ground under bridges and in dense forest | **DGM** |
| 20 | Last Return nicht Boden — points on buildings, cars and the like | DOM |
| 21 | aufgefüllte Gebäudepunkte (synthetisch), kept until 2019 — interpolated under large buildings | DOM |
| 17 | Brückenpunkte | DOM |
| 9 | aufgefüllte Gewässerpunkte (synthetisch) | DOM |
| 1 | unklassifiziert, e.g. medium returns inside vegetation | DOM |
| 24 | Kellerpunkte — below the natural ground, in a Kellerabgang or Lichtschacht | neither |
| 18 | Hochpunkte — birds, fog, cloud, steam | noise |

The DGM is computed from the DGM-relevant classes only. A DGM1 request therefore
returns bare earth, and a building's base is the ground it stands on. Nothing is
counted twice — **provided the registry only ever holds terrain products**, which
is why feature 0 records the product type per entry and why a DOM endpoint in the
terrain registry is a bug rather than a fallback.

**Two consequences, and both belong in the model:**

1. **The point cloud is not filtered — it is labelled.** The 3D-Messdaten
   "enthalten sämtliche Reflexionen des ALS in einer klassifizierten Punktwolke".
   Anyone reading LAZ directly gets roofs and treetops alongside the ground and
   has to select class 2 themselves. One more reason the Feinmodus is not the
   cheap upgrade it looks like.

2. **Under a building the ground is interpolated, not measured.** A laser does
   not see through a roof; class 26 exists for exactly that gap. A house's base
   height is therefore a smoothed guess from the ground around it — which is the
   right thing to stand it on, but it means a house on a steep slope gets one
   averaged base rather than an uphill and a downhill corner. Said out loud, not
   hidden.

**And one defensive check.** Ground filtering is not perfect: a large flat-roofed
hall can survive into the terrain, and then the model really would put a building
on a building. Feature 1 compares the terrain under each footprint against the
ring of ground around it, and where it stands proud by more than roughly a
storey, marks the window suspect instead of quietly building on a roof.

### Radar is a different animal

The global fallbacks are radar, and radar is where *Gebäude auf Gebäude* would
genuinely happen. The Copernicus DEM (GLO-30, TanDEM-X, flown 2011–2015) is
explicitly a **surface** model — buildings, infrastructure and vegetation are in
the numbers. It is not a terrain model and must never be used as one here, least
of all as a base height for an obstacle.

FABDEM removes forests and buildings from that very dataset by machine learning,
which would solve it, and is licensed **CC BY-NC-SA 4.0** — non-commercial. That
is outside this project's licence rule, in the same way and for the same reason
NaturaDB is.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | which-ground-and-whose | docs/68-which-ground-and-whose.md | complete | — |
| 1 | a-window-of-ground | docs/69-a-window-of-ground.md | complete | 0 |
| 2 | the-horizon-ring | docs/70-the-horizon-ring.md | complete | 0 |
| 3 | buildings-stand-on-the-ground | docs/71-buildings-stand-on-the-ground.md | complete | 1 |
| 4 | the-hill-that-eats-the-morning | docs/72-the-hill-that-eats-the-morning.md | complete | 2, 3 |
| 5 | which-way-does-it-fall | docs/73-which-way-does-it-fall.md | complete | 1 |
| 6 | say-how-good-it-is | docs/74-say-how-good-it-is.md | complete | 1 |

Delivered in three stages, each merged and deployed on its own:

- **Stage 1 — where the numbers come from:** 0, 1, 2. Nothing visible yet.
- **Stage 2 — the model uses them:** 3, 4. The shade map changes on a slope.
- **Stage 3 — the user sees them:** 5, 6.

## What each one is

### 0. which-ground-and-whose

Sixteen states, probed one at a time, each entry read from that service's own
GetCapabilities. `geo/terrain_sources.py`, shaped like `geo/orthophotos.py`:
state, endpoint, coverage id, CRS, licence, attribution, native resolution, and
the acquisition period where the service states one.

**This comes first and nothing is built on top of it until it is done.** It is
the same rule that kept this project off NaturaDB and off unlicensed imagery:
the licence question is answered before the pipeline exists, not after somebody
notices.

Two entries are already written (Brandenburg, NRW). Fourteen to go. Each is a
`GetCapabilities` call, a read of `ows:Fees` and `ows:AccessConstraints`, and one
real `GetCoverage` for a 200 m box to confirm the service actually subsets.

A state that has no such service gets **no entry**. Not a neighbour's data, not
a coarser federal substitute quietly swapped in.

### 1. a-window-of-ground

`geo/terrain.py`: given a location, return a height window.

- 200 m box around the anchor. The obstacle model reaches 50 m beyond the plot
  boundary (`surroundings.MARGIN_M`), so 200 m covers every building the shading
  already knows about, with enough ground around it to measure a slope against.
- Fetched through `ingest/http.py`, so a rerun costs zero requests.
- Stored on the volume in a `terrain_window` table: cell size, origin in the
  garden's local metres, cols, rows, heights as **int16 centimetres above the
  window's own minimum**, deflated — plus source, licence, acquired, native
  resolution, fetched_at. Provenance for terrain, on the same principle as
  provenance for traits.
- **Keyed by location rounded to 100 m, not by garden.** Two gardens in the same
  street share one window: less storage, and far fewer requests against public
  infrastructure that nobody is paying us to use.
- `-9999` is NoData and must be carried as such. Border tiles and water are
  genuinely empty, and a NoData averaged into a slope is a cliff that isn't
  there.

The reprojection is the one piece of real work: the services speak
ETRS89/UTM (EPSG:25832 or 25833), the app speaks metres from an anchor.
**Settled while planning: fifty lines, no dependency.** A Krüger-series forward
transform on GRS80 was written and checked against control points — longitude 9°
(zone 32's central meridian) returns easting 500000.000 exactly, and Köln Dom
lands on 356560 / 5645282, which is where it is. `pyproj` is a wheel per platform
for the same formulas. The control-point test ships with the code either way:
this is exactly the kind of thing that is quietly wrong by 30 m and shows up only
as a garden whose hill is in the wrong direction.

**The format is not uniform, and that was measured, not assumed.** Brandenburg
returns an uncompressed float32 GeoTIFF, which `struct` plus numpy reads in about
forty lines. NRW returns the same coverage **LZW-compressed** (`Compression = 5`)
for the DGM while its nDOM comes back uncompressed. So feature 1 needs a TIFF
LZW decoder — another forty lines, and a well-specified one — or it has to
negotiate the format per service. The registry records which, because finding out
at request time means finding out in production.

### 2. the-horizon-ring

One coarse request per location, reduced to **360 angles** — for each degree of
azimuth, the highest terrain angle above the horizontal within 5 km. 1,440 bytes,
stored beside the window, computed once.

This is what turns "a hill in the south" from a data problem into a lookup: the
sun is below the horizon in its own azimuth, or it is not.

**It will do nothing in flat country, and that is the correct outcome.**
Measured while planning, at Potsdam: the horizon ring maxes at 2.42°, mean 0.89°
— and the light model already discards the sun below `MIN_ALTITUDE = 5°`. In the
North German Plain this feature changes no number at all. In the Sauerland, the
Schwarzwald or the Alpenvorland it decides whether a garden sees the sun in
December. A test asserts the flat case explicitly, because a feature that
appears to do nothing is otherwise indistinguishable from a broken one.

### 3. buildings-stand-on-the-ground

The shading model gains one number per point and one per obstacle.

- An obstacle's top is `terrain under its footprint + height_above_ground +
  shading_height(...)`. `height_above_ground` keeps its current meaning — height
  above the ground *under the object* — so it composes with terrain instead of
  fighting it, and **no existing garden needs migrating**.
- A receiving point sits at its own cell's height, so the obstacle that matters
  is the one whose top clears the ray, not the one that is tallest.

**Keeping Wave 16's speed is the engineering.** That speed came from computing
each moment's shadow polygons once for all points, which was valid only because
every point was at z = 0. With terrain each point has its own height, so a single
swept polygon no longer serves.

The plan: keep the per-moment polygon, but sweep it for the **lowest** point in
the window — a conservative superset of every real shadow. A point outside it is
rejected as cheaply as today. A point inside it gets one exact check: is its
along-sun distance from the footprint within `(top − z_point) / tan(altitude)`?
That is a subtraction, a divide and a compare, run only on the few points the
bounding box already admitted. The budget stays where Wave 16 left it — under a
second for a 600-cell grid — and the plan must be measured against that budget
before feature 4 is started, not after.

### 4. the-hill-that-eats-the-morning

The ring from feature 2 enters the light field: at each moment, if the sun's
altitude is below the ring's angle at the sun's azimuth, the whole garden is
unlit — no polygon test needed, which makes this the *cheapest* feature in the
wave as well as the one with the largest effect in hill country.

Within the garden window, terrain shades itself over short distances too. That
is handled by each cell's own slope and aspect rather than by a per-cell horizon:
600 cells × 360 azimuths × 1,200 moments is not a computation this app is going
to do. The near field is the slope; the far field is the ring; the answer is
whichever blocks the sun first.

### 5. which-way-does-it-fall

Slope and aspect per bed, from the window: *"Südhang, 8 %"*, next to the light
figure it explains.

**Named, not scored.** A south-facing bank is warmer and drier than flat ground
and behaves like a site a few hundred kilometres further south — but folding
that into the Ellenberg fit is a change to how every suggestion is ranked, and
it belongs to the site model rather than to this wave. Wave 17 delivers the
words; a later wave may deliver the score.

### 6. say-how-good-it-is

A hillshade of the window under the plan, at low contrast, in both themes — and
next to it the four things somebody needs in order to decide whether to believe
it: **source and attribution, acquisition year, grid width, stated accuracy
(± 0,3 m)**.

And where there is no data: *"Für diese Adresse liegen keine Höhendaten vor —
der Plan rechnet mit ebenem Gelände."* The flat assumption is fine. The silent
flat assumption is what this wave exists to end.

## Where it is stored

| | Where | Why |
|---|---|---|
| `terrain_window` | volume, keyed by 100 m location | derived from public data, but per-location and unbounded — never in the image |
| `terrain_horizon` | volume, same key | 1.4 KB, computed once |
| The DGM tile or coverage response | `data/cache/`, gitignored | an HTTP cache, like every other fetch here |

Nothing terrain-shaped goes into the catalogue. The catalogue is species, it
ships in the image, and it is 10 MB because somebody keeps it that way.

## What the model will not know

Written down before it is built, in the same spirit as Wave 16's list:

- **The ground under a building is interpolated**, because a laser does not see
  through a roof. Correct as a base to stand the house on, smoothed on a slope.
  See *Terrain or surface* above for why nothing is counted twice, and for the
  check that catches it when the filtering fails.
- **Bridges are not in the DGM** (the BKG documentation says so outright), and
  water surfaces can have height jumps between acquisition flights.
- **The data is 2000–2022.** A garden on a plot that was levelled in 2024 has
  terrain from before the earthworks. The acquisition year is shown for exactly
  this reason.
- **Height systems differ**: DHHN2016 everywhere except Schleswig-Holstein
  (DHHN92). Irrelevant within one garden — every height here is relative — and a
  trap the moment somebody compares absolute heights across that border.
- **The horizon comes from bare earth**, so a forest edge 200 m to the south is
  invisible to it although it genuinely blocks the winter sun. See Open Research.
- **± 0,3 m.** A 1° slope across a 20 m garden is 35 cm — the same size as the
  error. Slope statements below roughly 2 % are noise and should not be made.

## Open Research

- **Does the ring want the surface model instead?** A DOM/bDOM would include the
  forest that genuinely cuts the low sun, at the cost of a second product with
  patchier coverage — and of the double-counting trap, because a DOM contains
  buildings too. If it is ever done, the rule has to be written first and it can
  only be one rule: **the ring starts beyond the obstacle model's reach.** The
  obstacle model knows buildings out to 50 m from the plot boundary; a ring built
  from a surface model must ignore everything inside that radius, or the
  neighbour's house is a shadow twice over.
- **Which states subset by bbox at all.** Fourteen unprobed. The registry may
  come back thinner than `hoehendaten.de` suggests, because "open data" and "has
  a WCS" are different claims.
- **What a fetch costs the state.** One request per location per garden, cached
  forever, is polite. It should still be measured and stated, and the delay in
  `ingest/http.py` should be set generously for these hosts.

## Deliberately not in this wave

- Slope and aspect as **growing conditions** — the score, not the words.
- Cold-air pooling and frost pockets. Terrain makes them computable and they are
  a real gardening answer; they are also a model of their own.
- Water: where the rain runs and where it stands. Same reasoning.
- Sub-metre relief from LAZ point clouds. See *Why not 20 cm*.
- **Measuring the buildings and trees themselves.** Explored while planning this
  wave and deliberately left out of it, because it is a second source doing a
  second job and would double the wave.

  The surface models are on the same hosts, under the same licences, with the
  same bbox subsetting: NRW serves `nw_dom` and — already differenced against
  the terrain — `nw_ndom`, object heights above ground, at **0.5 m**. A 200 m
  window is 640 KB and one request. Over a Cologne suburb it reads exactly as it
  should: a third of the window at ground level, then hedges, then garages, then
  roofs and crowns.

  Crossed with the OSM footprints this app already fetches, it measures what is
  currently assumed. A university building tagged `building:levels=5` — 15 m
  under the storey assumption — measures 20.0 m with a tight spread. That is the
  case for doing it.

  It also measures the failure modes. A 30 m² outbuilding came back at 17 m
  because a tree hangs over it, and a 60 m² kindergarten at 6.5 m median against
  a 12.8 m 95th percentile for the same reason. Footprints have to be eroded
  before they are sampled, and the statistic has to be chosen deliberately —
  ridge, eaves, or median are three different questions.

  And there is a better source than doing it ourselves: **LoD2 building models**,
  statewide and open in most Bundesländer, carrying a measured height *and a roof
  shape per building* — the very enum Wave 16 feature 7 has the user pick by
  hand. NRW ships them as addressable 1 km² CityGML tiles, and a Cologne tile
  holds 2,189 buildings with a height and a roof shape on every one of them.
  **This is now Wave 19**, planned in full.

  For trees the answer is thinner — they are not labelled at all — and that is
  Wave 19's second stage, kept separable for exactly that reason.
