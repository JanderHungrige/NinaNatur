---
id: ninanatur-wave-25
title: "Wave 25: Down to the square metre"
initiative: ninanatur
initiative_version: 23
status: in_progress
depends_on: ninanatur-wave-21
demo_state: "Ein Garten in München, Dresden, Wiesbaden oder Kiel bekommt sein Relief, seinen Horizont und die Nachbarhäuser mit gemessener Höhe und Dachform — und in Nordrhein-Westfalen kennt jeder Baum in der Nachbarschaft seinen Kronenansatz, aus der Punktwolke. Jede Zahl sagt, woher sie kommt und wie fein sie ist. (Das eigene Grundstück mit dem Telefon zu vermessen ist am 2026-09-20 in den Backlog gegangen, Feature 6.)"
created: 2026-09-07
hash: 75f01f33
---

# Wave 25: Down to the square metre

## Demo-State

Ein Garten in München, Dresden, Wiesbaden oder Kiel bekommt sein Relief, seinen
Horizont und die Nachbarhäuser mit gemessener Höhe und Dachform — und in
Nordrhein-Westfalen kennt jeder Baum in der Nachbarschaft seinen Kronenansatz,
aus der Punktwolke. Jede Zahl sagt, woher sie kommt und wie fein sie ist.

*Das eigene Grundstück mit dem Telefon zu vermessen* gehörte zu diesem
Demo-State und ist am **2026-09-20 in den Backlog** gegangen (Feature 6, unten).

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
| 1 | a-tile-not-a-service | 103 | 8 states of tiles — **ground everywhere** | 0 |
| 2 | a-horizon-for-everyone | 104 | built | 0 |
| 3 | every-roof-in-the-country | 105 | 13 states built | 1 |
| 4 | the-cloud-under-the-crown | 107 | 7 states built | 1, 3 |
| 5 | the-trees-in-the-other-states | 108 | 8 states built | 1 |
| 6 | measure-my-own-garden | — | **backlog** | 4 |
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

- **2026-09-20 — feature 5, the trees in the other states** (doc 108), Bayern.
  `canopies_in` has only ever worked where a state runs a coverage service, so
  a garden in Bayern had no trees around it — not because there are none.
  Bayern's own catalogue, read rather than guessed at, has *DOM20*: a
  **twenty-centimetre** surface model, CC BY 4.0, one-kilometre tiles, five
  times finer than anything in doc 80's registry. The tile address came out of
  the state's metalink index and three computed names were checked against the
  server (43.7, 48.4, 51.1 MB, all 200). Its scheme writes the zone onto the
  front of the easting, which `tile_of` now reads back.

  Two things followed from a 5,000 × 5,000 tile. The pixel guard grew to thirty
  million — a square kilometre at 20 cm is 25, which is a tile and not a
  malformed header — and **the mosaic stopped being a mosaic**: four of those
  tiles are 400 MB for a 400 m window, so the tiles are now pasted straight
  into the window's own extent, which is five. The subtraction that turns
  metres above the sea into metres above the ground is shared with the service
  path rather than copied.

  The same catalogue lists *Laserdaten* and *Einzelbäume* — surveyed individual
  trees — and neither is in the registry, because an entry is a request that
  was answered and those have not been asked.

- **2026-09-20 — the other states, and the thing that was actually in the way.**
  Twenty-two more candidates probed, every one answered, and the wave's own
  framing turned out to be wrong. Doc 102 called six states "index states";
  read properly they were three different problems. **Thüringen and Sachsen
  compute their tile names perfectly** — 16,945 and 19,881 of them checked
  against the pattern without one exception — and what stood in the way was
  simply that each tile arrives **in a zip**. Rheinland-Pfalz and
  Schleswig-Holstein genuinely need an index, because their raster names carry
  a per-tile flight year. Hamburg and Bremen publish no tile at all, only
  whole-city archives, which no index would fix.

  So the code was `geo/tile_zip.py`, and it bought six states. Thüringen and
  Sachsen — both fully gapped until today — now have **ground, the surface
  model over it, and surveyed roofs**. Brandenburg, Berlin and
  Mecklenburg-Vorpommern gained roofs their coverage services never carried,
  Niedersachsen's LoD2 turned out to need no index at all, and
  Baden-Württemberg gained both roofs and `nDOM1`, a 1 m canopy height model
  that closes the gap its 5 m surface service left for finding trees. The
  building model reads all eight states unchanged: feature 3 never did become
  a dozen parsers.

  What was inside each archive was **read rather than assumed**, and two things
  came out of that. Baden-Württemberg puts *four one-kilometre tiles in one
  two-kilometre archive*, inside a folder named after the archive — so the
  first version placed all four on one corner, and the test written to catch it
  passed anyway because four separate NaNs are four distinct values. Its grid
  also starts on an **odd easting**, which no other state's does. And writing
  the doc caught a bug the tests had not: `nDOM1` is *already* metres above the
  ground, so the surface path would have subtracted the terrain from it a
  second time and buried every tree three hundred metres down.

  **Bayern's point cloud is the other find.** It is not on the download host —
  every bayernwolke path for it is a 404 — and unlike NRW's it is *classified*:
  class 6 buildings, class 20 plants, 20.4 points per m² measured in Munich
  against the state's guaranteed 4. Doc 107 had to borrow the building model to
  tell a roof from a crown; in Bayern the cloud says so itself.

  Two long-standing questions closed by asking. **Saarland's licence is fine**
  — dl-de/by-2-0, the restrictive wording belongs to a legacy service record —
  but it publishes nothing smaller than a 559 MB Landkreis. And **Bayern's
  *Einzelbäume*** carries a position and two heights and **no crown base**, so
  it is worse than the cloud we already read, and it is not an entry.

