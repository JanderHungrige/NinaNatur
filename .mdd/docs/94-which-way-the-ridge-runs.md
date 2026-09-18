---
id: 94-which-way-the-ridge-runs
title: Which Way the Ridge Runs
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-21
wave_status: complete
depends_on: [82-the-roof-it-actually-has, 93-where-the-roof-came-from]
relates: [83-measured-surveyed-or-assumed, 93-where-the-roof-came-from]
source_files:
  - ninanatur/geo/roof_faces.py
  - ninanatur/geo/lod2.py
  - ninanatur/garden/measured.py
  - ninanatur/garden/roofshape.py
  - ninanatur/garden/lightcells.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/garden/models.py
  - ninanatur/garden/elements.py
  - ninanatur/garden/element_edits.py
  - ninanatur/api/elements.py
  - ninanatur/api/schemas.py
  - ninanatur/api/gardens.py
  - ninanatur/ingest/migrations.py
  - ninanatur/ingest/schema_user.py
  - frontend/src/roofs.ts
  - frontend/src/garden/selection.ts
  - frontend/src/components/ElementForm.tsx
  - frontend/src/api/types.ts
  - frontend/src/testing/gardens.ts
  - frontend/src/testing/elementForm.tsx
routes:
  - POST /api/v1/gardens/{token}/light
  - PATCH /api/v1/gardens/{token}/obstacles/{obstacle_id}
  - GET /api/v1/gardens/{token}
models: [element]
test_files:
  - tests/test_roof_faces.py
  - tests/test_roof_direction.py
  - frontend/src/roofs.test.ts
  - frontend/src/components/ElementForm.roof.test.tsx
  - frontend/src/garden/selection.test.ts
data_flow: .mdd/audits/flow-which-way-the-ridge-runs-2026-09-18.md
last_synced: 2026-09-18
status: complete
phase: all
mdd_version: 11
tags: [roofs, ridge, pitch, lod2, citygml, light, surveyed]
path: Map/Buildings
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# 94 — Which Way the Ridge Runs

## Purpose

Feature 2 of Wave 21. The roof model stands the pitches of a gable on either
side of a ridge, and until now the ridge was assumed to run along the long side
of the footprint. Measured against the survey, that turns the ridge by 90° on
two thirds of city gables — and a roof whose pitches are said to face north and
south that in fact face east and west is the one number on the plan that is
confidently wrong. The survey carries the answer in the roof faces it is already
downloading. This reads it, keeps it, and lets the page say it.

## What the survey says (measured 2026-09-18)

Three cached NRW tiles, two in Köln and one in Wuppertal:

| Roof | Parts | The faces give a direction | The long-axis ridge is turned ≥ 45° |
|---|---|---|---|
| gable | 1,725 | 1,717 by the highest edge, 1,699 of them agreeing with the faces | 1,114 (65 %) |
| hip | 46 | 44 by the highest edge; the faces alone give 12 | 0 of the 12 |
| pent | 1,551 | 948 (61 %) by the faces | — (modelled flat today) |

With the surveyed ridge, the pitch derived from eaves, ridge height and the span
across the ridge matches the pitch of the surveyed faces to a median of 0.1°;
with the assumed ridge, 6.9° — 13.1° on the turned ones.

## Architecture

```
LoD2 RoofSurface polygons ──► roof_faces.fall_of(roof, faces) ──► Lod2Building.fall_deg (grid)
                                                                     │  lod2.in_garden_frame
                                                                     ▼  (true north, the garden's axes)
                             measured._write_roof ──► element.roof_fall_deg
                                                          │
            roofshape.surface_of(…, fall_deg) ◄───────────┤──► lightcells (the sun on the roof)
                                                          │
                     ObstacleOut.roof_fall_deg, roof_pitch_deg ──► ElementForm
```

## Data Model

`element.roof_fall_deg REAL` — add-only, null on every existing row until the
next recompute measures it.

**One column, one meaning: the compass bearing the roof falls towards,**
degrees clockwise from true north on the garden's axes. A pent falls one way, so
its value is anywhere in [0°, 360°). A gable or hip falls both ways from its
ridge, so its value is the one of the two in [0°, 180°) — and its ridge runs at
right angles to it. Null is "not surveyed": the model then assumes the ridge
runs along the long side and leaves a pent flat, as before.

Downhill, which is the natural reading of *fall*. The project's slope aspects
are uphill (`RoofSurface.slope_aspect_at`); the two meet in `roofshape`, and
nowhere else.

## Reading the faces (`geo/roof_faces.py`)

