---
id: 46-freehand-paths
title: The Gesture Says Whether It Was a Path
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-11
wave_status: complete
depends_on: [43-shape-tools]
relates: [40-freehand-shapes, 42-element-model]
source_files:
  - frontend/src/canvas/freehand.ts
  - frontend/src/canvas/useFreehandStroke.ts
  - frontend/src/components/ObjectEditor.tsx
  - ninanatur/garden/polyline.py
routes: []
models: [element]
test_files:
  - frontend/src/canvas/freehand.test.ts
  - frontend/src/components/GardenCanvas.freehand.test.tsx
  - tests/test_polyline.py
data_flow: writes-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [freehand, path, polyline, gesture]
path: Canvas/Freehand
integration_contracts:
  - from: 43-shape-tools
    function: the armed tool
    when: a freehand stroke is drawn
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "A path is one metre wide until somebody changes it; there is no way to set the width while drawing."
---

# The gesture says whether it was a path

## What this is

Freehand draws both: a stroke that comes back near where it started is an area,
and one that does not is a path — a line with a width.

## Decisions

### The gesture decides, not a mode

Making the user choose "area or path" before drawing is one more thing to get
right before the pen touches the plan, which is the opposite of what freehand is
for. Wave 10's clean-up already detects a stroke that returns to its start; this
feature does something with that fact instead of only using it to close a ring.

### Wave 10 refused what this feature is about

`tidy` rejects a stroke with no area, and correctly — for an outline. A path is
exactly that stroke. So a straight sweep, which used to earn *"Der Umriss spannt
keine Fläche auf"*, is now a path. The only thing still refused is a stroke too
short to be either.

### A path is a metre wide, and stays editable

One metre is what a garden path usually is. The width is a field in the element
panel afterwards, because a line is two numbers per corner rather than twenty
points around a strip — which is the same reason walls and fences use this shape
and can now turn a corner in one element.

**What is missing, and stated rather than left to be found:** there is no way to
set the width while drawing. A wider path is drawn and then widened.

### The separate freehand button is gone

Freehand was its own mode with its own button in Wave 10. It is one of the five
tools now, beside rectangle, circle, triangle and polygon, which is where
somebody looks for it.

## Verified in the running app

Four gestures, four elements: a dragged rectangle (4 corners), a circle (16), a
triangle (3), and a wavy open stroke that became a **path** — a 32-corner band
around its own 16-point centreline. Clicking the rectangle and choosing
"Wohnhaus" changed its fill from `symbol-plain` to `symbol-building`: the skin
follows the label, which is the wave's demo state.
