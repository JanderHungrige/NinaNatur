---
id: 102-which-tiles-and-whose
title: Which Tiles, and Whose
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [68-terrain-sources, 80-surface-sources]
relates: [07-solar-geometry, 32-object-heights]
source_files:
  - ninanatur/geo/tile_sources.py
  - ninanatur/geo/tile_entries.py
  - ninanatur/geo/tile_grid.py
  - scripts/probe_tile_sources.py
routes: []
models: []
test_files:
  - tests/test_tile_sources.py
data_flow: greenfield
last_synced: 2026-09-20
status: complete
phase: all
mdd_version: 11
tags: [tiles, elevation, dgm1, lod2, point-cloud, licence, attribution, registry, open-data]
path: Geo/Tile sources
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 102 — Which Tiles, and Whose

## Purpose

The fourth registry, after orthophotos (doc 8), terrain (doc 68) and surface
models (doc 80), and the same rule: **an entry means a real request of ours was
answered**, a state with nothing gets no entry, and a licence that forbids this
use is a state without an entry.

What is new is the shape of the thing being registered. The first three
registries hold *services*: ask for a window, get the window. This one holds
**files** — a state publishes its country as a grid of tiles and you take the
one your garden is in. That is the "secondary tier" Wave 17 named and never
built, and it is the only route into the eight states that publish the data and
run no service.

## Probed on 2026-09-20

Every line below is a request this repository made, with a HEAD where the host
allows one and a one-byte range where it does not
(`python -m scripts.probe_tile_sources`). Sizes are what the host reported.

| Entry | Answer | What it is |
|---|---|---|
| `bayern-dgm1` | 200, 2,558,672 B, `image/tiff` | DGM1 as a 1 km GeoTIFF |
| `bayern-lod2` | 200, 161,627,079 B | LoD2 buildings as CityGML, one square kilometre |
| `bayern-index` | 200, 21,996 B, `application/metalink4+xml` | the per-municipality index, with SHA-256 per tile |
| `nrw-lod2` | 200, 20,684,673 B | LoD2 buildings, NRW's own tile scheme |
| `nrw-laz` | 200, 34,967,590 B | the laser point cloud |
| `nrw-laz-index` | 200, 3,418,756 B, `application/json` | which point-cloud tiles exist |
| `copernicus-glo30` | 200, 31,889,167 B, `image/tiff` | a 30 m surface for a horizon ring, anywhere |

**The plan's index URL was on the wrong host.** Plan 04 recorded
`download1.bayernwolke.de/odd/…/metalink/{AGS}.meta4`; that path answers 404.
The index is served by `geodaten.bayern.de/odd/a/dgm/dgm1/meta/metalink/{AGS}.meta4`,
and both the five-digit and the eight-digit municipality key work. This is why
a registry entry is a request and not a citation.

## The second round, the same day

Twenty-two more candidates, every one of them answered. Sachsen refuses a HEAD
and allows a range, which is why the probe asks twice.

| Entry | Answer | What it is |
|---|---|---|
| `by-laser` | 200, 112,064,676 B | Bayern's point cloud — **and it is classified** |
| `ni-lod2` | 200, 43,632 B | Niedersachsen's LoD2, flat and dateless |
| `th-dgm1` / `th-dom1` / `th-las` / `th-lod2` | 200, 8.9 / 9.2 / 114.4 / 2.8 MB | Thüringen, all four, all zipped |
| `sn-dgm1` / `sn-dom1` / `sn-lsc` / `sn-lod2` | 206 after HEAD 401 | Sachsen, all four, all zipped |
| `bw-lod2` / `bw-ndom1` | 200, 7.5 / 16.4 MB | Baden-Württemberg's roofs, and a 1 m canopy height model |
| `mv-lod2` | 200 | Mecklenburg-Vorpommern, through a servlet |
| `rp-lod2` / `rp-laz` | 200, 88,216 B / 338,759,225 B | Rheinland-Pfalz's roofs and its cloud |
| `rp-dgm1` / `rp-dgm1-index` / `rp-dom1-index` | 200, 1.5 MB / 12.0 MB / 7.6 MB | its ground and surface, and the lists that name them |
| `sl-dgm1-zip` | 200, 559,134,521 B | Saarland — one Landkreis, because there is nothing smaller |

