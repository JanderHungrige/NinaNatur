---
id: 116-no-hull
title: No Hull — the Shadow Drawn Is the Shadow Counted
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-26
wave_status: active
depends_on: [38-polygon-shadows, 65-the-shade-switch, 99-paper-bleed-and-a-real-shadow, 115-the-measuring-instrument]
relates: [64-light-across-the-bed]
source_files:
  - ninanatur/solar/sweep.py
  - ninanatur/solar/shading.py
  - ninanatur/solar/field.py
  - ninanatur/solar/day.py
  - ninanatur/solar/drawing.py
  - ninanatur/solar/reach.py
  - ninanatur/api/light.py
  - ninanatur/api/ratelimit.py
  - ninanatur/api/schemas_light.py
  - frontend/src/canvas/sweep.ts
  - frontend/src/canvas/sketch.ts
  - frontend/src/themes/draft-sketch/draw.tsx
  - frontend/src/components/SceneWorld.tsx
  - frontend/src/styles.css
  - pyproject.toml
  - requirements.txt
  - requirements-dev.txt
  - scripts/compile_dev_lock.py
routes:
  - GET /api/v1/gardens/{token}/shadows
models: []
test_files:
  - tests/test_drawn_shadow.py
  - tests/test_polygon_shadows.py
  - tests/test_light_api.py
  - frontend/src/canvas/sketch.test.ts
  - frontend/src/themes/draftSketchVocabulary.test.tsx
  - frontend/src/components/CanvasScene.shadows.test.tsx
  - tests/test_busy_slots.py
data_flow: reads-existing
last_synced: 2026-09-22
status: complete
phase: all
mdd_version: 11
tags: [shadows, geometry, concave, convex-hull, day-playback, draft-sketch, shapely]
path: Solar/Shadows/Drawn
integration_contracts:
  - from: 38-polygon-shadows
    function: shadow_hull(obstacle, sun)
    when: a point test wants a cheap first rejection
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The exact shadow costs about ten times the hull for concave outlines, and grows with their corners: ten 500-corner star-shaped houses, the API's limit, take 7 s for a day. Gated by a heavy slot and a per-visitor bucket, not bounded."
  - "The API accepts an outline that crosses itself (so does dragging a corner in the plan); it is repaired for the shadow, and the browser's drop shadow keeps the hull for it. Refusing such outlines at the API is not this feature's."
sister_projects: []
---

# 116 — No Hull: the Shadow Drawn Is the Shadow Counted

## Where it stood

Wave 26's plan measured the error on 2026-09-07. For a concave outline the
shadow was the convex hull of the footprint and its swept copy, so the open
corner of an L-shaped house read **0.00 h** where it gets **3.98 h**.

The review of 2026-09-22 fixed the **count** (doc 38). `is_shaded` and the
grid's `ShadowAt` now ask the exact question inside the hull: does the ray
towards the sun meet the footprint within the shadow's reach? That is the
plan's "ray against the walls", in the frame where the shadow runs along −y.
Doc 115's ray instrument confirms it over random L, U, T and star-shaped
outlines.

Two things kept drawing the hull, so the plan showed a shadow the sun map did
not count:

- **the day playback** (`solar/day.py`, doc 65), whose frames were each
  obstacle's hull;
- **Draft Sketch's drop shadow** (`canvas/sketch.ts::sweep`, doc 99), the hull
  of the outline and its offset copy.

This feature makes both exact. The model and the drawing are then one
construction, the way `roof_lines` made the roof one (CLAUDE.md).

## The construction

A footprint swept along the shadow is the union of three kinds of piece: the
footprint, its copy moved by the shadow's offset, and the band each wall sweeps
between the two. Only the walls that face along the shadow are needed. A point
of the footprint travelling with the shadow leaves it through one of those
walls, and that wall's band carries it the rest of the way. For a convex
outline the union is the hull, and the hull is kept: the same points as
before, so rectangles draw exactly as they did.

**A shadow can have a hole.** A house round a courtyard whose opening faces
along the shadow closes that opening with its own swept wall, and the part of
the courtyard the sun still reaches is lit ground inside the shadow.
Measured on a G-shaped outline swept south: one hole. A hull cannot say that.

### The day's frames (server)

`shading.shadow_rings` gives every shadow at a moment as rings: outlines
anticlockwise, holes clockwise. Each obstacle's shadow is worked out alone by
`sweep.shadow_shape`:

