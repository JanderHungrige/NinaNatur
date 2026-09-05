---
id: 69-a-window-of-ground
title: A Window of Ground
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-17
wave_status: active
depends_on: [68-which-ground-and-whose]
relates: [68-which-ground-and-whose, 63-neighbours-from-the-plot]
source_files:
  - ninanatur/geo/terrain.py
  - ninanatur/geo/terrain_store.py
  - ninanatur/geo/tiff.py
  - ninanatur/geo/utm.py
  - ninanatur/ingest/http.py
  - ninanatur/ingest/schema_user.py
routes: []
models: [terrain_window]
test_files:
  - tests/test_terrain.py
  - tests/test_tiff.py
  - tests/test_utm.py
data_flow: mixed
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [terrain, geotiff, lzw, utm, projection, cache, provenance]
path: Map/Terrain
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "A stored window is 39 KB for Cologne, against the 24 KB the wave plan projected from smoother ground near Potsdam."
  - "Predictors 1, 2 and 3 are supported; anything else raises rather than guessing."
---

# A Window of Ground

Feature 1 of Wave 17. The national DGM1 is a terabyte; a garden needs 200 m of
it. This fetches that, once per location, and keeps 39 KB.

## What it does

`terrain_for(anchor)` finds the state, looks it up in the registry, asks the
service for a 210 m box around the garden, and returns heights on the **garden's
own axes** — not the service's.

Two hundred metres because the obstacle model reaches fifty metres beyond the
plot boundary, so that covers every building the shading already knows about
with ground to spare for measuring a slope in. Ten metres more are requested
than kept, because of the rotation below.

## The rotation is the reason this is not a paste

UTM's grid north is not true north. The meridian convergence between them
reaches **2.3° at 6°E** — Aachen, Cologne, the whole western Rhineland — and the
garden is drawn on true-north axes. Pasting the raster in unchanged would turn a
south-facing slope into one facing 2° off south, and rotate every hill in the
horizon ring by two of its one-degree bins.

So every window is resampled. Over 200 m the map between the two frames is a
rotation, a scale and a shift to well under a millimetre, so it is measured from
three points — the origin, 100 m east, 100 m north — rather than recomputed per
cell.

`tests/test_terrain.py` asserts it with geometry rather than arithmetic: ground
that rises purely along the UTM northing must come back rising 2.3° off true
north, in the direction the convergence actually points.

The projection itself is fifty lines of Krüger series rather than `pyproj`,
which is a compiled wheel per platform for the same two formulas. Checked
against control points: longitude 9° returns easting 500000.000 exactly, and
Köln Dom lands on 356560 / 5645282.

## Three formats, and none of them optional

The six services in the registry disagree in three dimensions at once, and every
disagreement was found by decoding a real response rather than by reading a
specification:

| | Byte order | Samples | Compression | Predictor |
|---|---|---|---|---|
| Brandenburg, M-V, Hessen | little | float32 | none | — |
| Nordrhein-Westfalen | little | float32 | LZW | none |
| **Niedersachsen** | little | float32 | LZW | **3 — floating point** |
| **Baden-Württemberg** | **big** | **uint16** | none | — |

`ninanatur/geo/tiff.py` is the fraction of TIFF 6.0 those six emit, and it
refuses the rest loudly rather than guessing.

**Three things silently produced garbage before they were fixed:**

- **Brandenburg stores the strip offsets as LONG and the strip byte counts as
  SHORT in the same file.** Reading both as LONG gave plausible-looking lengths
  and nine times too many values.
- **Niedersachsen uses predictor 3**, the floating-point predictor, which is not
  a variant of horizontal differencing but a different reconstruction: byte
  planes are separated, then differenced. Without it the raster decoded to a
  median of 0.00 m and a range of 3.4 × 10³⁸ — and the first sanity check
  *passed it*, because a median of zero sits inside a tolerance built around
  Hannover's 55 m. The check was tightened to require a plausible **range** as
  well as a plausible middle.
- **Baden-Württemberg is big-endian**, and a big-endian TIFF stores a SHORT
  inline left-justified in the four-byte field. Reading the value before the
  type made a 200 × 200 raster look like 13 million pixels.

All six now decode to the right heights: Köln 51.2 m, Potsdam 32.6, Hannover
53.1, Schwerin 41.4, Kassel 175.5, Stuttgart 243.0.

## Stored small, and once

Keyed by location rounded to 100 m, not by garden: terrain does not change and
two gardens in one street stand on the same ground.

Heights are centimetres above the window's own minimum, as a deflated block of
16-bit integers. **The first version stored JSON and came to 202 KB — larger
than the GeoTIFF it was made from.** As a blob the same window is 39 KB.

Unsurveyed ground is `NO_HEIGHT = -32768` and comes back as `None`, never as the
base height: border tiles and water genuinely have none, and a zero there is a
cliff rather than an absence.

Provenance travels with the window — source, licence, attribution, and
`vertical_step_m`, which is 0.01 for a DGM1 and **1.0 for Baden-Württemberg**, so
feature 6 can say so rather than imply precision that was not given.

## One thing changed outside this feature

`mypy` was configured for `python_version = "3.11"`. numpy's own type stubs use
PEP 695 `type` statements, which mypy refuses to parse when told to target 3.11
— so the first module here to import numpy turned the whole strict check red.
The image runs 3.13 and CI runs 3.13; the floor was checking a version nothing
deploys on. Moved to 3.12, and `requires-python` with it.

## Tests

No network in any of them. `tests/test_tiff.py` builds each format byte by byte,
including an LZW encoder written from the specification so the decoder is checked
against an independent reading of the same rule rather than against itself. Both
the strip-type bug and the predictor-3 bug were put back afterwards to confirm
that their own test — and only their own test — fails.
