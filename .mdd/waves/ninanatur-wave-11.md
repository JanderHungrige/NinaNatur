---
id: ninanatur-wave-11
title: "Wave 11: Draw first, say what it is afterwards"
initiative: ninanatur
initiative_version: 12
status: complete
depends_on: ninanatur-wave-10
demo_state: "A user drags out a rectangle, a circle and a freehand path, moves a vertex to shape one of them, then clicks each and says what it is — and the plan redraws it as a bed, a gravel path and a pool"
created: 2026-08-30
hash: 5abbd009
---

# Wave 11 — Draw first, say what it is afterwards

## Demo-State

A user drags out a rectangle, a circle and a freehand path, moves a vertex to
shape one of them, then clicks each and says what it is — and the plan redraws
it as a bed, a gravel path and a pool.

*(This wave is not complete until this can be manually demonstrated.)*

## Why this wave exists

Wave 10 shipped a palette of ready-made elements, and the feedback on it was
specific: *"Die Elemente sind fixed in size. This is just a small selection."*
And: *"Wenn das Element steht, kann ich es anklicken und wählen, was es ist.
Beet, Kies-Weg, Pool … daraufhin verändert sich sein Skin."*

Wave 10 coupled **what a thing is** to **what shape it has**: a house *is* a
10 × 8 rectangle, a pond *is* a 3 m circle. That is backwards. A garden plan is
drawn first and named second, the way every drawing tool works — and the way
somebody actually thinks about their own garden.

## What the data-flow analysis found

The coupling is not only in the UI. It is in the schema.

| | `bed` | `obstacle` |
|---|---|---|
| Geometry | **`polygon` only** | `shape` / `width` / `depth` / `rotation` / `points` |
| Site | soil, moisture, four Ellenberg axes, `sun_hours` | — |
| Referenced by | **`planting`** (foreign key) | — |

Two consequences decide this wave's shape:

1. **A bed cannot be round today.** It has a polygon and no shape vocabulary at
   all, so "draw a circle and call it a bed" is not expressible in the current
   schema — no amount of UI work reaches it.
2. **`planting` hangs off `bed_id`.** Merging the tables is exactly the class of
   change CLAUDE.md warns about with `taxon`: a foreign key that either blocks
   the migration or takes someone's garden with it.

So feature 1 is the merge, and everything else waits on it. Doing the drawing
tools first would mean building them twice.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | element-model | .mdd/docs/42-element-model.md | complete | — |
| 2 | shape-tools | .mdd/docs/43-shape-tools.md | complete | 42 |
| 3 | vertex-editing | .mdd/docs/44-vertex-editing.md | complete | 43 |
| 4 | relabel-and-skin | .mdd/docs/45-relabel-and-skin.md | complete | 42 |
| 5 | freehand-paths | .mdd/docs/46-freehand-paths.md | complete | 43 |

### 1 — element-model

One table for everything drawn on the plan: geometry (`shape`, `width`, `depth`,
`rotation`, `points`), a kind, a label, and the site attributes a bed needs —
which are simply null on a paving slab. `planting` moves to `element_id`.

Being a bed becomes a property. That is the whole point: it is what lets an
element be re-labelled from bed to pool without moving between tables.

**Existing gardens are cleared, as in Wave 10** — still the test phase. The
migration carries a reset marker so it runs once per volume, and it is verified
against a volume grown under the Wave 10 image, not only against an empty one.

### 2 — shape-tools

Drag out a shape rather than stamp a fixed one: rectangle, circle, triangle,
polygon. Move, scale, rotate.

**The handles have to be findable.** Wave 10's are 8 px and appear only after a
click, which is why the elements read as fixed in size — the feature was there
and invisible. Discoverability is part of this feature, not a polish item.

### 3 — vertex-editing

Insert a vertex on an edge, drag it, delete it. The behaviour every flowchart
tool has and the reason a drawn bed can follow a real boundary.

Open question below: what a rectangle becomes when its first vertex is dragged.

### 4 — relabel-and-skin

Click an element, choose what it is, and the drawing changes: a bed takes soil
colour, a gravel path takes the stipple, a pool takes water. Wave 10 already
has the symbols; this feature is what points them at a decision the user makes
after drawing rather than before.

**Re-labelling away from a bed warns and then deletes its plantings** — the
user sees "hier stehen 7 Pflanzen, die dabei verloren gehen" and confirms.
Chosen over blocking, because a dead end in the middle of drawing is worse than
a warned loss, and over silently keeping them, which would leave data that
nothing displays.

