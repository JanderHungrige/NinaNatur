---
id: 86-the-plan-that-stayed-a-strip
title: The Plan That Stayed a Strip
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-23
wave_status: complete
depends_on: [11-garden-canvas, 26-drawing-canvas]
relates: [47-panel-order, 51-element-context-menu, 65-the-shade-switch]
source_files:
  - frontend/src/canvas/viewport.ts
  - frontend/src/canvas/useViewport.ts
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/StatusToast.tsx
  - frontend/src/App.tsx
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/canvas/viewportSize.test.ts
  - frontend/src/components/GardenCanvas.stage.test.tsx
  - frontend/src/components/StatusToast.test.tsx
  - tests/test_plan_stage.py
  - frontend/e2e/smoke.e2e.ts
data_flow: reads-existing
last_synced: 2026-09-14
status: complete
phase: all
mdd_version: 11
tags: [canvas, viewport, layout, sticky, toast, live-region, accessibility]
path: Workspace/Plan
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The sticky plan column (rule 4) was the stopgap until the workspace: doc 87 replaced both columns, and its guards moved to tests/test_workspace_layout.py."
  - "Since Wave 23's acceptance (2026-09-14) a Playwright smoke test, frontend/e2e/smoke.e2e.ts, measures the page's scroll, its height and the plan's share of the window through the core loop at 1280×720 and 375×812, on a garden it makes and deletes on the preview. It runs by hand (npm run test:e2e); whether it runs in CI is the owner's decision."
---

# 86 — The Plan That Stayed a Strip

Feature 0 of Wave 23, and stage 0 on its own: a bug fix, a few rules of CSS and
a status line people can see. It ships before anything else in the wave is
started, and it has to hold even if nothing after it is ever built.

## Purpose

On 2026-09-07 the garden plan measured **27 px high** on a desktop and **12 px**
on a phone, and it stayed that way until a reload (plan 05, B1). Separately, on
a wide window the plan leaves the screen as soon as the left column is scrolled,
and the line that says what just happened sits at the very bottom of the page,
where only a screen reader hears it. This feature makes the plan's height
independent of the plan, keeps the plan in view while the left column scrolls,
and turns the status line into a toast.

## Architecture

### Why the plan collapsed

Three facts formed a loop:

1. `useViewport` measured the SVG itself and stored its width and height in the
   view.
2. `viewBox(view)` derived the viewBox's aspect ratio from that measurement.
3. `.canvas { height: auto }` let the viewBox decide the SVG's rendered height.

One short measurement — a background tab, a short window, a phone's address bar,
an on-screen keyboard — became the viewBox's shape, which became the SVG's
height, which the next measurement confirmed. Observed: viewBox `-20 -0.6 40 1.2`.

### The fix: the stage owns the height

```
.canvas-wrap           container-type: inline-size
 └─ .canvas-stage      height: clamp(16rem, 75vh, 75cqi)      ← measured
     ├─ svg.canvas     position: absolute; inset: 0; 100% × 100%
     └─ .sun-readout   absolute, as before
```

- The stage's height comes from the window (75vh), capped at three quarters of
  its own width (75cqi) and never below 16rem. Nothing inside the stage can
  change it. A declaration without container units comes first, for a browser
  that does not know `cqi`.
- The SVG fills the stage exactly, so the measured box and the drawn box are the
  same box. Every pointer conversion (`useCanvasGestures`, `useSunReadout`, the
  drag hooks) keeps reading the SVG's rect and gets the numbers `useViewport`
  stored.
- `useViewport` observes the **stage** (a `stage` ref, returned beside
  `surface`), never the SVG. The Ctrl/Cmd-wheel handler stays on the SVG.

### Keeping the plan in view

Above the two-column breakpoint the plan's column (`.column--plan`) is
`position: sticky` at the top of the window, no taller than the window, and
scrolls itself when its content is taller. The left column scrolls past it; the
bloom year and the insect score below the plan stay reachable by scrolling the
column. Below the breakpoint nothing changes — one column, as before. The phone
is feature 5.

### The toast

`StatusToast` replaces `<p className="status">`. Its live region
(`role="status"`, `aria-live="polite"`) is always in the page, so the first
message is announced like every later one. A message appears at the bottom
centre of the window, above the page and below the element menu. The text is
keyed by a counter, so the same words said twice are announced and shown twice.

## Data Model

None.

## API Endpoints

None.

## Business Rules

1. **The plan's height never depends on its own measurement.** The stage's
   height is a function of the window and the column's width only.
2. **A measurement that is not one changes nothing.** A box of zero or
   non-finite width or height — not laid out yet, or hidden — leaves the view as
   it was (`measuredView`). A real measurement, however short and wide, is taken
   exactly as measured, and an unchanged one returns the same view so React has
   nothing to redraw.
3. **The viewBox has exactly the shape of the stored size**, so a click lands on
   the metre it points at. Only a degenerate size (zero or non-finite) falls
   back to the default 3:4, because a viewBox with no height draws nothing. The
   wave asked that a measurement with height 0 never yield an aspect below 0.3;
   it yields 0.75. What this feature deliberately does **not** do is put a floor
   under a real measurement: that would letterbox the drawing inside its box and
   move every click. The floor lives in the stage's CSS instead (16rem), where
   it changes the box rather than the drawing.
4. **The plan column is sticky only when there are two columns** — a
   `min-width` just above `.layout`'s 72rem breakpoint.
5. **The element menu is not clipped** by the column's own scroll. It is
   `position: fixed` and re-measures on scroll in the capture phase (doc 51),
   which already expected a plan scrolling inside its column.
6. **Status messages:**
   - Everything said still reaches the live region (doc 11).
   - A message that needs nothing from anyone goes once it could have been
     read: 70 ms per character, at least 5 s and at most 15 s (`readingTime`).
     When it goes, its text leaves the live region too.
   - A failure — what `run` catches — stays until it is closed with
     *Schließen* or replaced by the next message. The button sits outside the
     live region, so its label is never read as part of the message.
   - An empty status, as leaving a garden sets, shows nothing.
   - With reduced motion the toast appears and goes without a transition; that
     rule sits in the existing reduced-motion block, which must keep `.living`
     first (`tests/test_stylesheet.py`).

## Data Flow

- **Size:** stage `getBoundingClientRect()` → `measuredView()` →
  `view.widthPx/heightPx` (state in `useViewport`) → `viewBox(view)` on the SVG,
  and `toGarden`/`toScreen` in every pointer hook with the SVG's own rect as the
  offset. The SVG's rect equals the stage's, so both paths see one box. A `size`
  prop (tests) bypasses measurement, as before.
- **Status:** the `setStatus(text)` calls in `App.tsx` → `{ text, tone, stamp }`
  state → `StatusToast`. `run`'s catch passes the `problem` tone. Nothing else
  reads the status.

Full trace: `.mdd/audits/flow-the-plan-that-stayed-a-strip-2026-09-14.md`
(local).

## Dependencies

- **11-garden-canvas** — the live region, and focus is never removed.
- **26-drawing-canvas** — one transform; the "canvas never measured itself"
  guard, which this feature moves from the SVG to its stage.
- Related: **47-panel-order** (the columns), **51-element-context-menu** (the
  fixed, anchored menu), **65-the-shade-switch** (the sun readout placed in the
  stage's pixels; an SVG not laid out measures zero).

## Security

None: no input, no storage, no network.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