- **2026-09-20 — Rheinland-Pfalz, through its own list.** The last fully
  gapped state of any size, and the one that genuinely needed the index the
  wave planned: it writes the **flight year** into a raster's name
  (`dgm1_32_419_5490_1_rp_2022.tif`) and the tile next door was flown in 2025,
  so no arithmetic reaches it. Its metalink is 12 MB and **21,160 tiles**
  across four flight years with a sha-256 each — parsed in 1.5 s, once for the
  whole deployment, and a name out of it fetched and answered 200.

  The rule that shaped the code: **an index is remote content, and it is read
  as data rather than as an address.** What is taken from it is a *file name*,
  matched against a strict character set and kept only if it carries the grid
  it claims; the scheme, the host and the folder stay the registry's own, and
  the metalink's `<url>` element is never read at all. Doc 102's guarantee
  gains one clause rather than losing its meaning: an address is a template and
  two integers, or a template and a name the state gave us. A test forges that
  element and checks nothing changes.

  Rheinland-Pfalz joined whole — ground, surface, roofs and a 338 MB point
  cloud — which is what the credits invariant was holding out for.

- **2026-09-20 — Saarland and Hamburg, out of archives never fetched.** Doc 102
  had recorded both as unreachable: they publish no tile, only whole regions —
  Hamburg 0.7–1.4 GB per product, Saarland a Landkreis at a time, 559 MB for
  the ground and **12.5 GB** for the cloud. That was written down as a
  packaging decision no index would fix, and it was wrong.

  A zip keeps its index at the **end**. With range requests an archive reads
  like a local file, and only the bytes of one member are ever asked for.
  Against Saarland's real ground archive: its directory of 311 members costs
  **3 requests and 34,888 B**, and one 4 MB tile two more — **0.38 % of the
  file, in 2.0 s**. End to end, a garden near Merzig: six districts' directories
  give 2,775 tiles across the state in 11.8 s, the window follows in 3.2 s, and
  200 × 200 m at one metre comes back with every cell known, 223.8 to 241.6 m.

  The parsing is the standard library's. `zipfile` already knows Zip64 — which
  a 12.5 GB archive needs — so `remote_zip` supplies the one thing it lacks, a
  seekable file whose reads are range requests. Writing a second zip parser to
  save an import would be the wrong kind of clever.

  Saarland joined **whole**: ground, surface, roofs and a point cloud, out of
  124 GB it never downloads. All twenty-four of its archives were probed and
  all answered. Hamburg gained ground, surface and roofs.

  There are now three ways a tile has an address — computed, named by a state's
  list, or a member of an archive — and one function returns all three in the
  same shape, so the raster path, the building path and the cloud path each see
  one thing.

- **2026-09-20 — the decoder had never read a whole tile.** Hamburg's square
  kilometre took **492.9 seconds**, of which the fetch was three. Every state
  in this registry ships **LZW** — Bayern, Thüringen, Sachsen,
  Rheinland-Pfalz, Hamburg, all checked that day — and the LZW decoder was
  written in Wave 17 for what a coverage service answers: a 400 m window, a
  quarter of a megabyte. It kept every byte the stream had ever held in one
  Python integer, so each shift cost the whole of it and the loop was
  **quadratic**.

  One line, dropping the bits already consumed, and the same tile decodes in
  **0.58 s**. Bayern 0.90, Thüringen 1.27, Rheinland-Pfalz 0.56, Sachsen's
  four-square-kilometre tile 0.69 — that last would have been half an hour.
  Munich reads 510.5 to 522.7 m against the 523.8 m doc 104 measured from
  Copernicus at the same place, and Hamburg reads −0.5 to 2.6 m, which is
  Hamburg.

  **Nobody noticed because every fixture in the tile tier is a TIFF this
  repository wrote to its own expectations** — uncompressed, because that is
  the easy thing to write. The suite was green through three features and ten
  states. A tile tier is not tested until a real tile has been through it, and
  the regression test now decodes a megabyte of real LZW and fails if it goes
  slow again.