## "Six index states" was three different problems

Doc 102's first draft said Thüringen, Schleswig-Holstein, Hamburg, Bremen,
Rheinland-Pfalz and Sachsen "hand their tiles out through an index or an Atom
feed". Read properly, they do three unrelated things:

- **Thüringen and Sachsen compute perfectly.** Every one of Thüringen's 16,945
  height tiles and every one of Sachsen's 19,881 rows matches the grid pattern
  with no exception. What stood in the way was never an index: it is that the
  tile arrives **in a zip**. Their feeds are useful for enumerating coverage
  and for nothing else.
- **Rheinland-Pfalz and Schleswig-Holstein really do need one**, because the
  name carries a per-tile **flight year** (`dgm1_32_419_5490_1_rp_2022.tif`)
  that no arithmetic yields. Their LoD2, which carries no year, computes fine.
- **Hamburg and Bremen have no tile to address at all.** Both publish whole-city
  archives of 0.4–3.2 GB and nothing smaller; Hamburg's own LoD2 page says a
  smaller extract is *"kostenpflichtig zu beziehen"*. That is a packaging
  decision, not a missing index, and no index work will change it.

The lesson is doc 68's, again: the shape of a source is a thing to read, not to
infer from the words a catalogue uses.

## What Bayern's laser has that NRW's has not

Doc 107 had to borrow the building model to tell a roof from a crown, because
NRW's tile has ground and "unclassified" and nothing else. Bayern's, on the
published class list and on two decoded tiles, has **class 6 for buildings and
class 20 for plants** — and 20 is not the ASPRS vegetation class, so a reader
looking for 3, 4 and 5 finds nothing. Munich measures 20.4 points per m²
against the state's guaranteed 4, which is the half-metre cell rather than the
metre one.

It is also **not on the download host**: every `download1.bayernwolke.de` path
for it answers 404. The address came out of the product's own metalink, whose
size and sha-256 the fetched tile matched.

## Asked, and the answer was no

- **Bayern's *Einzelbäume*** — doc 108 named it as the better source for trees.
  It is not. The published attribute list is `id`, `dgmhoehe`, `baumhoehe`: a
  position, the ground under it and the tree's height. No species, no crown
  width, and **no crown base** — which is the one thing the shading model
  cannot get elsewhere and the point cloud does give. It is also 40 GB in 86
  lots keyed by production run rather than by the grid. Asked, read, declined.
- **Saarland's licence**, doc 102's other open question, is **fine**: the
  download is dl-de/by-2-0, *"© GeoBasis DE/LVGL-SL (Jahr der Bereitstellung)"*,
  and the restrictive wording that kept it out of doc 68 belongs to a legacy
  service record. What Saarland has no route for is **one tile**: the share
  holds six per-Landkreis archives, 559 MB for the ground and 12.5 GB for the
  cloud.
