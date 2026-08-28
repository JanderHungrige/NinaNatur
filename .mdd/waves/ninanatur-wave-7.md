---
id: ninanatur-wave-7
title: "Wave 7: The garden as a drawing"
initiative: ninanatur
initiative_version: 10
status: in_progress
depends_on: ninanatur-wave-6
demo_state: "A user draws their garden — outline, beds, trees, walls — labels each object by clicking it, enters what already grows there, and plays the bloom year as colour on the plan"
created: 2026-08-28
hash: f3fbee91
---

# Wave 7 — The garden as a drawing

## Demo-State

A user draws their garden — outline, beds, trees, walls — labels each object by
clicking it, enters what already grows there, and plays the bloom year as colour
on the plan.

## What this replaces

Wave 3 shipped coordinate forms: type x, y, width, depth. That was honest for a
keyboard path and wrong as the primary interface. Nobody knows their bed is at
x=3.5. They know it is *along the fence, left of the shed*.

**The forms stay.** They become the accessible equivalent rather than the main
way in — the rule from Wave 3 holds, and drawing is where keyboard access is
usually dropped.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | drawing-canvas | 26-drawing-canvas | complete | — |
| 2 | object-labelling | 27-object-labelling | planned | 26 |
| 3 | existing-plantings | 28-existing-plantings | planned | 27 |
| 4 | bloom-playback | 29-bloom-playback | planned | 27 |

**Queued after this wave:** `30-landing-and-garden-id` — the Wave 1 landing page
returns as the entry point (new garden, or load by ID), and the garden ID becomes
visible with a copy button until Wave 9 brings accounts. Requested during this
wave's planning, to be built once the four features above are merged.

### 1 — drawing-canvas (#2.1)

Draw polygons on a metre grid: garden outline, beds, buildings, hedges. Trees and
point obstacles as placed circles.

- **A 1 m grid that means one metre.** Zoom by scroll wheel and by buttons —
  buttons because a trackpad-less or motor-impaired user must not be locked out
  of a zoom-only interaction.
- Snap to the grid, with a modifier to place freely.
- **Undo is not optional.** A drawing tool without it is a tool people are afraid
  to use.

### 2 — object-labelling (#2.1)

Click an object to say what it is: kind, size, height — and for beds, **height
above ground**, because a raised bed sits in different light than a border and
Wave 9's sightlines need it.

Every object carries a type from a fixed vocabulary plus a free label. The
vocabulary drives shading and scoring; the label is for the user.

### 3 — existing-plantings (#2.2)

Draw and name what already grows there. Names resolve against the catalogue —
German or scientific, using Wave 6's index — and a match feeds the score and the
timeline exactly like a planned planting.

**An unmatched name is kept, not rejected.** It stays on the plan as the user's
own record and is reported as not-yet-identified. Discarding it would tell
someone their garden is wrong because our catalogue is incomplete.

### 4 — bloom-playback (#7a)

Click a month and the beds take the colour of what flowers then. A play button
runs the year in about seven seconds.

Two things this must get right:
- **Unknown colour is not a colour.** Most of the catalogue has none; those beds
  render in a neutral hatch that reads as *unrecorded*, never as green or grey
  that could be mistaken for a real answer.
- **`prefers-reduced-motion` stops the animation** and leaves the month stepper.
  An autoplaying year is exactly the motion that setting exists for.

## Risks

- Canvas interaction is where accessibility dies. Every drawing action needs a
  keyboard path decided while building, not retrofitted.
- Polygon editing is deceptively large — vertex drag, insert, delete, and
  self-intersection all need handling. Worth its own feature rather than being
  smuggled into the canvas.

## Open Research

- How much of the coordinate form survives as the keyboard path versus being
  replaced by keyboard vertex editing on the canvas itself. Decide while building
  the canvas, with a real screen reader.

## Definition of done

A user draws an outline, two beds, a shed and a tree; labels them; adds a shrub
they already have; and watches the plan change colour through the year.
