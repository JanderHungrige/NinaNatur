---
id: 39-element-stamps
title: Place a Ready-Made Element and Pull It to Size
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-10
wave_status: in_progress
depends_on: [37-object-footprints]
relates: [26-canvas-drawing, 27-object-labelling, 38-polygon-shadows]
source_files:
  - frontend/src/kinds.ts
  - frontend/src/canvas/handles.ts
  - frontend/src/components/StampPalette.tsx
  - frontend/src/components/ResizeHandles.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/BedPanel.tsx
  - frontend/src/components/ObjectEditor.tsx
  - frontend/src/App.tsx
routes: []
models: []
test_files:
  - frontend/src/canvas/handles.test.ts
  - frontend/src/components/StampPalette.test.tsx
  - frontend/src/components/GardenCanvas.stamps.test.tsx
  - frontend/src/components/BedPanel.test.tsx
  - tests/test_kind_vocabulary.py
data_flow: writes-existing
last_synced: 2026-08-30
status: complete
phase: all
mdd_version: 11
tags: [canvas, palette, resize, rotate, vocabulary, accessibility]
path: Canvas/Stamps
integration_contracts:
  - from: 37-object-footprints
    function: shape/width/depth/rotation on an obstacle
    when: an element is placed or resized
satisfies_contracts:
  - from: 40-freehand-shapes
    function: selection and handles on an obstacle
    when: a freehand outline becomes an object
    status: pending
    verified_at: ""
security_read_sites: []
known_issues:
  - "A circle resizes as a square by design; its depth is stored but ignored."
---

# Place a ready-made element and pull it to size

## What this is

A palette of the thirteen things a garden is made of. Pick one, click the plan,
and it lands at the size that kind usually is. It arrives selected, wearing the
eight handles of draw.io and a ninth that turns it.

## Decisions

### The vocabulary lives in one file, and a test binds it to the server

There were three lists of the same German words — the palette, the canvas
labels, the object editor — and one had already drifted: the editor still
offered **Gebäude**, a kind the server stopped knowing when feature 37 split
houses from sheds. Choosing it wrote a kind nothing downstream understood.

`frontend/src/kinds.ts` is now the only list. `tests/test_kind_vocabulary.py`
fails if it and `objects.py` disagree on which kinds exist, which of them stand
up, or what height each starts at. Two lists in two languages that no compiler
compares need a test that does.

### Handles are measured in metres, drawn in pixels

The arithmetic in `canvas/handles.ts` works in garden metres and in the object's
own frame: pulling the east handle of a house turned 90° must widen it along its
own axis, not along the screen's. A delta measured in pixels would resize
differently at every zoom level — the same mistake grid snapping already avoids.

The grips themselves are the opposite. They are 8 px converted to metres, so a
handle stays the same size on screen at every zoom. A grip fixed at 0.3 m is
invisible on a whole-garden view and swallows the object on a close one; the
user is aiming with a pointer, so the target belongs in the pointer's unit.

### A preview box during the drag, not a live redraw

The real footprint is the server's to compute. Reimplementing `footprint_of` in
TypeScript to animate the drag would be a second copy of geometry that has to
stay in step with the first. The drag shows a dashed outline of the box, and the
object redraws on drop — which is what draw.io does, for the same reason.

One consequence had to be fixed rather than accepted: a pond resized as a
rectangle previewed a rectangle and came back a circle. Round kinds now resize
square (`keepSquare`), so the preview shows something that can actually happen.

### One save per gesture

A PATCH per pointermove would recompute every bed's light dozens of times across
one drag. The new size is sent on pointerup, and only if the pointer actually
moved — clicking a handle is not a resize, and a request that changes nothing
still costs a full light recomputation.

### Placing arms once, then disarms, and selects what it placed

The palette is a stamp, not a mode to escape from: a click that keeps producing
houses is not what anyone expects. And the placed object arrives selected,
because the palette's own hint says *"danach lässt es sich an den Griffen
ziehen"* — without it the user must hunt for and click the thing they are
looking straight at.

## Bugs this feature found in the running app

Two, both in the hand-entry form that predates the palette, and both invisible
until the app was driven rather than tested:

1. **"Art" was a free text field.** The server takes a closed set of kinds, so
   any spelling not in it came back a 422 the user had no way to predict. It is
   a `<select>` over the shared vocabulary now, and choosing a kind fills in its
   size and height.
2. **`step="0.5"` over `min="0.2"` made 6 m an invalid value.** An invalid
   number input blocks form submission with no message anywhere — the button
   simply did nothing. The heights the vocabulary hands out (2.4 m, 1.2 m,
   1.5 m) failed the same check. Every number field is `step="any"`.

A third was caught before it shipped: the stamp buttons' accessible name
concatenated to `"Wohnhaus10 × 8 m"`, one word to anything reading the name
rather than the page. They carry an explicit `aria-label` now.

## Verified in the running app

- A pond placed at the canvas centre lands at garden (0, 0) with a 16-segment
  circle of radius 1.5 — the click-to-metre conversion is right at both ends.
- A hedge placed 4 m west snaps to (−4, 0) at 6 × 0.6 m, arrives selected with
  nine handles, and the palette disarms itself.
- Dragging that hedge's rotation handle due east turns it to 90°: the stored
  footprint runs from y −3 to 3 and x −4.3 to −3.7. North–south, 6 m by 0.6 m.
- Pulling a pond's east handle 120 px grows it from radius 1.5 to 4.04 and
  shifts its centre to 2.54 — half the drag, as keeping the far edge still
  requires.
