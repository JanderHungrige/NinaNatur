---
id: 73-which-way-does-it-fall
title: Which Way Does It Fall
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-17
wave_status: active
depends_on: [69-a-window-of-ground]
relates: [72-the-hill-that-eats-the-morning]
source_files:
  - ninanatur/garden/slopes.py
  - ninanatur/garden/lighting.py
  - ninanatur/ingest/schema_user.py
  - ninanatur/ingest/migrations.py
  - frontend/src/slopes.ts
  - frontend/src/components/BedPanel.tsx
routes:
  - GET /api/v1/gardens/{token}
models: [element]
test_files:
  - tests/test_slopes.py
  - frontend/src/slopes.test.ts
  - frontend/src/components/BedPanel.test.tsx
data_flow: writes-existing
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [slope, aspect, terrain, ellenberg, wording]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The slope is the plane through the bed's centroid. A bed spanning a break of slope reports the middle of it."
---

# Which Way Does It Fall

Feature 5 of Wave 17. *"6.4 h/Tag · L 8 · Südhang, 16 %"*.

## Named, never scored

This was a planning decision and Wave 17 turned it into a measured one.

A 17° slope at 52°N moves the sun **hours** by about a fifth of an hour. The
noon sun runs from 38° at the equinox to 61° at midsummer and clears a 17°
skyline easily; the low sun a slope does block is largely below the 5° the model
already stops counting at. Measured: 12.58 h flat, 12.38 falling to the south,
12.50 rising to the south.

What a north-facing bank actually loses is **energy per square metre** — the sun
strikes it obliquely — and this model does not compute that. So folding the
slope into the light score would move a number that should barely move, in the
wrong direction, for the wrong reason.

Instead it is said, in front of the figure it qualifies, so a gardener reads
*"5.2 h/Tag · L 6 · Nordhang, 30 %"* and knows both things. Nobody should read
"12.5 h" on a north bank as "as good as flat", and the number alone would let
them.

## Three states, not two

| Stored | Shown | Means |
|---|---|---|
| `null` | nothing at all | nobody has fetched the ground |
| `0` | nothing at all | measured, and level |
| `9`, `180` | *Südhang, 16 %* | measured, and a slope |

The first two look the same on the page and are different in the database, and
the difference matters: saying *"eben"* about a garden nobody has looked at is
the same false confidence the flat model had all along. So the word is withheld
rather than guessed, and the migration defaults both columns to `NULL` on every
existing bed.

## The units are the gardener's

Degrees go into the database; per cent comes out on the page. A ramp, a path and
a drainage fall are all measured in per cent, and nobody standing in their garden
thinks in bearings — so the compass point becomes a word: *Südhang*, *Nordosthang*.

Rounded to a whole degree of slope and five of direction. The DGM1 states
± 0.3 m; a tenth of a degree of aspect out of that would be arithmetic rather
than information.

Below **2°** nothing is said at all, for the same reason: across the few metres a
slope is measured over, ± 0.3 m is more than a degree, so a gentler reading is
the error bar rather than a gentle slope.

## One bug the type checker caught

`slopeName` indexed an eight-entry table with `Math.round(bearing / 45)`, which
is 8 for anything above 337.5° — one past the end, before the modulo brings it
home. `noUncheckedIndexedAccess` refused it, and it was right to: the test for
359.9° was written afterwards and would have failed.
