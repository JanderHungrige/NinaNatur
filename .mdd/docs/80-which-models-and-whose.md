---
id: 80-which-models-and-whose
title: Which Models, and Whose
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-19
wave_status: active
depends_on: [68-which-ground-and-whose]
relates: [68-which-ground-and-whose]
source_files:
  - ninanatur/geo/surface_sources.py
routes: []
models: []
test_files:
  - tests/test_surface_sources.py
data_flow: greenfield
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [dom, ndom, lod2, wcs, licensing, registry, buildings]
path: Map/Buildings
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Baden-Württemberg's only surface coverage is 5 m — listed, and refused by measures_buildings()."
  - "The LoD2 half is not built. Only Nordrhein-Westfalen's addressable tiles are verified; Bremen ships whole-state zips; the other states are unprobed."
  - "basemap.de 3D Gebäude is nationwide and anonymous but is 3D Tiles — geometry for rendering, probably without measuredHeight and roofType as attributes."
---

# Which Models, and Whose

Feature 0 of Wave 19, and the sibling of Wave 17's terrain registry. Same rule:
read from each service's own capabilities, confirm with a real request, and a
state with nothing gets no entry.

## Every state that has terrain has a surface model

Eight for eight, and it is not a coincidence — both come from the same airborne
laser scanning, and a survey that publishes one usually publishes the other. A
test asserts the equality, so if a state ever gains terrain without a surface
model, the building measurement is made to say so rather than to guess.

| State | Coverage | Product | Cell |
|---|---|---|---|
| Nordrhein-Westfalen | `nw_ndom` | **nDOM** | **0.5 m** |
| Mecklenburg-Vorpommern | `mv_ndom` | **nDOM** | 1 m |
| Niedersachsen | `ni_dom1` | DOM | 1 m |
| Hessen | `dom1` | DOM | 1 m |
| Brandenburg | `el_elevationgridcoverage` | DOM | 1 m |
| Berlin | Brandenburg's | DOM | 1 m |
| Sachsen-Anhalt | `Coverage1` | DOM | 1 m |
| Baden-Württemberg | `EL.ElevationGridCoverage` | DOM | 5 m |

Measured against real places: NRW's nDOM reads a median of 0.52 m and a maximum
of 27.98 m over a Cologne window — ground level and a tall building, which is
what an object-height raster should say. The DOMs read absolute heights: 54.87 m
of surface over Cologne against 51.22 m of terrain, and the difference is the
buildings.

## Two products, and the difference bites

**nDOM** is already differenced against the terrain, so a value is the height of
a thing above the ground it stands on. **DOM** is the raw surface in metres above
sea level, needing a second request and a subtraction.

Subtracting the terrain from an already-normalised model gives negative
buildings — and that failure looks like a bug in the shading model rather than
in the fetch, which is why `kind` is a field rather than something inferred from
the coverage name.

## Listed and refused are different jobs

Baden-Württemberg's only surface coverage is **5 m**. It is real, open, correctly
licensed and correctly in the registry — and a 5 m cell is wider than a small
dwelling, so its value is a blend of roof and garden.

So `measures_buildings()` is a separate function from `by_state()`. The registry
records what exists; the caller decides what it can use. Folding the two together
would mean the registry quietly deciding what may be asked.

## One assumption that cost a 404

Brandenburg's DOM1 is an INSPIRE service and wants **`x`/`y`**, where Hessen's
and Baden-Württemberg's INSPIRE services want `E`/`N`. There is no rule; it has
to be read per service, and the wrong one is a 404 rather than an error.

## The LoD2 half is not built

Two sources of building attributes exist and only one is verified:

- **CityGML per state.** Nordrhein-Westfalen's addressable 1 km² tiles carry
  `measuredHeight` and `roofType` on every building — 2,189 of them in one
  Cologne tile, checked while Wave 19 was planned. Bremen publishes whole-state
  zips, which suits a city-state and is a different fetch shape. The other
  states are unprobed.
- **basemap.de 3D Gebäude**, from the BKG at `sgx.geodatenzentrum.de` — nationwide,
  anonymous, and hierarchically tiled, which sounds ideal. It is **3D Tiles**:
  geometry for rendering. Height could be recovered from a mesh; roof shape
  almost certainly did not survive the conversion. Recorded as open research
  rather than adopted, because parsing glTF for a maybe is a poor trade against
  CityGML that states both attributes outright.

A surface model says **how tall**. Only LoD2 says **what shape the roof is**, and
that is the half Wave 16 currently asks a person to answer by looking out of the
window.
