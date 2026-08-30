---
id: 40-freehand-shapes
title: The Tool Cleans Up After the Hand
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-10
wave_status: in_progress
depends_on: [39-element-stamps]
relates: [26-canvas-drawing, 37-object-footprints]
source_files:
  - frontend/src/canvas/freehand.ts
  - frontend/src/canvas/geometry.ts
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/CanvasControls.tsx
routes: []
models: []
test_files:
  - frontend/src/canvas/freehand.test.ts
  - frontend/src/components/GardenCanvas.freehand.test.tsx
data_flow: writes-existing
last_synced: 2026-08-30
status: complete
phase: all
mdd_version: 11
tags: [freehand, rdp, simplification, self-intersection, canvas]
path: Canvas/Freehand
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Untangling re-orders corners by angle, which is a heuristic; a pathological stroke falls back to the convex hull."
---

# The tool cleans up after the hand

## What this is

Drag the outline in one go. Three hundred jittered points become a shape with a
handful of corners, an outline left slightly open is closed, and a stroke that
crossed itself is untangled. *Sonst muss der user zu genau arbeiten* — a drawing
tool that demands precision is a form with extra steps.

## Decisions

### Tolerances in metres, with a floor

Ramer–Douglas–Peucker thins the stream. Its tolerance is two pixels converted
to metres, so "close enough" is the same distance on screen at every zoom — a
tolerance fixed in pixels would erase corners when zoomed out and keep tremor
when zoomed in.

But it also has a **floor of 10 cm**. Without one, a scribble drawn while zoomed
right in stores a corner every few millimetres: detail no gardener plants to,
carried afterwards by every light computation the bed is part of. The floor is
the same centimetre the outline is rounded to.

Measured on the running app: a clean 331-point loop becomes 17 corners.

### Closing means dropping the stray end

Not appending the first point. A polygon is closed by being a polygon, and a
duplicated first corner is a zero-length edge for everything downstream to trip
over. Three points that happen to end near the start are left alone — a triangle
minus one corner is not a shape.

### Untangling is not a convex hull

A hull is the obvious way to make a self-crossing outline simple, and it is
wrong: an L-shaped bed is an ordinary thing to draw, and a hull fills in its
notch. So a stroke that does not cross itself is returned untouched, concavity
and all.

When it does cross, the corners are re-ordered by their angle around the middle
of the shape. That resolves the scribble people actually make — a stroke that
doubles back over itself — through the same corners the user drew, and it cannot
fail to terminate. The hull remains only as a last resort for a stroke that is
still tangled after sorting: something drawn beats a refusal the user cannot act
on.

A stroke with fewer than three corners, or with no area, is refused outright and
says why. Inventing the missing corner would put a bed on the plan nobody drew.

### The stroke lives in a ref

The points are accumulated in a ref and mirrored into state for drawing. Pointer
events can arrive faster than React re-renders, and reading the stroke out of a
render closure on pointerup would silently drop whatever came in after the last
paint — a bug that would show up as a bed slightly the wrong shape, which is
exactly the kind nobody reports.

### Drawing is not panning

Dragging pans the plan everywhere else. In freehand mode the same gesture draws,
and letting it do both would slide the garden out from under the line. Freehand
also disarms after one shape, so a later drag pans again rather than producing
a second bed.

## Verified in the running app

- 331 pointer samples around a wobbly loop that overshoots its own start — so it
  is both self-crossing and open — become a stored bed.
- The same loop without synthetic jitter becomes 17 corners. The higher count
  from the jittered version is the sawtooth in the test input, which alternates
  every sample; a hand's tremor is correlated between samples and thins away.
- Coordinates come out in metres: the outline scales with the garden, not with
  the window.
