---
id: 95-look-before-you-argue
title: Look Before You Argue
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-24
wave_status: complete
depends_on: [58-painted-plan, 41-garden-style]
relates: [58-painted-plan, 41-garden-style, 96-a-theme-is-a-thing]
source_files:
  - frontend/sheet.html
  - frontend/src/sheet/main.tsx
  - frontend/src/sheet/SheetCell.tsx
  - frontend/src/sheet/gardens.ts
  - frontend/src/sheet/build.ts
  - frontend/src/sheet/light.ts
  - frontend/scripts/plan-sheet.mjs
  - frontend/scripts/sheet-pixels.mjs
  - frontend/sheet/baseline.json
  - frontend/package.json
routes: []
models: []
test_files:
  - frontend/src/sheet/gardens.test.ts
  - frontend/src/sheet/SheetCell.test.tsx
data_flow: greenfield
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [contact-sheet, playwright, raster, visual-regression, performance, svg]
path: Canvas/Style
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
---

# 95 — Look Before You Argue

## Purpose

Feature 1 of Wave 24, built first. The plan's look has failed twice on reasons
(doc 58): the Browser pane returns a blank for this SVG, so changes went out
unseen and read as a technical drawing to the one person who looked. Nothing in
the plan's drawing is tested for its pixels. This makes the plan something that
can be looked at and compared: the real `CanvasScene`, three fixture gardens,
three zoom levels and the sun map, rendered by Chromium into one contact sheet
— and a record of every cell's pixels, so that "no visible change" is a check
rather than a claim.

## Architecture

```
npm run plan:sheet [-- --check | --update | --dark | --timing]
        │
        ├─ vite (its own port) serving sheet.html → src/sheet/main.tsx
        │        one cell per load: ?garden=&span=&sun=&w=&h=
        │        <svg class="canvas" viewBox=…><CanvasScene …/></svg>
        │        body[data-ready] after two frames and the fonts
        │
        └─ Playwright Chromium, one page per cell (pattern ids are global to a
           page, so nine plans on one page would borrow each other's grid)
                 screenshot → sheet-out/<mode>/<cell>.png
                 RGBA → SHA-256 (in the page) → compared with sheet/baseline.json
                 all cells → one labelled grid page → sheet-out/<mode>/sheet.png
```

Each cell is its own page load, so `#grid`, `#watercolour` and every
`#symbol-*` exist once per page, exactly as in the app.

## The fixtures (`src/sheet/gardens.ts`)

Synthetic, not imported: OSM-derived footprints carry ODbL obligations, and a
fixture must not change when the map does.

| Garden | What it is | Why |
|---|---|---|
| `small` — Reihenhausgarten | 10 × 20 m behind a house: terrace, lawn, a border and a raised bed in flower, a gravel path, a pond, a shed, a tree and a shrub, hedge, fence, wall, a street, something unnamed | every one of the 16 kinds at least once |
| `farmyard` — Hof | 60 × 40 m: barn, stable and sheds, a gravel yard, meadow, an orchard of eight trees, hedges, four vegetable beds, a pond | size: a plan that is mostly surface |
| `city` — Blockinnenhof | a terraced block: ten houses with ten backyards of lawn, terrace, shed, tree and shrub, fences between them, the street, and the gardener's own yard with beds | density: at least a hundred elements, the performance case |

Beds carry plantings with colours for June, built into clusters by the app's
own `clustersFor`, so the bloom dots are the app's. The sun map is a synthetic
grid of hours (`src/sheet/light.ts`): a formula, not a model run — it is there
to show the layer's two inks over the plan.

## The sheet

Rows are the three gardens; columns are 12 m, 40 m and 120 m across and 40 m
with the sun map on. Cells are 360 × 270 px, the page is Chromium at device
scale 1 in light mode, or dark with `--dark` (`prefers-color-scheme`
emulated). The sheet page labels each cell with its garden and span and prints
nothing else.

## The record of pixels (`sheet/baseline.json`)

Per cell and mode: the SHA-256 of the screenshot's RGBA pixels, computed in the
page from a canvas, not of the PNG file — a new PNG encoder must not read as a
change, and a changed pixel must. Stored with the Chromium version it was taken
with.

- `--update` writes it (only on purpose: an intended change, or a new
  Chromium).
- `--check` renders every cell and compares; it exits non-zero naming each
  changed cell and leaves the new PNGs in `sheet-out/` to be looked at.

The PNGs are not committed. Twenty-four textured cells would add several
megabytes to a public repository every time they were renewed; the record is
a few hundred bytes, and the images are one command away.

## The budget (`--timing`)

The city garden at 40 m, the page loaded with Chromium's CPU slowed four times
(a phone), five loads: from mounting the scene to the second frame after it.
The median is recorded in `baseline.json` with the machine it was measured on,
and it is the budget stage 2 and 3 are held to. One filter chain per layer and
no filter on anything interactive are rules for the themes that come next; this
feature only measures.

## What the record holds

- `cells`: a SHA-256 per cell, Technisch's, in both modes — the pixels a change
  must not move by accident.
- `chromium`: which browser took them, because a new one may move them all.
- `timing`: Technisch's paint for the city at 40 m, CPU ×4 — the guard.
- `budgets`: what another style costs on the same cell, each measured in the
  same run as Technisch so the pair can be compared (doc 99). Draft Sketch:
  73 ms against Technisch's 21, accepted by the owner on 2026-09-20. A budget
  is recorded, never asserted: a stopwatch on a shared machine is not a test.

## Business Rules

1. The sheet renders the app's own components with the app's stylesheet —
   nothing in `src/sheet/` draws.
2. One cell per page load.
3. Every kind appears in the sheet (a test counts them in the fixtures).
4. The record is of pixels, not of files.
5. Nothing here is served in production: `sheet.html` is not a build input.

## Dependencies

- 41, 58 — the look being recorded.

## Security

None at runtime: the harness is a development tool, never built into the
bundle, and it talks to no server. The fixture gardens are synthetic.

## Taken on 2026-09-18

Today's plan, before anything of Wave 24 touched it: 24 cells (twelve per mode)
recorded with Chromium 153.0.8010.12, and a second `--check` straight after
found all 24 as recorded — the render is deterministic. The whole sheet takes
under four seconds. The paint budget: the city block (102 elements) at 40 m,
CPU slowed four times on an Apple M1, a median of **36 ms** over five loads
(46, 33, 36, 37, 35). A cell altered in the record made `--check` exit 1 naming
that cell alone; the production build contains no `sheet.html`.

Looking at it found two things the fixtures needed before the record was taken:
the farmyard's close-up was nothing but gravel, so its centre moved to where the
path, the beds and the paving meet; and the first sun map shaded only north of
buildings, which here is mostly street, so trees, hedges and walls cast shade
too and both of the layer's inks are on the sheet.

## Retaken on 2026-09-21

The owner's check changed every cell, on purpose, and the record was taken again
with `--update` after all 24 were looked at in both themes: Technisch's garden
ground is a flat grass wash instead of a 5 % leaf tint (#10), outlines are
screen pixels, the grid is 3 cm or a pixel and the watercolour wobble is capped
at 7 px (#1), and the sun map and relief are drawn as paths (#11). A `--check`
just before the first of these found all 24 as recorded.

## Known Issues

- In dark mode the sun map's sun ink covers the plan almost entirely (the
  "40 m, Sonne" column). It is the app's own look, recorded as it is; feature 5
  measures the contrast of every wash over paper.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
