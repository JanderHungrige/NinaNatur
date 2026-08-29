---
id: 33-imagery-objects
title: The Licence Question, Answered
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-8
wave_status: complete
depends_on: [31-map-selection]
relates: [32-object-heights]
source_files:
  - ninanatur/geo/orthophotos.py
  - ninanatur/api/geo.py
  - frontend/src/map/tiles.ts
  - frontend/src/components/MapPicker.tsx
routes:
  - GET /api/v1/geo/imagery
models: []
test_files:
  - tests/test_orthophotos.py
  - tests/test_map_selection.py
  - frontend/src/components/MapPicker.test.tsx
data_flow: reads-existing
last_synced: 2026-08-29
status: complete
phase: all
mdd_version: 11
tags: [orthophotos, licensing, dl-de, cc-by, imagery, attribution]
path: Garden/Imagery
integration_contracts:
  - function: GET /geo/imagery
    when: a place is chosen on the map
    note: imagery is offered per Bundesland because the licences are per Bundesland; a state without an entry gets none rather than a neighbour's
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects:
  - DinoTraining
---

# 33 — The Licence Question, Answered

## Feature 0: the research, and its answer

The wave held this feature behind a licence question, on the rule that kept this
project off NaturaDB: **no imagery is used until its licence is established, and
that does not bend because the data would be convenient.**

Probed service by service on 2026-08-29, reading each one's own
`GetCapabilities` rather than a summary of it:

| Bundesland | Licence | Required credit |
|---|---|---|
| Nordrhein-Westfalen | Open Data (GovData / VermKatG NRW) | © Geobasis NRW |
| Brandenburg | dl-de/by-2-0 | © GeoBasis-DE/LGB, dl-de/by-2-0 |
| Thüringen | dl-de/by-2-0 | © GDI-Th, dl-de/by-2-0 |
| Sachsen | kostenfrei, Geoportal-Bedingungen | © GeoSN |
| Niedersachsen | CC-BY-4.0 | © LGLN |
| Baden-Württemberg | dl-de/by-2-0 | © LGL-BW, dl-de/by-2-0 |
| Bayern | CC-BY-4.0 | © Bayerische Vermessungsverwaltung |
| Schleswig-Holstein | keine Beschränkungen (Open GBD) | © GeoBasis-DE/LVermGeo SH |

**The licence clears.** There is no federal source — the BKG endpoint refuses
anonymous requests with 403 — so this is a registry, not a URL.

## What was built, and what deliberately was not

Given a clear licence, the useful thing to build first is **not** recognition.

Feature 31 established that OSM holds no garden trees, and trees are the main
thing that shades a garden. The shortest path from that gap to a correct plan is
to let the user *see* their trees and draw them, which Wave 7's canvas already
supports. So this feature is the **aerial backdrop**: an optional orthophoto
under the outline, where a licence covers it.

Automatic recognition of roofs and crowns remains a sub-project. It has an
obvious starting point in the sister project `DinoTraining`, and it is not
something to half-build inside a wave.

## Business Rules

- **Per Bundesland, because the licences are.** A state with no entry gets no
  imagery rather than a neighbour's — using one state's photos over another's
  ground is using them outside their licence area.
- **The credit is shown whenever the imagery is.** DL-DE/BY-2.0 and CC-BY-4.0
  both require it, so a photo without its credit is a photo used outside its
  terms. It appears in the toggle's own label and in the attribution line.
- **One WMS request per view, not a tile grid.** These are state services sized
  for occasional use; slicing their output into dozens of requests per pan would
  be the same discourtesy the OSM tile policy spells out.
- **`CRS:84`, not `EPSG:4326`.** WMS 1.3.0 flips the axis order for EPSG:4326 and
  half the servers in the world disagree about it; CRS:84 is unambiguous lon/lat.

## Known Issues

- **Eight Bundesländer, not sixteen.** Hessen, Rheinland-Pfalz, Berlin, Hamburg,
  Bremen, Saarland, Sachsen-Anhalt and Mecklenburg-Vorpommern have no entry —
  some because the endpoint guessed at was wrong, some because the terms were not
  established. Absent rather than approximated.
- **Recognition is not built.** Trees are traced by hand from the photo.

## Bugs

(none new. One process failure worth recording: the imagery endpoint returned
404 in the browser while working in tests, because the running server predated
the route. Kill the server by PID and restart — the same trap this project has
already written down.)
