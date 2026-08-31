---
id: 43-shape-tools
title: Drag Out a Shape, Any Shape
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-11
wave_status: complete
depends_on: [42-element-model]
relates: [44-vertex-editing, 45-relabel-and-skin, 39-element-stamps]
source_files:
  - frontend/src/canvas/shapes.ts
  - frontend/src/canvas/handles.ts
  - frontend/src/components/ShapeTools.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/ResizeHandles.tsx
routes: []
models: [element]
test_files:
  - frontend/src/canvas/shapes.test.ts
  - frontend/src/components/GardenCanvas.shapes.test.tsx
data_flow: writes-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [canvas, shapes, drag, handles, discoverability]
path: Canvas/Shapes
integration_contracts:
  - from: 42-element-model
    function: element geometry as points
    when: a shape is drawn or resized
satisfies_contracts:
  - from: 44-vertex-editing
    function: selection and a derived box
    when: an element's vertices are edited
    status: done
    verified_at: "frontend/src/canvas/useShapeBand.ts:37"
security_read_sites: []
known_issues: []
---

# Drag out a shape, any shape

## What this is

Rectangle, circle, triangle, polygon — dragged out at the size you want, not
stamped at a size somebody chose. Then moved, resized and turned.

## Why the stamps were not enough

Wave 10's palette placed a house at 10 × 8 m and a pond at 3 m. The feedback:
*"Die Elemente sind fixed in size. This is just a small selection."* Both halves
of that are right, and they have different causes.

**Fixed in size** was not true, and that is the more interesting failure: the
resize handles existed and worked. They are 8 px, grey, and appear only after a
click. A feature nobody finds is a feature that is not there, so this one treats
being findable as part of the work rather than as polish.

**A small selection** was true, and no palette fixes it. A garden is not made of
thirteen shapes. It is made of whatever outline the ground actually has.

## Decisions

### Drag to draw, in the shape's own terms

Press, drag, release. The rectangle spans the drag; the circle takes it as a
diameter; the triangle sits in it. Nothing is created below a quarter of a metre
across, because that is a mis-click rather than a request for a tiny shape.

### Everything becomes points on the way in

The client sends points, and the server stores them. A rectangle carries the
`rect` hint so its corners keep their right angles under a handle; a circle is
the one shape that stays a centre and a radius.

### A new shape has no kind yet

It arrives as `other` with no height, which casts no shadow. That is the whole
order the user asked for — draw first, say what it is afterwards — and it means
a half-finished plan never claims a shading effect nobody described.

### Handles you can find

Twelve pixels rather than eight, filled in the accent colour rather than the
surface colour, and a cursor per handle so the pointer says what will happen
before the drag starts. The shape under the pointer shows its outline on hover,
so it is discoverable without a click.

## Definition of done

Dragging with each tool produces an element of that shape at the dragged size;
the handles resize and rotate it; and a mis-click produces nothing.
