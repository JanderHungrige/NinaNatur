---
id: 58-painted-plan
title: Pigment, and a Rim Where the Paint Stops
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-14
wave_status: complete
depends_on: [41-garden-style]
relates: [56-bloom-dots]
source_files:
  - frontend/src/components/GardenSymbols.tsx
routes: []
models: []
test_files:
  - frontend/src/components/CanvasScene.style.test.tsx
data_flow: reads-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [watercolour, svg-filter, canvas, style]
path: Canvas/Style
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# Pigment, and a rim where the paint stops

## What this is

The plan reads as painted rather than plotted — colour that varies inside a
shape, and an edge that pools the way paint does.

## What was already there, and why it was not enough

The wobble filter has existed since Wave 10: turbulence displacing the outline
so it wavers like a pen. The plan still read as CAD, so "add a filter" was never
the answer.

Looking at it named the reason. **Every fill was exactly one flat colour.** A
wobbled edge around a perfectly even field is still a technical drawing — the
flatness is the tell, not the straightness. And the symbols were already drawn
objects: gravel has grains, grass has blades, water has ripples, a roof has
battens. The drawing was fine. The paint was not.

## Decisions

### Two primitives, every symbol

Both changes live in the shared filter rather than in each pattern:

- **Pigment.** Fine noise, desaturated and kept faint, multiplied back inside
  the shape. That mottles every wash at once. Past about a quarter opacity it
  stops looking like paper and starts looking like dirt.
- **The rim.** Watercolour is darker where it stops and thinner in the middle.
  Eroding the painted shape and keeping the difference is exactly that band.

Doing this per symbol would have been eleven edits agreeing by hand. One filter
is one answer.

### The rim is measured in metres

`feMorphology`'s radius is in user units, which on this canvas are metres. A
radius in pixels would be a rim of a different width at every zoom — the same
trap that put a three-metre focus ring on the plan in Wave 11, and the test
guards it the same way.

## The first attempt shipped unseen, and was wrong

It went out on reasons alone because the Browser pane returns a blank capture
whenever this SVG is on screen. The user looked and said it still read as a
technical drawing. They were right.

**Rasterising it was the whole fix.** `qlmanage` renders an SVG to PNG, so a
standalone harness carrying the real filter and the real washes could be looked
at, changed, and looked at again in seconds. Three things were wrong at once and
none of them were guessable:

1. **The wobble was invisible.** Displacement of 0.42 across a forty-metre plan
   is nothing. Two wavelengths now — a long one that bends the outline and a
   short one that roughens it, because one alone reads as either wavy or
   jittery.
2. **The "pigment" was grey dirt.** Desaturated noise multiplied over a wash is
   not paint; it is a smudge. It is a variation in the shape's own colour now —
   black at low alpha through coarse turbulence, never a grey layer on top.
3. **The patterns tiled into a visible lattice.** Grass blades in perfect rows,
   gravel in a grid, battens evenly spaced. This was the strongest technical
   signal on the plan and the filter could never have fixed it.

### The lattice is the same lesson the bloom bands taught

A tile small enough to hold one mark can only repeat into a grid. The tiles are
two to three metres across now and carry forty or fifty marks scattered by hand,
so nothing lines up at garden zoom. A roof is staggered tiles rather than
parallel battens — evenly spaced lines are a hatch, and a hatch is corrugated
iron. Ripples wander and sometimes break off, the way a pen loses pressure.

### And the outline was a uniform hard stroke

Thinner and part-transparent now, so the wash carries the shape and the line
only suggests where it ends.

## Definition of done

Somebody shown the plan calls it a drawing of a garden rather than a diagram of
one. Verified by rasterising the same filter and washes and looking at the
result, which is the check the first attempt could not run.
