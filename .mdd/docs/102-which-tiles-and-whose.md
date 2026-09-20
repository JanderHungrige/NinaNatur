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

- Six states wait on feature 1's index resolver (above).
- Saarland's download licence text is not yet read from the source.

## Bugs