### 5 — freehand-paths

Freehand as a first-class way to draw, aimed at paths. Wave 10's clean-up
(`canvas/freehand.ts`) already simplifies, closes and untangles; this feature
gives it a stroke that stays open — a path is a line with a width, not a closed
outline — and hands the result to the same element model.

## Risks

- **The `planting` foreign key.** The migration either moves it correctly or
  takes a garden with it. Clearing gardens removes the sharp edge for now, but
  the same migration has to be written correctly before real gardens exist.
- **Two waves of geometry churn in a row.** Wave 10 rewrote the obstacle table;
  this rewrites it again into `element`. Anything reading `obstacle` directly —
  `solar/shading.py`, `garden/sightlines.py`, `api/geo.py` — moves with it.
- **Discoverability is not testable the way behaviour is.** "The handles are
  findable" has no assertion. It needs looking at the running app, and saying
  so honestly rather than declaring it done.

## Geometry, as decided

Both open questions are answered, and between them they make the model
*smaller* than Wave 10's.

### Points are the only area geometry — no conversion, ever

A rectangle is stored as its four points, like every other outline. The question
"what does a rectangle become when you drag its vertex" then has no answer to
give, because nothing changes representation.

What a rectangle keeps is a **constraint hint**, honoured by the editing tool
and by nothing else: `rect` means "these corners are meant to stay square", so
dragging one corner moves its two neighbours with it. A house should not become
a trapezoid by accident. Insert a vertex, or drag one deliberately out of true,
and the hint is dropped — the geometry is untouched, only the promise ends.

`width`, `depth` and `rotation` therefore leave storage entirely. Rotation is
applied to the points; the accumulated float error over a hundred rotations is
far below the centimetre the outline is rounded to.

### The circle is the one real exception

Sixteen segments are visible when you zoom in, and ponds and tree crowns are
common. A circle stays a centre and a radius. Inserting a vertex into one is
the single genuine conversion left in the model, and it means something
unambiguous when it happens.

### A path is a line with a width — and so are walls, fences and hedges

Today a wall is a 6 × 0.3 m rectangle, which means **a wall that turns a corner
needs two objects**. As a polyline with a width it is drawn in one gesture, and
vertex editing works on it for free. The same shape covers path, wall, fence
and hedge.

This is affordable because of a contract Wave 10 already established: nothing
downstream knows how an element is stored. `footprint_of` returns a polygon,
and `solar/shading.py` (8 call sites) and `garden/sightlines.py` (5) consume
only that. A line costs one new branch there and nothing beyond it.

**The cost to name:** expanding a polyline to a polygon is not trivial at the
corners — mitre or round joins — and a tight turn makes the expansion overlap
itself. That is the same class of problem `resolveOverlap` solved for freehand
in Wave 10, and it needs the same care.

### The vocabulary

Three shapes, down from Wave 10's three with clearer meaning:

| Shape | Stored as | Constraint hint |
|---|---|---|
| `polygon` | points | optional `rect` — corners stay square |
| `circle` | centre, radius | — |
| `line` | points, width | — |

## Definition of done

Drawing a rectangle, a circle and a freehand path, dragging one vertex, and
labelling the three as bed, gravel path and pool produces a plan that shows
all three correctly — and the bed still takes plantings and computes its light.


## What the wave cost, and what it found

Five features. The table merge was the whole of feature 1 and it moved twelve
files; everything after it was small by comparison, which is what the data-flow
analysis predicted and the reason the merge went first.

| Found by | Defect |
|---|---|
| the test suite | `planning.py` still joined `bed` in a raw SQL string — nothing type-checks a query |
| the test suite | my own schema edit swallowed the `garden` table; 156 tests failed with one cause |
| writing feature 44 | `update_obstacle` dropped explicit nulls, so the rectangle hint could not be cleared |
| writing feature 44 | its allow-list still named `depth` and `rotation`, which stopped being columns in feature 42 — a resize would have been refused |
| a test | Escape did not abandon a freehand stroke after it moved into a hook |
| the file-length hook | `GardenCanvas.tsx` at 521 lines carrying five interaction modes |

The two in `update_obstacle` are the ones worth remembering: both were live,
neither had a test, and both would have looked like the handles simply not
working.

## What is not done

- A path is one metre wide until somebody changes it; the width cannot be set
  while drawing.
- `planning.py` and `schemas.py` are still over the 300-line limit. They were
  before this wave too, and splitting them is its own task.
