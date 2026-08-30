---
id: ninanatur-wave-11
title: "Wave 11: Draw first, say what it is afterwards"
initiative: ninanatur
initiative_version: 12
status: planned
depends_on: ninanatur-wave-10
demo_state: "A user drags out a rectangle, a circle and a freehand path, moves a vertex to shape one of them, then clicks each and says what it is — and the plan redraws it as a bed, a gravel path and a pool"
created: 2026-08-30
hash: 7ad9d3f8
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
| 1 | element-model | 42-element-model | planned | — |
| 2 | shape-tools | 43-shape-tools | planned | 42 |
| 3 | vertex-editing | 44-vertex-editing | planned | 43 |
| 4 | relabel-and-skin | 45-relabel-and-skin | planned | 42 |
| 5 | freehand-paths | 46-freehand-paths | planned | 43 |

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

## Open Research

- [ ] When a rectangle's vertex is dragged, does it become a polygon
      permanently, or does the tool refuse and offer "convert to polygon"?
      draw.io converts; the cost is that width/depth/rotation stop meaning
      anything, and the resize handles change behaviour under the user's hand.
- [ ] Does a path need a stored width, or is it a closed outline like
      everything else? A 1 m gravel path drawn as a line is two numbers; drawn
      as an outline it is twenty.

## Definition of done

Drawing a rectangle, a circle and a freehand path, dragging one vertex, and
labelling the three as bed, gravel path and pool produces a plan that shows
all three correctly — and the bed still takes plantings and computes its light.