- **2026-09-20 — Schleswig-Holstein and Bremen, and with them the whole
  country.** The last two states, and the same obstacle: both publish their
  ground only as **XYZ** — a million lines of `easting northing height` to the
  square kilometre, twenty-eight megabytes of ASCII for four of binary — where
  every other state publishes a raster.

  Three things were measured and each changed the code. **A tile is not always
  a million lines**: Schleswig-Holstein's border tiles carry 730,232 or 829,760
  or 999,000, with holes inside a row, and there is **no NoData token anywhere**
  in 4.5 million points checked — a cell nobody surveyed is simply an absent
  line. So values are placed by their own coordinates rather than by counting,
  and a gap stays a gap. **Bremen disagrees with itself four ways**: bare
  integer eastings in the city, the zone glued on in Bremerhaven
  (`32466000.5`), a double underscore in one filename and a single one in its
  neighbour, north-first in one archive and south-first in another, and an
  `x y z` header line above the grid. And **every Schleswig-Holstein download
  carries a 760-byte HTML footer**, with a stale row answered as 200 and an
  HTML apology rather than a 404.

  Its terrain model needs the state's list, because the name carries a per-tile
  survey year — 2005 in one tile and 2025 in its neighbour. Its building model
  carries no year and a fixed one in the query, so that one is arithmetic. The
  list is GeoJSON rather than metalink: one more parser, no new idea, and the
  address still built from the registry's own template.

  Bremen needed no new fetch code at all — the archive tier already reached it.

  Verified end to end that day: Kiel, Rendsburg and Bremen each return a
  200 x 200 m window at one metre with every cell known. Rendsburg reads 2.2 to
  8.3 m for a town about five metres up; Bremen's ground tops out at 4.8 m where
  its surface reaches 33.5, and the difference is the houses. Cross-checked
  against Copernicus at the same points, which agrees — including at a hill
  where the DGM1 read 50.8 to 64.7 m and Copernicus 54.9 to 69.0, so the number
  that looked wrong was my coordinate rather than the data.

  **Ground now reaches 100 % of the population** — every one of the sixteen
  states. Surface 97 %, surveyed roofs 89 %, point clouds 54 %.

  A correction belongs here too: this wave's XYZ commit claimed `np.loadtxt`
  takes 2.86 s where `fromstring` takes 0.21. That was measured under
  `tracemalloc`, which taxes the allocation-heavy one far more. Without it they
  are 0.18 and 0.21 — near enough the same. The reader keeps `fromstring` for
  returning three columns in one pass, not for speed, and the docstring says so
  now.

- **2026-09-20 — a way to find out that a state moved, before a gardener does**
  (doc 109). Not one of the wave's eight features; asked for on the day, and
  the registry is what made it possible. Forty-nine sources across sixteen
  surveying offices, and in the two days this registry took to build, four of
  them changed underneath it.

  It cannot be a ping. Every one of Niedersachsen's dead LoD2 tiles is listed
  by a live index, and Schleswig-Holstein answers a stale row with **200 and an
  HTML apology** — a checker reading status codes would call all of it healthy.
  So a source passes only when the bytes are what they claim: `II*` for a TIFF,
  `LASF` for a cloud, a root element for CityGML, a directory that still holds
  the square kilometre.

  Writing it earned its keep twice over. It found its own cap was smaller than
  Rheinland-Pfalz's twelve-megabyte index, and then something better: **silent
  is not absent.** Bayern's laser host serves no range and states no length, so
  the first run called a healthy source gone. "Does this answer" is now a
  different question from "how large is it", and a source that will not be
  looked into is reported as unread rather than as well.

  `probed_tile` joined `probed_bytes` on every computed entry, so there is a
  square kilometre to ask for and something to compare against. The logic is
  tested offline against all four real failures; the thing that touches the
  network is a script whose exit code is the alarm, never a test — doc 102's
  rule, kept. **Baseline: 49 of 49.**

