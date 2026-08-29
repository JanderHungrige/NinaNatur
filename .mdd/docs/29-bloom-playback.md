---
id: 29-bloom-playback
title: The Year, Playing on the Plan
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-7
wave_status: complete
depends_on: [26-drawing-canvas]
relates: [24-month-suggestions, 15-timeline-ui]
source_files:
  - ninanatur/api/planning.py
  - ninanatur/api/schemas.py
  - ninanatur/bloom/palette.py
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/components/BloomPlayer.tsx
  - frontend/src/App.tsx
routes:
  - GET /api/v1/gardens/{token}/bloom
models: []
test_files:
  - tests/test_bloom_palette.py
  - frontend/src/components/BloomPlayer.test.tsx
data_flow: reads-existing
last_synced: 2026-08-29
status: complete
phase: all
mdd_version: 11
tags: [bloom, colour, playback, animation, reduced-motion, accessibility]
path: Bloom/Playback
integration_contracts:
  - function: GET /gardens/{token}/bloom
    when: the plan is coloured by month
    note: unrecorded colour is its own state, never a colour that could be mistaken for an answer
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 29 — The Year, Playing on the Plan

## Purpose

Click a month and the beds take the colour of what flowers then. A play button
runs the year in about seven seconds.

The timeline already says *when* a garden flowers. This says *where*, which is
the question a plan is for.

## Two things this must get right

### Unknown colour is not a colour

Flower colour is recorded for **590 of 8,939** species — 6.6%. A bed of plants
whose colour was never recorded must not render green, grey or beige, because
every one of those reads as an answer. It gets a **hatch**, and the legend says
what the hatch means.

This is the same rule as everywhere else in this project, at the layer where it
is easiest to break: a fill is the most confident thing a UI can draw.

### `prefers-reduced-motion` stops the animation

An autoplaying year is exactly the motion that setting exists for. When it is
set, the play button is not rendered and the month stepper remains — the feature
still works, it just does not move on its own.

## The API

`GET /gardens/{token}/bloom` returns, per bed and per month, the colours in
flower and how many plantings had no colour recorded:

```json
{"beds": [{"bed_id": 1, "months": [{"month": 6,
   "colours": ["yellow", "white"], "unknown": 3, "flowering": 5}]}]}
```

Computed server-side rather than in the browser because the frontend has bed
plantings but neither their flowering windows nor their colours, and shipping
those per planting to render a swatch would send the catalogue to the client.

Wrapping windows are honoured — this reads the same `flowering_months` the
month filter was fixed to use in Wave 6.

## Business Rules

- **A bed with nothing in flower is empty, not black.** It renders as it does
  the rest of the time.
- **Several colours share the bed** as bands rather than blending. Mixing yellow
  and blue into green would invent a flower nobody planted.
- **Playback is ~7 seconds for 12 months** and loops until stopped.
- **The month the player is on is the month the suggestions filter to**, which is
  the same single piece of state Wave 6 feature 4 established. There is one
  selected month.

## Security

Read-only over data the garden already exposes. No new user input.

## Known Issues

- **Most beds will show the hatch.** Colour is recorded for 6.6% of the
  catalogue, so a real garden of native species is mostly "not recorded". That
  is the honest picture and it is also a thin feature until the coverage
  improves — the BfN request that would fix it is still deferred.
- **The legend is the hint text**, not a swatch key on the plan itself.

## Bugs

**The stylesheet was still measuring in pixels.** Feature 1 moved the plan's
viewBox into garden metres and left every length in the stylesheet behind:
`.bed { stroke-width: 2 }` had meant 0.2 m under the old ten-pixels-per-metre
viewBox and now meant **two metres**. A 4 m bed painted a metre of outline
outside itself on every side, which swallowed most of the shape, and the 1 m
grid rendered as a field of blocks rather than lines.

It was in every screenshot from feature 1 onward and I registered it in none of
them — it only became undeniable when a pattern fill had to compete with it.
`tests/test_stylesheet.py` now refuses a stroke wider than 30 cm on any plan
selector.

**The pattern was sized in metres, twice wrongly.** Six units meant a six-metre
band, wider than most beds; sub-metre bands tiled from the SVG origin rather
than from the shape. `objectBoundingBox` says what was actually meant — split
this bed into one band per colour, whatever size the bed is.

**The palette loaded only on refresh.** A garden opened from its own link goes
through `load`, not `refresh`, so the plan had no colours at all until something
was edited. Found by opening a garden by its link, which is how every returning
user will arrive.
