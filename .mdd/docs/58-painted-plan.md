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
known_issues:
  - "Not verified by eye: the Browser pane cannot capture this SVG, so the visual judgement is outstanding."
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

## What is not verified

**Nobody has looked at it.** The Browser pane returns a blank capture whenever
this SVG is on screen — the canvas is fully in view at full opacity and the
screenshot comes back empty, while the DOM reports everything correctly. That is
a tool limitation, not a fault in the page.

The wave's plan said this feature is not done until it is looked at on a real
plan with real beds. That has not happened, and the change is defensible on its
reasons rather than on its result. **It needs the user's eyes before it is
believed.**

## Definition of done

Somebody shown the plan calls it a drawing of a garden rather than a diagram of
one — which is still outstanding.
