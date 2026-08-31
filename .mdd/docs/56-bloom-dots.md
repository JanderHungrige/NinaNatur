---
id: 56-bloom-dots
title: Flowers as Dots, Grouped the Way They Are Planted
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-14
wave_status: complete
depends_on: [22-bloom-palette]
relates: [58-painted-plan]
source_files:
  - frontend/src/canvas/blooms.ts
  - frontend/src/canvas/geometry.ts
  - frontend/src/components/CanvasScene.tsx
routes: []
models: []
test_files:
  - frontend/src/canvas/blooms.test.ts
  - frontend/src/canvas/geometry.test.ts
  - frontend/src/components/CanvasScene.style.test.tsx
data_flow: reads-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [bloom, colour, canvas, clustering]
path: Canvas/Bloom
integration_contracts:
  - from: 22-bloom-palette
    function: colours per bed per month
    when: a month is shown
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Density is fixed per square metre; a whole-garden zoom and a close-up may want different answers."
---

# Flowers as dots, grouped the way they are planted

## What this is

A bed's flowers are dots inside it, one group per colour — not a bar across it.

## Decisions

### A bar says something untrue

Bands said the bed was half yellow and half blue. What is true is that *some of
the flowers* are yellow and some are blue. Dots say that, and they say it at the
size a flower actually is.

### Clustered, because that is how anybody plants

Nobody puts one salvia here and one over there. Each colour gets a centre inside
the bed and its flowers around it, with the distance drawn as `sqrt(random)` so
the group stays even rather than crowding its middle.

A tiling pattern could not do this at all: a pattern repeats uniformly, and
clustering is the opposite of uniform. That is why this is generated geometry
rather than another `<pattern>`.

### Seeded from the bed's id

Without that the planting reshuffles on every React render, which reads as the
garden twitching. The same bed draws the same way every time, and two beds draw
differently.

### The footprint, not the bounding box

Placement is rejection-sampled against the outline, so an L-shaped bed gets no
flowers in its notch. That needed a point-in-polygon test on the client, which
did not exist — the server has had one since Wave 10 and the two now agree by
using the same rule.

### Bounded

A bed with two hundred plants is not two hundred dots; it is a bed that reads as
full. Past ninety, more dots carry no more meaning and cost a node each.

### "Never recorded" keeps its hatch

Colour is recorded for 6.6% of the catalogue. An unknown colour must not become
a grey dot among coloured ones — that would put it in the same sentence as a
known colour. It stays the hatch it has always been.

## What the existing tests caught

The dots are `aria-hidden` decoration, and a test written in Wave 10 asserts
that every such element also sets `pointer-events: none`. It failed immediately:
without it, seventy flowers sit between the pointer and the bed underneath and
swallow the click that selects it.

## Definition of done

A bed with three flower colours shows three groups of dots; a bed with an
unrecorded colour still shows the hatch; the same bed looks the same twice.
