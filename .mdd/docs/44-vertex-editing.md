---
id: 44-vertex-editing
title: Move a Corner, and the Promise Ends
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-11
wave_status: complete
depends_on: [43-shape-tools]
relates: [42-element-model, 46-freehand-paths]
source_files:
  - frontend/src/canvas/vertices.ts
  - frontend/src/canvas/useVertexDrag.ts
  - frontend/src/components/VertexHandles.tsx
  - ninanatur/garden/store.py
  - ninanatur/api/schemas.py
routes: ["/api/v1/gardens/{token}/obstacles/{obstacle_id}"]
models: [element]
test_files:
  - frontend/src/canvas/vertices.test.ts
  - frontend/src/components/GardenCanvas.vertices.test.tsx
  - tests/test_object_editing.py
data_flow: writes-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [vertices, outline, constraint, editing]
path: Canvas/Vertices
integration_contracts:
  - from: 43-shape-tools
    function: selection and a derived box
    when: an element's vertices are edited
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# Move a corner, and the promise ends

## What this is

Every corner of an outline can be dragged, every edge can take a new corner in
the middle, and a double click removes one. The behaviour every flowchart tool
has, and what lets a drawn bed follow a boundary that is not a rectangle.

## Decisions

### Nothing converts, because there was nothing to convert

This is what Wave 11's geometry decision bought. A rectangle is its four points
like every other outline, so dragging one corner is an ordinary edit — no
"convert to polygon?" prompt, no moment where the handles change behaviour under
the user's hand.

What ends is the **promise**: `constraint_hint` goes to null, so the corners
stop being kept square. The shape is untouched.

### Three corners is the floor

Below that an element would still exist and cover nothing. The removal is
refused rather than silently ignored, and the shape stays as it was.

### A line has ends, not a closing edge

An area offers an insertion point on every edge including the one from the last
corner back to the first. A path does not have that edge, and offering one would
put a handle in mid-air between two ends that are not joined.

### One save per gesture

A corner that was clicked and not moved is not an edit. Saving it anyway costs a
PATCH and a recomputation of every bed's light — the same rule the resize
handles follow.

## Two bugs this feature found in the update path

Both were live and neither had a test:

1. **`update_obstacle` dropped explicit nulls.** Its filter said
   `if v is not None`, which is how "leave this alone" was expressed before
   `exclude_unset` did that job upstream. Clearing the rectangle hint is exactly
   an explicit null, so it was not expressible at all.
2. **Its allow-list still named `depth` and `rotation`.** Those stopped being
   columns in feature 42, so a resize — which is precisely what sends a width, a
   depth and an angle — would have been rejected by the column check. The handles
   would have looked broken in the running app.

The update path now converts geometry on the way in: width, depth and an angle
go in, points come out, and anything not named keeps what the element already
has. A move that names only x and y no longer resets the shape to its default.

## Definition of done

Dragging a corner reshapes the element and drops the rectangle hint; clicking an
edge adds a corner; a double click removes one unless three would be left.
