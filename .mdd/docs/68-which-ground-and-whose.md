---
id: 68-which-ground-and-whose
title: Which Ground, and Whose
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-17
wave_status: active
depends_on: []
relates: [63-neighbours-from-the-plot, 64-light-across-the-bed]
source_files:
  - ninanatur/geo/terrain_sources.py
routes: []
models: []
test_files:
  - tests/test_terrain_sources.py
data_flow: greenfield
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [terrain, dgm, wcs, licensing, provenance, registry]
path: Map/Terrain
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Nine Bundesländer have no entry: no anonymous bbox coverage service was reached for Bayern, Berlin, Bremen, Hamburg, Rheinland-Pfalz, Sachsen, Sachsen-Anhalt, Schleswig-Holstein, Thüringen."
  - "Baden-Württemberg's INSPIRE coverage quantises height to whole metres, not the 0.01 m the DGM1 specification states."
---

# Which Ground, and Whose

Feature 0 of Wave 17, and it comes first for the reason every registry in this
project comes first: the licence question is answered before the pipeline
exists, not after somebody notices.

## What was done

Sixteen Bundesländer, probed on 2026-09-05. Every entry read from the service's
own `GetCapabilities` and then confirmed with a real `GetCoverage` for a 200 m
box — because "the metadata says it is open" and "it hands me a window of ground"
are different claims, and only the second one is the feature.

Finding the endpoints by guessing was going nowhere, so they came from the
**GDI-DE catalogue** (`gdk.gdi-de.org`, CSW GetRecords over 417 service records)
rather than from URL patterns.

## Six states answer

| State | Coverage | EPSG | Axes | Licence |
|---|---|---|---|---|
| Nordrhein-Westfalen | `nw_dgm` | 25832 | x/y | dl-de/zero-2-0 |
| Brandenburg (+ Berlin data) | `bb_dgm` | 25833 | x/y | dl-de/by-2-0 |
| Niedersachsen | `ni_dgm1` | 25832 | x/y | CC-BY-4.0 |
| Mecklenburg-Vorpommern | `mv_dgm` | 25833 | x/y | keine Bedingungen, Quellenvermerk Pflicht |
| Hessen | `he_dgm1` | 25832 | E/N | dl-de/zero-2-0 |
| Baden-Württemberg | `EL.ElevationGridCoverage` | 25832 | E/N | dl-de/by-2-0 |

All six return a 200 × 200 m window at 1 m in a single request, 72–156 KB.

## Saarland is why this is a registry and not a URL

Its service answers. Its metadata is listed as open by every aggregator,
`hoehendaten.de` included. Its own `AccessConstraints` say:

> "Jegliche andere Nutzung, so auch das Einbinden in weitere Anwendungen
> (Download) ist kostenpflichtig"

Viewing it in the state's own portal is free. Using it here is not. **It is
therefore not in the registry** — and it is the reason the test asserts the rule
("no entry may be chargeable") rather than the absence of a name. Its coverage
also turned out to be 5 m rather than the DGM1 its title claims.

## Three things that would have been silently wrong

**Axis names are not uniform.** The state services want `SUBSET=x(…)`; the
INSPIRE ones want `SUBSET=E(…)`. The wrong one is not an error message — it is a
404, which is how Hessen and Baden-Württemberg first appeared to be broken.

**Baden-Württemberg is big-endian 16-bit unsigned integer** where the others are
little-endian 32-bit float, and its heights are **whole metres**. Read as the
others are read, it produces numbers in the millions. Read correctly, Stuttgart
comes out at 241–244 m, which is right — but a 20 m garden on a 3 % slope rises
0.6 m, and whole metres cannot see that. Recorded as `vertical_step_m` so the
page can say so instead of implying precision it does not have.

**Compression is not uniform either.** NRW and Niedersachsen return LZW;
Brandenburg, M-V and Hessen return uncompressed. Feature 1 needs a decoder for
both, and the registry is where that is known before the request is made.

## Nine states have no entry

Bayern, Berlin, Bremen, Hamburg, Rheinland-Pfalz, Sachsen, Sachsen-Anhalt,
Schleswig-Holstein and Thüringen. Several publish DGM1 as open data by download
or as a WMS; Thüringen's `.../services/DGM` answers a WCS request with WMS
capabilities, and Sachsen and Sachsen-Anhalt return 403 to anonymous requests.
The federal `sgx.geodatenzentrum.de/wcs_dgm1` also returns 403 — exactly as the
BKG orthophoto endpoint did in Wave 8.

**A gap stays a gap.** `by_state` returns `None`, the garden keeps the flat
assumption, and feature 6 says so on the page. No neighbour's ground, no coarser
federal substitute quietly swapped in.

## Tests

`tests/test_terrain_sources.py` asserts the rules rather than the contents: every
entry names a licence and a credit, no entry is chargeable, axes and projection
are one of the known values, no state appears twice, a missing state returns
`None`, and the coarse vertical step is recorded rather than rounded away.

Verified by putting Saarland back in — the licence test fails, with the offending
text in the message.
