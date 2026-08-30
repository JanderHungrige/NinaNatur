---
id: 37-object-footprints
title: A House Is Not a Circle
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-10
wave_status: complete
depends_on: [27-object-labelling]
relates: [38-polygon-shadows, 41-garden-style]
source_files:
  - ninanatur/garden/footprint.py
  - ninanatur/garden/objects.py
  - ninanatur/garden/models.py
  - ninanatur/garden/store.py
  - ninanatur/ingest/db.py
  - ninanatur/api/schemas.py
routes:
  - POST /api/v1/gardens/{token}/obstacles
  - PATCH /api/v1/gardens/{token}/obstacles/{obstacle_id}
models:
  - obstacle
test_files:
  - tests/test_footprint.py
  - tests/test_object_kinds.py
data_flow: writes-existing
last_synced: 2026-08-30
status: complete
phase: all
mdd_version: 11
tags: [footprint, geometry, vocabulary, shapes, rotation]
path: Garden/Footprints
integration_contracts:
  - function: footprint_of(obstacle)
    when: anything needs the ground an object covers
    note: one polygon, used by shading, sightlines and drawing alike — three answers to that question is how they drift
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 37 — A House Is Not a Circle

## Purpose

Every object in this garden is currently a cylinder: a position, a radius, a
height. That fits a tree and nothing else. This gives objects a real footprint
and gives the kind vocabulary the properties that make a kind mean something.

## Shape, not raw polygon

An object stores **what shape it is** rather than a bag of points:

| Shape | Stored | Fits |
|---|---|---|
| `circle` | width (= diameter) | a tree crown, a shrub |
| `rect` | width, depth, rotation | a house, a shed, a raised bed, a paving area |
| `polygon` | points in local metres, rotation | anything drawn freehand |

A rectangle is stored as two numbers and an angle rather than four corners
because that is what a resize handle edits. Four corners would have to be
re-derived on every drag, and two of them would eventually disagree.

**A tree stays a circle**, and that is not a compromise: a crown is the one thing
a circle actually fits.

## One footprint function

`footprint_of()` turns any object into a polygon in garden metres. Shading,
sightlines and drawing all call it.

The data-flow analysis found occlusion already computed twice, agreeing only
because both sides assumed a cylinder. **Three answers to "what ground does this
cover" is how they drift**, so there is one.

## The vocabulary gains what a kind actually is

Wave 7 gave each kind a default height. A kind now also carries:

- **default shape and size** — a house is a 10 × 8 m rectangle, a hedge a 6 × 0.6 m
  strip, an oak a 6 m circle;
- **whether it casts a shadow** — paving and gravel do not, a wall does;
- **whether it is a surface** — a lawn is drawn under everything, a shed on top;
- **its drawing symbol**, which feature 41 renders.

The list grows to what a garden contains: `house`, `shed`, `wall`, `fence`,
`hedge`, `tree`, `shrub`, `bed`, `lawn`, `paving`, `gravel`, `pond`, `path`,
`other`.

## Business Rules

- **Rotation is degrees clockwise from north**, matching the compass on the plan
  and the azimuth convention the solar model already uses. A second angular
  convention in the same drawing is a bug waiting for its first rotated house.
- **A surface has no height and casts nothing.** Setting a height on gravel is
  accepted and ignored rather than refused — the user may be describing a raised
  gravel bed, and the shadow model has nothing to do with it either way.
- **Existing gardens are deleted**, as agreed: this is a test deployment, and one
  deliberate reset beats a compatibility path for circle-shaped houses.

## Security

No new user input reaches a query. Points are bounded in number and in extent by
the schema before they are stored.

## Known Issues

- **The map import squares its circles.** Wave 8 fetches `out tags center`, so
  no outline exists to store; a building becomes a rectangle of the same area
  rather than a circle. Closer than before and still not the building. Fetching
  `out geom` is the open research item on the wave.
- **`canopy.py` still speaks in radii** for planted woody species, which is
  right — a crown is a circle — but it means one more place that knows a shape.

## Bugs

(none. Two test fixtures encoded the old approximation and were corrected with
the model rather than against it: a shadow now starts at the wall rather than at
the wall's centre, and a sightline clears a hedge's near edge rather than its
middle — which is what a person actually looks over.)
