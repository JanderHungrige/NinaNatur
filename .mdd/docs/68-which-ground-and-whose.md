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
  - "Eight Bundesländer have no entry, each for a stated reason. Bayern's data is open but its coverage service needs credentials; Thüringen, Sachsen, Schleswig-Holstein, Hamburg, Bremen and Rheinland-Pfalz have no anonymous coverage service found; Saarland's licence forbids this use."
  - "About 64 % of the population is covered. 'Not found' is not 'does not exist' — the four smallest gaps were probed less thoroughly than the rest."
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

## Eight states answer

| State | Coverage | EPSG | Axes | Licence |
|---|---|---|---|---|
| Nordrhein-Westfalen | `nw_dgm` | 25832 | x/y | dl-de/zero-2-0 |
| Brandenburg | `bb_dgm` | 25833 | x/y | dl-de/by-2-0 |
| **Berlin** | `bb_dgm` (Brandenburg's) | 25833 | x/y | dl-de/by-2-0 |
| **Sachsen-Anhalt** | `Coverage1` | 25832 | x/y | dl-de/by-2-0 |
| Niedersachsen | `ni_dgm1` | 25832 | x/y | CC-BY-4.0 |
| Mecklenburg-Vorpommern | `mv_dgm` | 25833 | x/y | keine Bedingungen, Quellenvermerk Pflicht |
| Hessen | `he_dgm1` | 25832 | E/N | dl-de/zero-2-0 |
| Baden-Württemberg | `EL.ElevationGridCoverage` | 25832 | E/N | dl-de/by-2-0 |

All eight return a 200 × 200 m window at 1 m in a single request, and every one
was checked against a place whose height is known: Köln 51.2 m, Potsdam 32.6,
Tempelhofer Feld 48.4, Magdeburg 52.1, Hannover 53.1, Schwerin 41.4, Kassel
175.5, Stuttgart 243.0.

**Berlin is its neighbour's service**, which Brandenburg's own licence text says
outright — and which was checked rather than taken on trust. It is the one case
where using another state's endpoint is not borrowing somebody else's ground.

**Sachsen-Anhalt was found on the second pass.** The first search read the
catalogue's Dublin Core view, whose `dc:URI` points at landing pages; the ISO
view has `gmd:linkage`, which is the endpoint. It also needed two format
capabilities nothing else had asked for — see below.

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

## Two more formats, both from one state

Sachsen-Anhalt answers `multipart/related` rather than a bare GeoTIFF — legal
WCS 2.0 that no other service in the registry uses — and packages the image as
**tiles** rather than strips. Both had to be implemented:

- Multipart is unwrapped by finding the TIFF magic rather than by parsing MIME
  headers, because boundaries and header casing vary between servers while
  `II*\0` and `MM\0*` do not.
- A tile grid pads its last column and row out to whole tiles. Dropping that
  padding rather than shifting it in is the whole of the work, and getting it
  wrong skews every row after the first tile boundary — which looks entirely
  plausible on a hillside.

Tiling is also what makes a Cloud-Optimised GeoTIFF, which the BKG's own
documentation says these products may be delivered as. This is the format to
expect more of, not less.

## The eight that are not here, each for its own reason

"Not found" and "does not exist" are different claims, and only the first is
being made.

| State | Status |
|---|---|
| **Bayern** | DGM1 is open (CC-BY-4.0) and downloadable; the coverage service answers **401** — credentials from the LDBV's customer service |
| **Saarland** | Works, and forbids this use: embedding it in another application is *kostenpflichtig*. Its coverage is 5 m, not 1 |
| **Thüringen** | The geoproxy answers *"No service with identifier 'WCS_DGM' available"*; its WMS serves DGM2 and DGM5 — pictures, not heights |
| **Sachsen** | 403 on every path tried, and no terrain WCS record in the GDI-DE catalogue |
| **Schleswig-Holstein** | Download portal and a WMS; no coverage service found |
| **Hamburg** | `HH_WMS_DGM1` exists; no coverage service found |
| **Bremen**, **Rheinland-Pfalz** | No coverage service found, in the catalogue or by probing |

The federal `sgx.geodatenzentrum.de/wcs_dgm1` answers `NOACCESS_SERVICE` from a
security gate — exactly as the BKG orthophoto endpoint did in Wave 8.

**A gap stays a gap.** `by_state` returns `None`, the garden keeps the flat
assumption, and feature 6 says so on the page. No neighbour's ground, no coarser
federal substitute quietly swapped in.

## Why there is no coarse fallback, measured

The obvious next move is a second tier: where there is no 1 m service, use
something coarser. It was tried and rejected, and the reason is worth keeping
because it will be proposed again.

**The question splits by scale.** Terrain does two jobs here and they do not
want the same resolution:

| Job | Needs | Can a coarse model do it? |
|---|---|---|
| Ground under each grid cell, the base under a building, a bed's slope | metres, across 200 m | **No.** A 25 m cell is wider than most gardens; a 200 m cell is four hectares |
| The horizon ring | ~20 m, across 5 km | **In principle yes** — the ring downsamples to 20 m anyway |

So a fallback could only ever serve the far field. That narrows it to one
question: is a coarse horizon better than no horizon?

**The federal DGM200 says no.** It is genuinely open — GeoNutzV, "es gelten
keine Zugriffsbeschränkungen", anonymous, the whole country, and it answers.
Measured against the same ring built from 20 m data:

| | 20 m | 200 m |
|---|---|---|
| Wolfach, Schwarzwald — highest | 12.54° | **15.67°** |
| Wolfach — southern sector | 12.54° | 14.26° |
| Potsdam — highest | 4.80° | **7.00°** |
| Mean difference | — | 1.37° to 2.64° |
| Worst difference | — | 8.07° |

It reads systematically **too high**, because a 200 m cell holds one value that
the ray then meets at the cell's near edge as well as its far one. And the
direction of the error is the damaging one: Potsdam's real 4.80° sits below the
5° the model already stops counting at and therefore changes nothing, while
7.00° does not. A coarse fallback would invent a horizon for exactly the flat
country whose honest answer is that it has none.

**And the gap is mostly a delivery gap, not a data gap.** Rheinland-Pfalz,
Schleswig-Holstein, Hamburg, Bremen and Bayern all publish **DGM1** as open
data — behind a download rather than a bbox service. Rheinland-Pfalz also
publishes a DGM25 (dl-de/by-2-0), but at ± 1.25 m to 5 m of height accuracy and
as a 1 GB ASCII download or an ATOM feed, so it is neither more accurate nor
more convenient than the 1 m data next to it.

So the second tier that would actually help is **a different delivery of the
same resolution**, not a coarser model: fetch a 1 km tile, distil it, cache it,
discard the rest — which is the machinery Wave 19 already plans for LoD2. Worth
doing there, once, rather than twice.

**Copernicus GLO-30** was checked too: reachable on AWS without authentication,
range requests supported, and this project's TIFF reader now handles the tiled
layout a COG uses. It is a *surface* model, which for a far-field horizon is
arguably a feature — but the Copernicus 30 m view service became restricted to
authorised user categories on 28 July 2026, so its licence position is no longer
settled, and this project does not build on unsettled licences.

Eight states is roughly **64 % of the population**. Worth being precise about
rather than rounding up — and the four smallest gaps were probed less thoroughly
than the rest, so this is a floor rather than a finding.

## Tests

`tests/test_terrain_sources.py` asserts the rules rather than the contents: every
entry names a licence and a credit, no entry is chargeable, axes and projection
are one of the known values, no state appears twice, a missing state returns
`None`, and the coarse vertical step is recorded rather than rounded away.

Verified by putting Saarland back in — the licence test fails, with the offending
text in the message.