- **Hessen** charges for its point cloud (*"fallen Gebühren nach Zeitaufwand
  … an"*), publishes no per-tile raster, and puts a token in its download path
  that only resolves for a day.
- **Berlin's point cloud** is nine regional bundles of 1–50 GB whose members
  are packed with **deflate64**, which Python's `zipfile` cannot read.
- **Baden-Württemberg's surface model is no longer 5 m**, which this wave's
  plan assumed: DOM1 at 1 m and **nDOM1**, a 1 m canopy height model already
  normalised to the ground, are both open.

## The two questions this feature existed to answer

**Is the federal LoD2-DE an open, tileable product?** *No.* It exists —
`3D-Gebäudemodelle LoD2 Deutschland (LoD2-DE)`, CityGML, height accuracy about
a metre — and its own product page says: *"Dieses Produkt steht nur einem
eingeschränkten Kreis Nutzungsberechtigter zur Verfügung"*, listed as
*"nur für Bundesbehörden"*. Price €0.00 and not for us. **Feature 3 stays
per-state**, which is a dozen adapters rather than one, and the doc says so
before the work is planned around the other answer.

**Are Niedersachsen's point clouds open now?** *No.* Its OpenGeoData catalogue
lists LoD1, LoD2, bDOM20, DGM1, DOM1, orthophotos and the topographic maps —
and no laser data of any kind. The availability list's "planned 2024" has not
arrived in the portal. Niedersachsen is therefore a **raster** state for
feature 5: its open bDOM20 and DOM1 carry the trees, without the crown base a
point cloud would give.

## What an entry holds

`geo/tile_sources.py`, one `TileSource` per state and product:

- `state`, `product` — `dgm1` | `dom1` | `lod2` | `laz`.
- `url_for(east_km, north_km)` — the tile's address, computed from UTM
  kilometres, because every one of these schemes is the grid written down.
- `tile_km` — 1 or 2; `fmt` — GeoTIFF, CityGML, LAZ, zip.
- `licence`, `attribution` — the same rule as doc 68: **no entry may be
  chargeable, and every entry carries the credit its licence asks for.** A
  height shown without its credit is a height used outside its licence.
- `vertical_step_m` for a raster, `points_per_m2` for a cloud — what the number
  is worth, so the page can say how fine it is.
- `index_url` where the state publishes one, for the tiles that exist.

**The tile name is arithmetic, not a lookup.** Bayern writes `690_5334.tif`;
NRW writes `LoD2_32_347_5647_1_NW.gml` — the same two numbers, one in
kilometres of easting with the zone prefix dropped, the other with it kept. The
registry holds the scheme and `tile_of` round-trips it, which is what the test
checks for every entry.

## What is not here yet, and why

The states whose portals hand out tiles through an index or an Atom feed —
Thüringen, Schleswig-Holstein, Hamburg, Bremen, Rheinland-Pfalz, Sachsen — need
the index fetched, cached and resolved before a URL exists. That is feature 1's
work, and each state joins this registry when its index answers. Saarland's
download licence (dl-de/by-2-0 per the catalogue, while its WCS forbids
embedding) still needs its licence text read from the source.

## Business Rules

1. **An entry is a request that was answered**, dated, by the probe script —
   never a portal page that says a thing exists.
2. **Nothing chargeable, and never a licence that forbids this use**, whatever
   a catalogue says about it.
3. **Every entry carries its attribution**, and the plan shows it wherever the
   number is used.
4. **A gap is a gap.** No state borrows its neighbour's ground.
5. **The probe is not a test.** A suite that needs sixteen state portals to be
   up fails on their maintenance window; the probe is run deliberately and its
   date is written here.

## Dependencies

Doc 68 (terrain services) and doc 80 (surface services) for the rule and the
shape; `ingest/http.py` for the fetch and its politeness.

## Security

Every URL is built from two integers and a fixed template; nothing user-typed
reaches a path. The hosts are named in the registry, so a tile cannot be
fetched from somewhere a garden's data suggests.

## Known Issues

- **Schleswig-Holstein waits on the index reader**, which now exists but reads
  metalink and not GeoJSON. Two quirks are already known and not yet handled:
  it appends an HTML footer to every download, and a stale row answers **200
  with an HTML error body** rather than a 404, so the content type is the only
  honest check.
- **Hamburg and Bremen cannot join at all** while they publish only whole-city
  archives. Range-reading a member out of a remote zip is possible — Saarland's
  share was proved to allow it, 1.6 MB instead of 559 — and it is not built.
- **Sachsen's share tokens could rotate.** They are constants in the entry, one
  per product, and the state's own download index already carries two stale
  ones; `index_url` points at the configuration that has the current set.
- Bayern's laser is LAS 1.2 in lots up to 2021 and **LAS 1.4 point format 6**
  from 2022, with extra per-point fields. A reader that only reads the legacy
  point count gets zero from the newer lots.

## Bugs