- **Gable and hip — the highest edge.** The roof's vertices within 0.3 m of its
  highest point; the two farthest apart are the ridge's ends, if they are at
  least 1 m apart. A pyramid has a point for a top and no direction. On a gable
  the faces must agree: the area-weighted axis of their falls (from each
  polygon's normal, Newell's method, faces under 5° ignored), where it is clear
  (resultant ≥ 0.5), must lie within 10° of the ridge's right angle — otherwise
  neither is trusted. A hip's faces cancel each other out too often to judge by.
- **Pent — the faces.** The area-weighted mean of the pitched faces' falls, where
  the resultant is at least 0.5. Faces falling several ways are not a pent roof
  this model can place.
- **Everything else** (flat, mixed, other) — no direction.

The bearing is read in the tile's UTM grid and turned onto the garden's axes the
way the outline is: both ends of a 10 m step along it go through the same
projection. The grid and true north differ by up to 2° in NRW.

## API Endpoints

- `POST /api/v1/gardens/{token}/light` — the survey now writes `roof_fall_deg`
  with the shape it writes, under feature 1's rule: not over a shape the
  gardener chose.
- `PATCH /api/v1/gardens/{token}/obstacles/{obstacle_id}` — choosing a roof shape
  clears `roof_fall_deg` (the survey's direction described a different roof), and
  so does a new outline (`shape`, `width`, `depth`, `rotation`, `points`). Moving
  an element keeps it. A client cannot send one.
- `ObstacleOut` gains `roof_fall_deg: float | null` and `roof_pitch_deg:
  float | null` — the pitch the model uses, from eaves, ridge height and the span
  across the ridge; null where the roof is modelled unpitched.

## Business Rules

1. **Measured beats assumed.** With a direction, `surface_of` measures the span
   across the surveyed ridge; a hip's ridge is shortened by that span at each
   end, down to a point. Without one, nothing changes.
2. **A pent with a known fall is a pent.** One plane: the ridge height along its
   upper edge, the eaves along the lower, the fall across. Without a fall it
   stays flat, as before.
3. **The light follows.** The roof cells' height and slope come from the
   surface, and `signature_of` includes the direction, so a light map computed
   before it was known says it is stale.
4. **The page says it.** Under the roof shape, after where the shape came
   from, one line: *First Ost–West (amtlich vermessen) · Neigung 38°*, or
   *First entlang der längeren Seite (angenommen) · Neigung 28°*; for a pent
   *Fällt nach Norden (amtlich vermessen) · Neigung 12°*, or *Gefälle unbekannt:
   gerechnet wie ein Flachdach*. The source belongs to the direction; the pitch
   follows from the eaves, whose own note says where they came from. The
   compass is eight-point for a fall and four-point for a ridge. Nothing for a
   flat, mixed or other roof, and the line goes once another shape is chosen.
   Both notes describe the select, so a screen reader hears them after its
   name.

## Dependencies

- 82 — the parser and its faces.
- 93 — the per-value rule the survey writes under, and `roof_source`.

## Security

No new input. The direction is written by the survey only; the PATCH can clear
it and never set it. The faces come from the same parser and size limits as
Wave 20 set (`defusedxml`, `MAX_TILE_BYTES`).

## Built (2026-09-18)

On the real tiles the parser now gives a direction to 952 of 968 gables, 34 of
39 hips and 584 of 962 pents, in the same time as before (0.85 s for a 49 MB
tile). `ElementForm.test.tsx` passed 300 lines with these tests, so the roof's
(docs 93 and 94) moved to `ElementForm.roof.test.tsx`, and the render helper
both use to `src/testing/elementForm.tsx`.

## Verified on the preview (V0.20.193, 2026-09-18)

A garden made south of a detached Wuppertal gable (deleted after). The import
brought it as OSM's gable with 15 m eaves from five storeys and no direction.
The recompute measured it: 17.9 m, a surveyed gable, eaves 13.41 m, falling at
170.2° — a ridge at 80°, as the tile has it — and a pitch of 33.9°. On the light
map as imported, 35 elements wide and in 5 m cells, its north face read 8.8 h
against 10.7 h on the south; with only the gable and the garden drawn, in 0.5 m
cells, 10.7 h against 11.7 h (221 and 211 cells), and the plan's own readout
said *Dach · 10.7 h* and *Dach · 11.8 h* over the two faces. The form said
*Satteldach — amtlich vermessen* and *First Ost–West (amtlich vermessen) ·
Neigung 34°*.

## Known Issues

- On a garden as the map import leaves it — the neighbours and the street
  across 150 m — the light grid's time budget gives 5 m cells, a handful on a
  house's roof: the two faces differ (8.8 h and 10.7 h here), but coarsely.
  That is the grid's budget (doc 64), not the roof.

- The shadow a house throws on the garden is still the `RISE_KEPT` prism, which
  does not depend on the ridge's direction. Casting it from the real planes is
  Wave 26, feature 5.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
