---
id: 31-map-selection
title: Finding the Garden on a Map
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-8
wave_status: complete
depends_on: [26-drawing-canvas]
relates: [32-object-heights, 33-imagery-objects]
source_files:
  - ninanatur/geo/projection.py
  - ninanatur/geo/osm.py
  - ninanatur/api/geo.py
  - frontend/src/map/tiles.ts
  - frontend/src/components/MapPicker.tsx
routes:
  - GET /api/v1/geo/search
  - POST /api/v1/gardens/from-map
models: []
test_files:
  - tests/test_projection.py
  - tests/test_osm.py
  - tests/test_map_selection.py
  - frontend/src/map/tiles.test.ts
  - frontend/src/components/MapPicker.test.tsx
data_flow: mixed
last_synced: 2026-08-29
status: complete
phase: all
mdd_version: 11
tags: [map, osm, nominatim, overpass, attribution, tiles, projection]
path: Garden/Map
integration_contracts:
  - function: POST /gardens/from-map
    when: a user outlines their garden on the map
    note: coordinates are stored in metres and the latitude is rounded to 0.1° — the map knows where the garden is, the database does not need to
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 31 — Finding the Garden on a Map

## Purpose

Search an address, outline the garden on a map, and get a plan that already
carries the buildings that shade it. Wave 3's coordinate entry becomes the
fallback rather than the way in — nobody knows their bed is at x=3.5.

## Being a guest on other people's infrastructure

Nominatim and Overpass are free services run for the community, and the OSM tile
server is covered by a usage policy that says plainly what it expects. All of it
is treated as a condition of the feature, not paperwork around it:

- **Both API calls go through our server**, not the browser. The policies ask for
  a `User-Agent` that identifies the caller and for restraint in how often you
  call. One place can do that and share a cache; every visitor's browser cannot.
- **Search happens when asked**, never per keystroke.
- **Tiles are fetched for the visible window and no more.** The tile policy
  forbids bulk downloading and prefetching outright, and a layer that helpfully
  warms its neighbours is doing exactly that.
- **Attribution is shown from the first search on**, not only once the map
  appears — the address results are OpenStreetMap data too.

Tiles are computed rather than pulled in as a dependency: a tile layer is Web
Mercator arithmetic and a grid of images, and a map library would bring a second
coordinate system with its own opinions into a project that already owns a
metre-based one.

## The margin is the point

The selection is taken with **50 m** of surroundings, because what shades a
garden is mostly outside it. A 25 m margin — the first plan's number — loses the
morning and evening shade of ordinary houses: a 12 m house casts 45 m at a 15°
sun, an 8 m house 30 m.

Fifty metres would ordinarily mean a lot of objects. So an object is only taken
over **if its shadow could reach the garden at all** — height ≥ distance ×
tan 15°. Measured against a real address in Kleinmachnow: 11 buildings inside the
margin, **2** taken over. A 12 m house counts at 45 m, a 2 m fence only at 7.

## Business Rules

- **Coordinates are stored in metres**, converted once at the boundary. The
  projection is equirectangular around the garden's own centre — exact to
  millimetres at this scale and wrong at any larger one, which is why it is
  documented as not escaping the garden.
- **Latitude is still rounded to 0.1° on the way into storage.** The map knows
  where the garden is; the database does not need to.
- **Germany only**, matching the catalogue. A search that happily found Ohio
  would produce a garden this product has no plants for.
- **A polygon needs three points**, same rule as the drawing canvas.

## Security

No user input reaches a query: the Overpass query is built from a bounding box of
floats, and the address string is a request parameter to a third-party service,
never to a database. Coordinates are bounded to Germany by the schema before
anything is fetched.

## Known Issues

- **Trees do not come from the map.** OSM holds essentially none in residential
  areas — zero around the measured plot. They are drawn by hand, which Wave 7
  supports, and feature 33's aerial backdrop is what makes that accurate.
- **A building's footprint becomes a circle**, because the shading model is
  cylinders. It overstates a long building's shade at its ends.

## Bugs

(none — the two that appeared were in the tests' own fixtures: a building placed
beyond the reach of its own height, and a monkeypatch pointed at a name the
module no longer imported.)
