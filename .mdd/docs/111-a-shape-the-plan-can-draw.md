---
id: 111-a-shape-the-plan-can-draw
title: A Shape the Plan Can Draw
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [37-object-footprints, 42-element-model, 46-freehand-paths]
relates: [44-vertex-editing, 40-freehand-shapes, 112-drawing-at-any-zoom]
source_files:
  - ninanatur/garden/footprint.py
  - ninanatur/garden/store.py
  - ninanatur/garden/element_edits.py
  - ninanatur/api/geo.py
  - ninanatur/ingest/repairs.py
  - ninanatur/ingest/db.py
  - frontend/src/canvas/freehand.ts
  - frontend/src/garden/useElements.ts
routes:
  - POST /api/v1/gardens/{token}/obstacles
  - PATCH /api/v1/gardens/{token}/obstacles/{obstacle_id}
  - POST /api/v1/gardens/from-map
models: [element]
test_files:
  - tests/test_unbuildable_geometry.py
  - tests/test_footprint.py
  - frontend/src/canvas/freehand.test.ts
  - frontend/src/components/GardenCanvas.corners.test.tsx
data_flow: writes-existing
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [validation, footprint, freehand, paths, migration, repair, owner-check]
path: Garden/Elements/Validation
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Rows the repair removes are logged by id on the server; nothing on the page says a garden lost an element it could never show."
sister_projects: []
---

# 111 — A Shape the Plan Can Draw

## What the owner saw (2026-09-21, #3)

> the free draw always says error: it need at least two points … after using
> freehand once, also for the other elements: *Hindernis hinzufügen
> fehlgeschlagen: 422: a band needs at least two points*

## Why it happened

The server stored an element first and built its footprint only when the
garden was read. `add_obstacle` inserted the row and committed it, and then
`to_out` walked every element to answer the request. One element without a
footprint was enough to make that walk raise. From then on, **every** request
that returns the garden answered 422: adding, editing, deleting, reloading. And
each "failed" add had been committed anyway.

Two routes wrote such rows:

- **A freehand press that stayed inside one centimetre.** A click with a hair
  of jitter, or a small scribble at close zoom, thinned to `[first, last]`, both
  the same point once rounded. `traceFrom` refused fewer than two points, not
  two equal ones, so it sent a line of one point twice.
- **Any reshape of a path.** A vertex drag sends points, a resize sends points
  and a position, and neither sends the band. `update_obstacle` wrote the
  `None` they arrived as, so the path lost its width: *"a line footprint needs a
  positive width, got None"*. This was the commoner route of the two.

## What changed

### The server checks before it writes

`footprint.require_buildable(shape, width, points)` builds the footprint the
row would have, and raises if there is none. An outline also needs three
*different* corners there, which reading does not insist on, because rows
stored before this check must still open.

- `store.add_obstacle` calls it before `insert_element`. A refusal is a clean
  422, and nothing is written. A check after the insert would leave the
  outcome to whether anything commits the connection before it is closed.
- `element_edits.update_obstacle` calls it on the element **as it would be**
  after the merge. A width-only change to a line sends no points, and judging it
  against `None` would refuse a valid resize.
- A reshape keeps a line's or circle's stored width when none is sent.
- `api/geo._add_streets` skips a way whose nodes collapse to one point once
  rounded, and logs it. One lost street, never a half-made garden: the garden
  row is already committed when the streets are added.

### The client does not send what the server would refuse

- `traceFrom` rounds first and judges afterwards: a path needs two different
  points and at least `MIN_DRAG_M` (25 cm) of length, the rule a dragged shape
  already had. Otherwise "Der Strich ist zu kurz — zieh ihn etwas weiter."
- `drawTrace` rounds the centre before taking the corners relative to it, so the
  stored corners are exactly the drawn ones. Rounding twice around an unrounded
  centre could merge two corners a centimetre apart.

### Gardens already broken open again

`ingest/repairs.mend_unbuildable_elements`, a one-time migration marked
`wave_25_unbuildable_elements` in `catalogue_meta` (in its own module because
`one_time.py` is near the line limit), runs at startup after `roof_provenance`:

- A line whose width was cleared gets its kind's usual width back. The path was
  real and somebody drew it; only its band was lost.
- A line without two different points, or an outline without three different
  corners, is **removed**, and each removal is logged by id. Such a row covers
  no ground and could never be seen or selected, and the lines never even
  reached a plan, because no request that stored one ever returned. Removing
  them was chosen over flagging them, because a garden that cannot open is the
  greater loss.

**What the owner should know before looking at a garden that broke.** Every
add, edit and delete that showed the 422 *was* carried out. Once the repair
runs, the shapes and beds tried after the first error appear, possibly twice.

## Business rules

- No write path stores an element without a footprint.
- A partial edit is judged on the merged element, never on the request alone.
- A repair that removes user rows logs what it removed and runs exactly once.
