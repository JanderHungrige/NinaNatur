---
id: 41-garden-style
title: A Plan That Looks Drawn
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-10
wave_status: complete
depends_on: [37-object-footprints, 39-element-stamps]
relates: [26-canvas-drawing, 22-bloom-colours]
source_files:
  - frontend/src/components/GardenSymbols.tsx
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/kinds.ts
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/components/CanvasScene.style.test.tsx
  - tests/test_kind_vocabulary.py
  - tests/test_stylesheet.py
data_flow: reads-existing
last_synced: 2026-08-30
status: complete
phase: all
mdd_version: 11
tags: [svg, patterns, watercolour, accessibility, contrast, dark-mode]
path: Canvas/Style
integration_contracts:
  - from: 37-object-footprints
    function: KindTraits.symbol
    when: an object is drawn
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The watercolour filter displaces the drawn edge by up to 30 cm; hit testing uses the undisplaced geometry, so the click target and the painted edge differ slightly at the boundary."
---

# A plan that looks drawn

## What this is

Every kind is drawn as what it is: paving as slabs, gravel as stipple, lawn as a
wash with blades, a pond with ripples, a tree crown as overlapping foliage
rather than a disc. The outlines wobble like a pen rather than a plotter.

## Decisions

### The symbol is the server's word, not the stylesheet's

`KindTraits.symbol` already said what each kind should be drawn as. It is now
carried through `kinds.ts` and guarded by the same pytest that binds the rest of
the vocabulary: a kind whose symbol drifts is drawn as something else entirely —
paving as water — and nobody sees a stack trace.

### The textures are measured in metres

Everything is `patternUnits="userSpaceOnUse"` in the canvas's own unit. A slab
pattern sized in pixels would be a different slab at every zoom level, which is
the mistake the drawing tolerances and the grid already avoid.

Two things had to be tuned against the running app rather than reasoned about:

- **The crown tile started at 1.1 m with 30 cm leaves.** At ordinary zoom that
  is a two-pixel dot, and the trees read as flat green discs — the one thing
  this feature exists to stop. The tile is 2.4 m now, so a 6 m crown shows a
  handful of blobs.
- **The wobble started at `baseFrequency="0.6"`.** That is a wave every 1.7 m,
  finer than a pixel at ordinary zoom, and it averaged back into a straight
  line. At 0.16 the edge reads as drawn.

### One filter on the group, one pattern per symbol

The wobble is applied to the group of objects, not to each object: a filter per
object is a filter run per object. Likewise six paving slabs reference one slab
pattern — a pattern per object is a `defs` block that grows with the garden, and
there is a test that fails if it starts to.

### Drawing order is a property of the kind

A lawn goes under the shed standing on it. `is_surface` already decided this on
the server, so the canvas sorts by it rather than by the order somebody happened
to click.

### Legibility outranks prettiness

Every object keeps its `role="button"`, its `tabIndex`, its accessible name and
its click target — a plan nobody can tab through is a picture, not a tool. The
texture is decoration and never the only thing carrying a meaning: the name says
"Kies" whether or not the stipple renders.

Under `prefers-contrast: more` and `forced-colors: active` the washes and the
filter are dropped entirely and the outline carries the shape alone.

### Dark mode is not the light plan inverted

A wash that works on paper glows on a dark ground. The dark palette is the same
colours desaturated and dropped in value, declared as their own tokens, so the
plan stays a plan rather than becoming a set of lights.

## The bug the stylesheet guard caught

`.obstacle` declared `fill: color-mix(…)`. A CSS fill beats a `fill` presentation
attribute, so every kind would have been drawn as the same grey while the markup
faithfully asked for slabs, water and foliage — and the component test asserting
on the attribute would have passed. There is now a guard that fails if
`.obstacle` declares a fill at all.

The metre guard from Wave 7 caught the other one in the same pass: the
high-contrast rule set `stroke-width: 2.5`, which on this canvas is a 2.5 metre
outline.

## Verified in the running app

- One object of all fourteen kinds on one plan, in light and dark mode: every
  texture renders, the trees read as foliage, and the pond has ripples.
- Clicking a house still selects it and raises its handles, with the texture
  applied.