- **2026-09-21 — the elevation stack became a package** (doc 110). Not one of
  the wave's eight features; asked for once the wave had built something with
  no equivalent on PyPI. `packages/geokachel`, MIT — and the repository has a
  LICENSE for the first time, having been public with none, which meant all
  rights reserved and nobody able to reuse any of it.

  The seam is one sentence: **the package stops at a north-up raster in the
  source's own UTM, and putting that on somebody's own axes is theirs.** UTM
  grid north is up to 2.3° off true north here; a shadow model must correct for
  it and a map-maker must not have the correction imposed. So `resample` and
  the garden frame stayed, and everything about where a tile lives and what
  comes out of it moved — seventeen modules unchanged, `addressing.py` cut out
  of `tiles.py`, `net.py` and `cli.py` written for it, forty-five files'
  imports rewritten. 1,530 tests passing before and 1,530 after.

  **A panel said not yet, and the owner overruled it.** The argument against
  was real — the registry is both the only thing worth packaging and the thing
  that churns most, so extraction turns a one-step fix into two and a half.
  That is answered by not depending on PyPI: the package lives in this
  repository and the image installs it from the same commit, so a state moving
  a file is still one commit. Publishing is an occasional act, not a dependency.

  Three things the build caught that reading would not. **There was no
  `py.typed`**, so mypy silently treated every symbol from the new package as
  `Any` and the app that had just been refactored onto it lost its types
  without a word — three stray "returning Any" errors were the only trace. The
  `Coverage` protocol declared **mutable attributes**, which a frozen dataclass
  cannot satisfy. And the **supply-chain test caught the new workflow** using
  `@v4` tags instead of pinned commits, which is exactly what it is for.

  Doc 109's health check ships inside it as `geokachel check`, so whoever
  installs the package can find out that a state moved — not only this app. It
  runs weekly in `.github/workflows/sources.yml` and **does not fail the
  build**: it opens an issue, or comments on the open one.

  Verified as a package rather than as a directory: the wheel builds, carries
  `py.typed` and both licence files, and installs into a clean 3.13 venv with
  three dependencies and no trace of NinaNatur, where its registry, readers and
  CLI all work. And verified in the image, because the Dockerfile changed —
  built, run against a **fresh empty volume**, `/healthz` ok, `geokachel` 0.1.0
  importable inside with all sixteen states carrying ground, the CLI on the
  path at `/usr/local/bin/geokachel`, a garden created and the front page
  served.

- **2026-09-20 — the image was built and run, because the wave added a binary
  dependency.** `docker build` (404 MB) and a run against a fresh empty volume,
  as the project's own rule asks: `laspy` 2.7.0 with the `Lazrs` and
  `LazrsParallel` backends available inside the image, every tile source
  importable, `/healthz` ok, the front page served and
  `GET /gardens/{token}/sources` answering `[]` for a garden that rests on
  nothing. The lock resolves 33 wheels for `lazrs`, so the Linux one is in it —
  and the run is what turns that from an inference into a fact.

