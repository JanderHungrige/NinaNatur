---
id: 26-drawing-canvas
title: A Surface You Can Draw On
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-7
wave_status: complete
depends_on: []
relates: [27-object-labelling, 14-garden-canvas]
source_files:
  - frontend/src/canvas/viewport.ts
  - frontend/src/canvas/snap.ts
  - frontend/src/canvas/history.ts
  - frontend/src/canvas/geometry.ts
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/CanvasControls.tsx
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/plural.ts
routes: []
models: []
test_files:
  - frontend/src/canvas/viewport.test.ts
  - frontend/src/canvas/snap.test.ts
  - frontend/src/canvas/history.test.ts
  - frontend/src/canvas/geometry.test.ts
  - frontend/src/components/GardenCanvas.test.tsx
  - frontend/src/components/GardenCanvas.drawing.test.tsx
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [canvas, drawing, zoom, grid, snap, undo, svg, accessibility]
path: UI/Canvas
integration_contracts:
  - function: toGarden(point, viewport)
    when: any pointer position becomes a coordinate that is stored
    note: the transform is the only place screen pixels become metres; a second copy of it is a second answer
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 26 — A Surface You Can Draw On

## Purpose

Wave 3 shipped coordinate forms: type x, y, width, depth. Honest for a keyboard
path and wrong as the primary interface — nobody knows their bed is at x=3.5.
They know it is *along the fence, left of the shed*.

This turns the read-only plan into something a pointer can draw on: pan, zoom, a
grid that means metres, snapping, and undo.

## Scope, and what is deliberately left to feature 2

The wave lists "garden outline, beds, buildings, hedges". The data model today
has exactly two things: `bed` (a polygon) and `obstacle` (a circle with a
height). Introducing a general object vocabulary is a schema change and it is
what feature 2 exists for.

So this feature builds **the surface and its mechanics**, and draws the two
shapes the model already stores. Outlines, buildings and hedges arrive with the
vocabulary that gives them meaning, one feature later. Building the surface
against types that do not exist yet would mean guessing twice.

## The mechanics

### A grid that means one metre

At 40 m across, a 1 m grid is 40 lines and useful. At 400 m it is 400 lines and
a grey wash that still claims to be metres. So the grid **thins as it zooms
out** — 1 m lines while they are more than 6 px apart, 5 m lines beyond that,
25 m beyond that — and a **scale bar** states the current spacing in words.

A grid whose spacing silently stops being one metre is worse than no grid: it
looks like a measurement.

### Zoom by wheel and by button

Both, and not as a nicety: a wheel-only zoom locks out anyone without a wheel or
trackpad, and anyone whose hands do not do precise scrolls. The buttons are the
real control; the wheel is the shortcut.

Wheel zoom **anchors on the pointer** — the metre under the cursor stays under
the cursor — because zooming to the centre makes a user chase their own garden
across the screen. It calls `preventDefault` so the page does not scroll, which
means the listener has to be non-passive and bound to the element.

### Snapping

Positions snap to the nearest grid intersection. Holding **Alt** places freely,
and the UI says so rather than leaving it to be discovered.

Snapping happens in **garden metres, after the transform**, not in screen
pixels. Snapping pixels then converting gives a different answer at every zoom
level, and the stored coordinate would depend on how far the user had zoomed in
when they drew it.

### Undo is not optional

A drawing tool without undo is a tool people are afraid to use, and a timid user
draws nothing. Undo covers the vertex being placed as well as the finished
shape: while drawing, it removes the last point; between shapes, it removes the
last shape.

Redo comes with it. An undo that cannot be undone is its own small betrayal.

## Accessibility — decided here, not retrofitted

The wave's Open Research asked how much of the coordinate form survives. The
answer: **all of it.** The forms stay as the keyboard and screen-reader path,
and the canvas is the pointer path for the same operations. This is the rule
from Wave 3 and it holds.

What this feature owes accessibility beyond that:

- Existing beds and obstacles stay focusable and named, as they are today.
- Zoom buttons are real buttons with labels, reachable by tab.
- The canvas announces its current scale, so a user who zoomed with a button
  knows what happened.
- `preventDefault` on wheel is scoped to the canvas element. A page that cannot
  be scrolled is not accessible either.

## Business Rules

- **One transform.** `toGarden` and `toScreen` are inverses in one module. A
  second conversion written inline is a second answer that will disagree.
- **Coordinates are stored in metres**, never in screen or SVG units. What is
  saved must not depend on the window size at the moment of drawing.
- **A polygon needs three distinct points.** Two clicks and a double-click is a
  line, not a bed; it is refused with a reason rather than saved as a degenerate
  shape the area and shading code would then divide by zero on.
- **Zoom is clamped** to a range where the grid can still be honest — roughly
  2 m to 1,000 m across.

## Security

No new input reaches the server: this feature produces the same polygon and
circle payloads the Wave 3 API already validates. Coordinates are numbers and
are bounded by the zoom clamp before they are sent.

## Known Issues

- **A drawn bed gets a placeholder name and the default soil.** Asking mid-gesture
  would interrupt the one motion this feature exists for; the bed form edits it
  after. Feature 2's labelling replaces this properly.
- **No vertex editing yet** — a finished outline can be deleted and redrawn, not
  adjusted. The wave's own Risks section calls polygon editing out as deceptively
  large, and it is not smuggled in here.

## Bugs

**The wheel zoom ate the page's scrolling.** A plain wheel over the canvas
zoomed, so the page could not be scrolled past the plan at all: loading the page
and letting it settle swallowed every tick as a zoom step until the view sat at
its 1,000 m limit, centred somewhere the user never chose. This document says
*"a page that cannot be scrolled is not accessible either"* — I wrote that and
then built against it. Now Ctrl/Cmd + wheel zooms and a plain wheel scrolls,
which is also the gesture browsers already use.

**The canvas never measured itself.** `size` was declared as an override with a
`= DEFAULT_SIZE` default in the same destructuring, so it was never `undefined`
and the `ResizeObserver` guard returned early every time. The surface is
633×292 and the maths assumed 800×600, which is a different metre. Caught by
drawing a square and reading the coordinates back.

**A bow tie was told it needed three corners.** It has four, and zero *net*
area, so the degeneracy check matched before the self-intersection check and
gave a complaint about a shape the user was not drawing. Most specific
complaint first.

**"Beet Beet 1".** The labels prepend "Beet " and the drawing tool names its
beds "Beet 1". Pre-existing — "Beet Neues Beet" had been read out since Wave 4 —
and only obvious once beds got generated names. One helper now, used by both
label sites, so they cannot drift.