- **a convex, simple outline** gets its hull, with no shapely at all;
- **anything else** becomes shapely's union of the footprint, its copy and the
  bands of the walls facing along the shadow.

The page draws each frame as **one path under the non-zero rule**. A hole winds
against its outline and stays open. Two shadows that overlap fill once, so the
ground under two houses' shadows is no darker than under one.

**Not one union for the whole garden.** The first version merged every shadow
of a frame into one shape and drew it even-odd. The review measured that at
10–47× the old cost of `/shadows` (24 houses of OpenStreetMap-like outlines:
63 ms → 1,655 ms). Oriented rings drawn non-zero give the same picture without
merging.

**Robustness** (review, 2026-09-22):

- *GEOS can throw on valid input* ("side location conflict"). A tangled shed
  failed the whole day's shadows with a 500. The union is retried
  snap-rounded, at 1 µm and then 1 mm, and each retry is logged. Snap-rounding
  every union cost 70% more, so it is not the first try.
- *An outline that crosses itself* — a dragged corner can leave one, and the
  API accepts it — is repaired into the shapes it encloses (`make_valid`), and
  each is swept, the way the model's crossing parity counts it. It is never
  dropped as having no area.
- *A wall drawn as a line* has a spur at the inside of every corner: its band
  runs past the corner and straight back. `reach.is_convex` read the spur as no
  turn, so every turning wall counted as convex, and its hull shaded the corner
  it turns round, in the model too. A doubling-back edge now makes an outline
  concave. The model's exact reach already handled the spur.
- *Slivers*: where two pieces meet in floating point, the union can leave a
  ring of three points and no area. Rings under 1 cm² are dropped.

`ShadowFrame.polygons` keeps its type (a list of rings of points). What it
holds changes: oriented rings, where it used to be one hull per obstacle.

**Cost**, `GET /shadows` for June (30 frames), median of 5, hull → exact:

| Garden | Before | After |
|---|---|---|
| 40 rectangles | 18 ms | 20 ms |
| 24 L-shaped houses | 14 ms | 108 ms |
| 24 houses, 24-corner outlines | 35 ms | 282 ms |
| 24, mixed | 20 ms | 136 ms |
| 10 houses, 500-corner stars (the API's limit) | 370 ms | 6.96 s |

So the route became a heavy one: it takes one of the two computation slots
(`ratelimit.heavy_slot`) and has its own per-visitor bucket, `shadows`,
60 in 10 minutes, like the month view.

### The drop shadow (Draft Sketch)

It is drawn in the browser from the outline being drawn, so a dragged house
drags its shadow (doc 99). `canvas/sweep.ts` builds the pieces — the
footprint, its copy and every wall's band, each turned anticlockwise — and the
mark is one path of all of them under the non-zero rule. Pieces turned the same
way add up and never cancel, so the path fills exactly their union with one
fill and no seams. The mark has no stroke, so the pieces' inner edges never
show.

Before the pieces are built, the outline loses its spurs, as the server's
convexity test now reads them. An outline that still crosses itself keeps the
hull: its lobes wind opposite ways, and one would cancel a band under the
non-zero rule.

## Shapely

The union comes from shapely (BSD-3, GEOS inside, wheels for both of the
image's architectures, checked by `docker build` on 2026-09-22) and not from a
boolean routine written here. It is a runtime dependency in `pyproject.toml`
and `requirements.txt`; `types-shapely` is in the dev lock. Features 5 and 6
will need the same union for roofs cast plane by plane and for crowns.

## The hull that stays

`shadow_polygon` is renamed `shadow_hull`, for what it now is: a cheap
superset. Only the point tests use it, for the box and the first rejection
(the plan: "the bounding-box prefilter stays"). Nothing draws it.

## Business rules

1. What the plan draws as shadow is what the light model counts as shadow, for
   every outline, concave included. In the browser, an outline that crosses
   itself is the one exception: it keeps the hull.
2. A convex outline's shadow is drawn exactly as before.
3. A frame is one path: overlapping shadows do not darken, and a hole in a
   shadow is drawn open.
4. The hull is a prefilter and never a drawing.
5. A day of exact shadows is a computation: a heavy slot and a rate limit.

## Security

No new input. The frames are computed from a garden the token already names.
The work grows with the obstacles' corners (above), so the route takes a heavy
slot and is rate-limited per visitor (`tests/test_busy_slots.py`).