- **2026-09-21 — the owner's check of waves 24 and 25.** Waves 24 and 25 went
  to the preview together, and the owner used them and sent eleven items. Each
  was investigated before anything was changed (nine read-only agents, three
  adversarial verifiers for the bugs); then four agents in parallel worktrees
  built #5+#8, #6, #7+#10 and #9, while the canvas items (#1–#4, #11) were done
  here. The branch `feat/ninanatur-owner-check` merges all of it.

  | # | Asked | Done | Doc |
  |---|---|---|---|
  | 1 | lines too thick to draw in detail | outlines in screen pixels; his ink and waves never larger than at 1:250; the wobble capped at 7 px | 112 |
  | 2 | Vieleck corner lands next to the click | it was the grid rounding every click to a metre: magnetic within 6 px, Alt never; closing at 12 px, which also stopped a 3 × 1 m bed saving as a triangle | 112 |
  | 3 | freehand "needs two points", then every add fails with 422 | the server stored a row and only then failed to draw it, for ever after. It checks before it writes now, a reshape keeps a path's width, and a one-time repair opens broken gardens | 111 |
  | 4 | zoom with the wheel | a plain wheel, in proportion, about the pointer; Safari's pinch; the address map too | 112 |
  | 5 | day play button under Tagesverlauf | a day player in the sun panel, following the Zeitraum, pausing when hidden | 65, 87 |
  | 6 | shade raster too coarse | the grid covers the plot + 5 m, not the neighbourhood: 3 m → 1 m on a map-made garden in the same time; stored maps read stale once | 64 |
  | 7 | Zurück zum Garten more prominent | a filled button, first, sticky | 88 |
  | 8 | animations while things compute | a pending counter, a spinner, a note in the header, a sweep over the plan, the front page's waits | 87 |
  | 9 | do suggestions use the sun? | yes, and they did; now a bed too bright for a species leaves it out, the list says when light is missing or stale, and the woody list follows light | 13 |
  | 10 | colour the ground, from OSM? | Technisch's ground is grass now; OSM is credited where its shapes are drawn; landcover polygons not built (recommendation: an orthophoto first) | 95, 106 |
  | 11 | laggy when zooming and dragging | a pan redraws the backdrop, not the garden; the sun map and relief are a few paths; the costly paint pauses while moving | 113 |

  **Checked in the running app** (a local server on a copy of a scratch database,
  2026-09-21): a freehand press refused on the client with "zu kurz" and nothing
  sent; corners landing on the click, pulled onto a grid point only a few pixels
  away; a path reshaped by its corner keeping its 1 m width, the garden still
  reading 200; the wheel zooming about the pointer, the outlines staying one
  pixel at the closest zoom in both styles; the sun map drawn as 10 paths and no
  rects; the day player under the chip, playing; the rebuild's spinner, header
  note and sweep; "Suche…" and "Wird angelegt…" on the front page; a garden made
  from the map in Kleinmachnow with "Karte: © OpenStreetMap-Mitwirkende" under
  its plan; the address map stepping a level on one wheel notch while the page
  stayed put.

  **What the browser found that the tests had not**: a rebuild left every bed
  saying "noch nicht berechnet" beside the map it had just computed (it did not
  read the garden again); the drawing's instructions and a complaint lay under
  the tool's hint, unreadable; with the sheet up, the plan's scale and credits
  climbed over the header. All three fixed, the first with a test that fails
  without it.

  **What the merge and the review found**: a perennial planted from the list
  marked the shade stale (the signature hashed every planting; now only those
  that shade); CI's "API types in sync" gate had compared nothing since it was
  written (`git diff` run from inside `frontend/`), and the schema it would
  have compared depended on git and on a built bundle, both fixed and the gate
  seen failing on purpose; the day player's clock was a live region that would
  have read out every frame; and the repair would have deleted zero-area beds
  that still opened, with their plants. `api/light.py` (350 lines) was split.

  The review ran as a workflow of five reviewers and three adversarial
  skeptics per finding (80 agents; the first run hit a session limit and was
  resumed). Of 25 findings, 20 were confirmed and fixed, 5 refuted. Beyond the
  four above: a map import failed after committing its garden when one OSM
  building's corners merged (now its square); a plotless garden of surfaces got
  no grid and an old map read stale for ever; OpenStreetMap's credit was
  inferred and lost for a corrected map house (now `element.outline_source`,
  written by the import only, with a backfill); an iPhone pinch zoomed twice;
  a month picked during a rebuild was overwritten; the list's "Schatten
  berechnen" was fooled by any new map; reduced motion mid-play hid the pause
  button of a running day; two buttons dropped the keyboard focus; `npm run
  generate:api` could not run; and seven doc passages said what was no longer
  so.

- **2026-09-21 — released to production as V0.23.217** (merge `50a617b` from
  `dev-deployment`, at the owner's word "push und merge into main"). The
  release runbook's gate failed first: on the phone the smoke test's new patch
  lay hidden under the chosen bed's handles, because an unplaced patch's seeded
  spot can land on a corner; default spots now keep off the bed's rim, and the
  gate passed in both windows on the preview. Production serves the preview's
  assets exactly (`index-DFDjOJu1.js`, `index-COJrsAG7.css`). Its migrations,
  after the automatic pre-migration copy: `element.outline_source` added, four
  reshaped paths given their width back, two undrawable elements of garden 3
  removed (an outline with no points, a zero-length freehand line — that garden
  could not be read before), and 394 map outlines marked as OpenStreetMap's.
  Found on the way: the header's "Sonne & Schatten" looked as if it loaded for
  ever on dev and on main — it was disabled until a map existed, and every
  disabled button wore the busy cursor; the host's logs showed no rebuild was
  ever asked for. Fixed in this release.

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
- **The gardener's own measurement (feature 6), moved to the backlog on
  2026-09-20.** What it would be is written up in `### 6. measure-my-own-garden`
  below and in plan 04 § 6.4: a phone scan uploaded and rastered, georeferenced
  by control points the gardener clicks on the plan. Two things make it a wave
  of its own rather than the tail of this one — it parses a file a stranger
  uploads, which is the sort of surface Wave 20's review exists to weigh, and
  how somebody places a control point on a plan is a design question nobody has
  answered yet. Everything it depends on (feature 4) is built and waiting.
