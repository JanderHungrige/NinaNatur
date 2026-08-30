---
id: ninanatur-wave-10
title: "Wave 10: The garden drawn as a garden"
initiative: ninanatur
initiative_version: 11
status: complete
depends_on: ninanatur-wave-9
demo_state: "A user stamps a house, a lawn and an oak onto the plan, sketches a bed freehand without aiming precisely, names everything — and the plan looks like a garden plan, with shadows shaped like the things that cast them"
created: 2026-08-30
hash: 3e5bcd8a
---

# Wave 10 — The garden drawn as a garden

## Demo-State

A user stamps a house, a lawn and an oak onto the plan, sketches a bed freehand
without having to aim precisely, names everything — and the plan looks like a
garden plan, with shadows shaped like the things that cast them.

## Why this wave exists

Waves 7 and 8 made the plan *correct*. This wave makes it *a plan*. Right now
it is a grid with green polygons on it, and the one thing every object has in
common is that it is a circle — including the house.

## What the data-flow analysis found

Two things that decide the order of work.

### Occlusion is computed twice

`solar/shading.py::is_shaded` and `garden/sightlines.py::_blocks` each decide,
independently, whether a cylinder stands between two points. They agree today
only because both assume a cylinder. Give obstacles a real footprint in one and
not the other and a hedge blocks the sun but not the eye — **and nothing would
fail**, because no test compares them.

So feature 2 merges them rather than adding a third.

### The map already has the footprints and throws them away

`geo/surroundings.py::_radius_of` reduces a building outline to half its
diagonal, and `geo/osm.py::buildings_in` does not even fetch the outline
(`out tags center`). Doc 31 records the consequence in its Known Issues.
Polygon shadows are what make fetching real geometry worth the payload.

## Decided with the user

- **Existing gardens are deleted.** This is still a test deployment, so there is
  no compatibility path for circle-shaped houses and no re-computation of stored
  light values. One deliberate reset, stated in the deploy, rather than two
  shadow models living side by side — the double-path shape that has already
  caught this project twice.
- **The old Wave 10 (nursery order consolidation) becomes Wave 13.** Waves 11
  and 12 are reserved.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | object-footprints | 37-object-footprints | complete | — |
| 2 | polygon-shadows | 38-polygon-shadows | complete | 37 |
| 3 | element-stamps | 39-element-stamps | complete | 37 |
| 4 | freehand-shapes | 40-freehand-shapes | complete | 37 |
| 5 | garden-style | 41-garden-style | complete | 37 |

### 1 — object-footprints

An object stops being a circle. It gets a **footprint polygon** in garden metres
plus a rotation, and the kind vocabulary from Wave 7 gains what each kind
actually is:

| Property | Why it exists |
|---|---|
| default footprint | a house is a rectangle, a tree is a circle, a hedge is a strip |
| casts shadow | paving and gravel do not; a wall does |
| is a surface | a lawn is drawn under things, a shed on top |
| drawing symbol | what feature 5 renders |

**A tree stays a circle** and that is not a compromise — a crown is the one thing
a circle actually fits. `canopy.py` keeps deriving its radius from height.

The vocabulary grows to what a garden actually contains: `house`, `shed`,
`wall`, `fence`, `hedge`, `tree`, `shrub`, `bed`, `lawn`, `paving`, `gravel`,
`pond`, `path`, `other`.

### 2 — polygon-shadows

**A house rarely casts a round shadow.** The shadow of a footprint at a given sun
position is that footprint swept along the anti-solar direction by
`height / tan(altitude)` — for a convex outline, the convex hull of the original
and the swept copy.

This replaces both occlusion implementations with one. Sightlines and sunlight
then agree by construction rather than by coincidence, and a test pins that they
answer the same question about the same object.

Cost is real and worth stating: the light model samples every 15 minutes across
eight months per bed, so point-in-polygon replaces a distance comparison in the
innermost loop. Measure before and after; a correct model nobody waits for is
not shipped.

### 3 — element-stamps

Place a ready-made element and size it, in the manner of draw.io: pick from a
palette, click to place at its default size, then drag the handles. Rotate.
Snap to the metre grid, Alt to place freely — the rules feature 26 established.

Every stamp is an object of a kind, so it is clickable and labelable from the
moment it lands, which is what Wave 7's editor already does.

### 4 — freehand-shapes

Draw a shape by dragging, and **the tool cleans up after the hand**:

- **Simplify** the point stream (Ramer–Douglas–Peucker) so a sketch is a shape
  and not four hundred vertices.
- **Close it automatically** when the end lands near the start; a user should not
  have to hit the first point.
- **Resolve self-overlap** rather than refusing it, so a scribbled bed becomes
  the outline the user meant.

The whole point: *"sonst muss der user zu genau arbeiten"*. A drawing tool that
demands precision is a form with extra steps.

### 5 — garden-style

The plan should look like the reference: a hand-drawn, watercolour garden plan —
soft washes, textured outlines, tree crowns as foliage rather than discs.

- Kind drives the symbol: paving gets a slab pattern, gravel a stipple, lawn a
  wash, a pond a water tone, a tree a crown with texture.
- **Legibility outranks prettiness.** Every object keeps its focus ring, its
  accessible name and its click target. A plan nobody can tab through is a
  picture, not a tool.
- `prefers-reduced-motion` and high-contrast settings are respected; the texture
  is decoration and never the only thing carrying a meaning.

## Risks

- **Feature 2 changes every stored light value.** Deleting existing gardens is
  the agreed answer, and it must actually happen rather than being assumed.
- **Polygon shading in the innermost loop.** Benchmark it; a nested loop over
  edges inside a per-minute sampler is where a correct model becomes an unusable
  one.
- **Freehand overlap resolution is real computational geometry.** If it turns out
  to be its own project, the honest fallback is simplify-and-close without the
  self-intersection repair, stated rather than quietly dropped.
- **Style can eat accessibility.** The canvas is already the place where this
  project's accessibility rules are most at risk.

## Open Research

- [ ] Does Overpass `out geom` for a 50 m box stay within a courteous payload,
      and does the tile policy's spirit extend to it?
- [ ] Is there a shadow-polygon shortcut fast enough for the sampler, or does
      the sampler need to change (fewer samples, cached sun positions)?

## Definition of done

A user stamps a house and an oak, sketches a bed freehand, renames the house to
"Wohnhaus" and sees it drawn as one — and at 17:00 in March the house's shadow
falls across the lawn as a long rectangle, not as a circle.


## What the wave actually cost, and what it found

Five features, five docs, and eight defects that only the running app or a
guard test exposed:

| Found by | Defect |
|---|---|
| the vocabulary guard | the object editor still offered `building`, a kind the server dropped in feature 37 |
| driving the app | `Art` was a free text field over a closed server enum — any typo was an unpredictable 422 |
| driving the app | `step="0.5"` over `min="0.2"` made 6 m invalid, and an invalid number input blocks submission in silence |
| reading the a11y tree | the stamp buttons' name concatenated to `Wohnhaus10 × 8 m` |
| the stylesheet guard | `.obstacle` declared a CSS fill, which beats the per-object texture attribute — every kind would have drawn as the same grey |
| the metre guard (Wave 7) | the high-contrast rule set `stroke-width: 2.5`, a 2.5 **metre** outline |
| looking at the plan | the crown tile at 1.1 m is a two-pixel dot; trees read as flat discs |
| looking at the plan | the wobble at `baseFrequency="0.6"` is finer than a pixel and averages into a straight line |

The two guard-test finds are the ones worth keeping in mind: both would have
passed every unit test in the suite while being visibly wrong on screen.
