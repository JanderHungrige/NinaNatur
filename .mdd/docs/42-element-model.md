---
id: 42-element-model
title: One Drawn Element, Named Afterwards
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-11
wave_status: complete
depends_on: [37-object-footprints]
relates: [43-shape-tools, 45-relabel-and-skin, 12-bed-light]
source_files:
  - ninanatur/garden/footprint.py
  - ninanatur/garden/elements.py
  - ninanatur/garden/models.py
  - ninanatur/ingest/db.py
routes:
  - /api/v1/gardens/{token}/elements
  - /api/v1/gardens/{token}/elements/{element_id}
models: [element, planting]
test_files:
  - tests/test_element_model.py
  - tests/test_footprint.py
data_flow: writes-existing
last_synced: 2026-08-30
status: complete
phase: all
mdd_version: 11
tags: [schema, geometry, migration, elements, polyline]
path: Garden/Elements
integration_contracts:
  - from: 37-object-footprints
    function: footprint_of
    when: anything asks what ground an element covers
satisfies_contracts:
  - from: 43-shape-tools
    function: element geometry as points
    when: a shape is drawn or resized
    status: done
    verified_at: "ninanatur/garden/elements.py:60"
  - from: 45-relabel-and-skin
    function: kind is a column, not a table
    when: an element is re-labelled
    status: done
    verified_at: "ninanatur/garden/elements.py:60"
security_read_sites: []
known_issues: []
---

# One drawn element, named afterwards

## What this is

`bed` and `obstacle` become one table, `element`. Geometry, a kind, and the
site attributes a planting place needs — null on a paving slab. Being a bed is
a property.

## Why it has to be the schema and not the UI

A bed today has a `polygon` column and no shape vocabulary at all. "Draw a
circle and call it a bed" is not expressible, however much interface is written
on top. And `planting` hangs off `bed_id`, so re-labelling a bed to a pool
means moving a row between tables and deciding what happens to its plants —
which is a data question wearing a UI costume.

## The geometry

Three shapes, and `width`/`depth`/`rotation` leave storage entirely.

| Shape | `points` | `width` | Notes |
|---|---|---|---|
| `polygon` | the outline | — | any area, including a rectangle |
| `circle` | — | diameter | a centre and a radius; the one non-point shape |
| `line` | the centreline | band width | paths, walls, fences, hedges |

A rectangle is four points like any other outline, so there is nothing to
convert when a vertex is dragged. What it carries instead is
`constraint_hint = 'rect'`, honoured by the editing tool and by nothing else:
drag one corner and its neighbours follow, so a house stays square. Break it
deliberately and the hint is dropped — the geometry never changes, only the
promise ends.

Rotation is applied to the points. A hundred rotations accumulate float error
far below the centimetre the outline is rounded to, so storing an angle would
buy nothing and add a second source of truth.

## Why a line is affordable

Nothing downstream knows how an element is stored. `footprint_of` returns a
polygon; `solar/shading.py` (8 call sites) and `garden/sightlines.py` (5)
consume only that. A line is therefore one new branch in `footprint_of` — the
polyline offset — and nothing beyond it.

That offset is the one piece of real new geometry in this feature. Corners need
a join, and a tight turn makes the band overlap itself. It is the same class of
problem `resolveOverlap` solved for freehand in Wave 10, and it gets the same
treatment: solve it in the geometry module, with its own tests.

**A wall that turns a corner is one element now.** It was two.

## The migration

Gardens are cleared, as in Wave 10 — still the test phase, and the user chose
this over migrating. The reset carries its own marker so it runs once per
volume.

The rule that matters is unchanged from Wave 10 and from the catalogue: **the
migration is verified against a volume grown under the previous image**, not
only against an empty one. A fresh volume never has an `obstacle` table to drop
or a `planting.bed_id` to rewrite, which is exactly why it proves nothing here.

## Definition of done

A polygon, a circle and a line can be stored and read back; each yields a
footprint polygon; `planting` hangs off `element_id`; and a volume grown under
the Wave 10 image comes up on this one without an error.
