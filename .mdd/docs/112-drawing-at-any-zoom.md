---
id: 112-drawing-at-any-zoom
title: Drawing at Any Zoom
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: complete
depends_on: [26-drawing-canvas, 50-polygon-closing, 96-a-theme-is-a-thing, 97-draft-sketch-in-svg]
relates: [111-a-shape-the-plan-can-draw, 113-a-plan-that-keeps-up, 31-map-selection]
source_files:
  - frontend/src/canvas/snap.ts
  - frontend/src/canvas/useCanvasGestures.ts
  - frontend/src/canvas/useDrawingModes.ts
  - frontend/src/canvas/useViewport.ts
  - frontend/src/map/useMapSurface.ts
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/components/CanvasControls.tsx
  - frontend/src/styles.css
  - frontend/src/themes/types.ts
  - frontend/src/themes/technisch/symbols.tsx
  - frontend/src/themes/draft-sketch/paths.ts
  - frontend/src/themes/draft-sketch/ours/Roads.tsx
  - frontend/src/workspace/shortcuts.ts
routes: []
models: []
test_files:
  - frontend/src/components/GardenCanvas.corners.test.tsx
  - frontend/src/components/GardenCanvas.wheel.test.tsx
  - frontend/src/components/MapPicker.wheel.test.tsx
  - frontend/src/canvas/snap.test.ts
  - frontend/src/themes/draft-sketch/paths.test.ts
  - tests/test_plan_stylesheet.py
data_flow: greenfield
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [canvas, zoom, wheel, snap, stroke-width, non-scaling-stroke, draft-sketch, technisch, owner-check]
path: Canvas/Drawing/Zoom
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Pattern textures — a lawn's blades, his grass tufts — are drawn in metres and grow with the zoom, by design: a close-up of a lawn shows big blades. Only outlines and ink are held to pixels."
  - "The grid is still pale and under the ground's wash. The snap reach is kept small (6 px) because of it; a visible snap cue was not built."
sister_projects: []
---

# 112 — Drawing at Any Zoom

Three items of the owner's check (2026-09-21) are one problem: the plan measured
in metres things that are about the screen.

## #1 — "the line thickness is too thick … we might want to draw more detailed"

Every outline had a width in metres. At the closest view (2 m across) that was
40 px in Technisch and 50–75 px of Draft Sketch's ink.

- **Technisch** (`styles.css`): `.bed`, `.obstacle` 1 px, `.bed--selected` 2 px,
  the garden's dashed edge 1.5 px, the draft line 1.5 px, all under
  `vector-effect: non-scaling-stroke`. The high-contrast outline is 2 px.
  Pattern strokes (roof battens, blades, ripples) stay in metres.
- **The grid** is 3 cm, or one pixel once 3 cm is more (`CanvasScene`,
  `Math.min(0.03, scale)`); it was a 13 px bar at the closest zoom. The draft's
  corner dots are 3.5 px.
- **Draft Sketch** keeps his widths and waves in metres, since his generated
  data stays his. At run time `paths.onScreen` never draws a length of his
  larger on screen than it was at his own scale, 1:250 at 96 dpi (≈ 0.066 m per
  pixel): his 0.103 m ink is at most about 1.6 px. The same cap applies to his
  wave's amplitude, which at the closest zoom moved a bed's edge 40 px off its
  corners. `Roads.tsx` takes the capped width (`inkWidth`) for its ink and its
  mask alike, or a hairline would show at junctions.
- **Technisch's watercolour** displacement is `min(0.3 m, 7 px)`. The theme's
  `Defs` are told the plan's scale for it (`themes/types.ts`). At ordinary zoom
  nothing changes; up close a bed no longer drifts off its corners.

## #2 — "the Vieleck does not set the point where the user clicks, but slightly next to it"

It was not a coordinate error. Every click was rounded to the grid, and the
grid is at least a metre, so a corner landed up to half a metre off, on lines
too faint to see.

- **Magnetic, not always** (`snap.snapNear`): a corner snaps to an intersection
  only within 6 px, and is otherwise kept where it was clicked, to the
  centimetre. Alt never snaps. A phone, which has no Alt, can now place a corner
  off the grid at all.
- **Closing reaches 12 px** (`useDrawingModes`, 5 cm floor), not a grid square.
  With snapped corners, a last corner exactly one square from the first was
  silently dropped on "Fertig": a 3 × 1 m bed became a triangle.
- **Another tool clears the draft**, and any complaint left over from the tool
  before it.
- **One message over the plan at a time**: while the controls carry the
  drawing's instructions or a complaint, the tool's hint steps aside
  (`.canvas-wrap:has(.canvas-controls .hint) .plan-hint`). The two had been
  lying on top of each other.

## #4 — "zooming in and out should be possible with the mouse wheel"

- **A plain wheel zooms**, about the pointer. It needed Ctrl/Cmd since doc 26,
  because a plain wheel swallowed the page's scroll. Since the workspace became
  a full-height app (doc 86) nothing scrolls behind the plan, so the reason is
  gone.
- **In proportion to the wheel** (`wheelFactor`): `exp(px × 0.0025)` for a wheel,
  `× 0.01` for a trackpad pinch (which arrives as ctrl-wheel), line and page
  deltas turned into pixels, at most ×2 per event. At a fixed 1.6 per event, a
  pinch slammed the view to its limit at once.
- **Safari's pinch** comes as `gesturestart`/`gesturechange` with a `scale`. It
  is handled, and prevented, where it used to zoom the page.
- **The address map** (`useMapSurface`) steps one tile level per 100 px of
  wheel, so a trackpad adds up to a notch. It captures the wheel over the map
  only; the page scrolls everywhere else.
- The shortcut list says "Mausrad" and the drawing hint says so too.

## Decided in the owner's absence

- The snap reach is 6 px rather than 8, because the grid is hard to see and every
  pull reads as a miss.
- A trackpad's two-finger swipe over the plan now zooms (as on Google Maps)
  instead of panning. The plan pans by dragging, as before.
