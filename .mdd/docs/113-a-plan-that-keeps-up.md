---
id: 113-a-plan-that-keeps-up
title: A Plan That Keeps Up
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [11-garden-canvas, 65-the-shade-switch, 95-look-before-you-argue, 96-a-theme-is-a-thing]
relates: [112-drawing-at-any-zoom, 64-light-across-the-bed, 58-painted-plan]
source_files:
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/components/SceneWorld.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/SunMap.tsx
  - frontend/src/components/ReliefMap.tsx
  - frontend/src/components/SunReadout.tsx
  - frontend/src/canvas/cellPaths.ts
  - frontend/src/canvas/useStableHandlers.ts
  - frontend/src/canvas/useMoving.ts
  - frontend/src/canvas/useElementDrag.ts
  - frontend/src/canvas/useClusterDrag.ts
  - frontend/src/canvas/useHandleDrag.ts
  - frontend/src/canvas/useVertexDrag.ts
  - frontend/src/canvas/useCanvasGestures.ts
  - frontend/src/usePinch.ts
  - frontend/src/styles.css
  - frontend/src/themes/draft-sketch/theme.css
routes: []
models: []
test_files:
  - frontend/src/components/GardenCanvas.memo.test.tsx
  - frontend/src/components/GardenCanvas.wheel.test.tsx
  - frontend/src/components/SunMap.test.tsx
  - frontend/src/components/ReliefMap.test.tsx
  - tests/test_plan_stylesheet.py
data_flow: greenfield
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [performance, react-memo, svg, paint, sun-map, relief, pan, zoom, owner-check]
path: Canvas/Performance
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "A pan still changes the viewBox, which repaints the whole drawing on every frame. Moving the drawing on the compositor during a gesture, and committing the viewBox on release, is the next step if this is not enough (findings #11, item 1b); it was not built without a measurement to justify it."
  - "Textures pause while the plan moves: Technisch's wobble pops back when it stops, and Draft Sketch's dabs are plain dots until then."
sister_projects: []
---

# 113 — A Plan That Keeps Up

## What the owner saw (2026-09-21, #11)

> everything is quite laggy (not the first load, but working with it later,
> especially zooming in and out or dragging the map) … can certain things be
> saved and only loaded when needed?

## Where the time went

Pan and zoom already go through one viewBox, so no element is moved one by one.
The cost was elsewhere, and it came from four places at once:

1. **Every pan frame re-rendered the whole scene in React.** The view lived in
   the canvas and was handed to the scene, and nothing below it was memoised.
2. **Every frame repainted the most expensive paint in the app.** A viewBox
   change is not composited, and Technisch runs a turbulence and displacement
   filter over every shape, while Draft Sketch has masked paper and a mask on
   each bloom. Doc 95 measured one zoom step at 66 ms and 98 ms, on a phone at
   4× CPU slowdown.
3. **The sun map and the relief were a `<rect>` per cell**: thousands for a
   garden made from the map, all rebuilt and repainted per frame. A finer grid
   (#6) would have been four times as many for every halving.
4. **With the shade on, a plain mouse move re-rendered everything**, because the
   readout's state lived in the canvas.

## What changed

- **The scene is split** (`CanvasScene` → `SceneWorld`). The paper, the grid and
  the compass follow the view. Everything else is a memoised `SceneWorld` that is
  never given the viewport, only the scale in halvings (`planScale`), which
  changes a few times across a zoom. For memo to hold, what it is given must
  stay the same object between frames:
  - `useStableHandlers` wraps the callbacks once each, reading the newest
    version through a ref;
  - the drag hooks' `grab` functions are stable;
  - the cluster drag returns the displaced clusters memoised;
  - empty defaults are module constants, not a fresh `[]`.

  `GardenCanvas.memo.test.tsx` counts how often the shapes are drawn across a
  pan, a wheel and a hover over the sun map. It is zero each time. That test
  found a fresh `[]` the first time it ran. The land around the garden (doc 114)
  is a second memoised layer beside `SceneWorld`, under it, held to the same
  rule and counted by the same test.
- **The sun map and the relief are a few paths** (`canvas/cellPaths`). There is
  one path per wash (at most twenty) and one per slope step (eight each way). A
  run of equal cells along a row is one rectangle. The relief's opacity is
  quantised to those eight steps, finer than its faint grey can show.
- **The readout is its own component** (`SunReadout`), so a mouse move with the
  shade on re-renders one label. It is not read at all while a pan holds the plan.
- **The drag hooks attach their window listeners once per drag.** They depended
  on `options`, a new object every render, so each pointer move tore the
  listeners down and put them back.
- **The costly paint pauses while the plan moves** (`useMoving`, the
  `canvas--moving` class, set on the element and never through state): the
  watercolour filter, his paper, and his bloom masks. A pan starts it on its
  first real move and ends it on release; a pinch starts it on the second finger
  and ends it when the pair breaks; the wheel pulses it and lets it lapse after
  150 ms.

## What was not done, and why

- **Compositing the gesture** (a CSS transform on the drawing during a pan, the
  viewBox committed on release) is the large remaining step. It rewrites the
  gesture layer and changes how every pointer is converted mid-gesture. The
  steps above remove most of what a frame did; this one waits for a measurement
  on the owner's machine that says it is still needed.
- **requestAnimationFrame batching** of pan updates: browsers already align
  pointer moves to frames, and batching would have made every gesture test wait
  on a frame for little gain.
