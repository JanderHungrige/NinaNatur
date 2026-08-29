---
id: 27-object-labelling
title: Saying What a Thing Is
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-7
wave_status: complete
depends_on: [26-drawing-canvas]
relates: [28-existing-plantings, 12-bed-light]
source_files:
  - ninanatur/ingest/db.py
  - ninanatur/garden/objects.py
  - ninanatur/garden/store.py
  - ninanatur/solar/light.py
  - ninanatur/solar/shading.py
  - ninanatur/api/schemas.py
  - ninanatur/api/gardens.py
  - frontend/src/components/ObjectEditor.tsx
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/App.tsx
routes:
  - PATCH /api/v1/gardens/{token}/obstacles/{obstacle_id}
  - PATCH /api/v1/gardens/{token}/beds/{bed_id}
models:
  - obstacle
  - bed
test_files:
  - tests/test_object_kinds.py
  - tests/test_raised_beds.py
  - tests/test_object_editing.py
  - frontend/src/components/ObjectEditor.test.tsx
data_flow: writes-existing
last_synced: 2026-08-29
status: complete
phase: all
mdd_version: 11
tags: [vocabulary, labelling, obstacles, raised-bed, shading, height]
path: Garden/Objects
integration_contracts:
  - function: bed_light_value(location, point, obstacles, height_above_ground)
    when: a bed's light is computed
    note: a raised bed stands above low obstacles; ignoring its height overstates their shade
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 27 — Saying What a Thing Is

## Purpose

Feature 1 draws shapes. This says what they are: a kind from a fixed vocabulary,
a free label, and the heights that make the shading model mean something.

## The vocabulary has to do work

A dropdown that only decorates is a form field asking a user to do our
bookkeeping. Each kind therefore carries the numbers that make it a thing:

| Kind | Default height | Casts shade |
|---|---|---|
| `tree` | 8 m | yes |
| `hedge` | 2 m | yes |
| `shrub` | 1.5 m | yes |
| `building` | 6 m | yes |
| `wall` | 2 m | yes |
| `fence` | 1.2 m | yes |
| `other` | — | yes, if a height is given |

Defaults are offered, never imposed: a user who types 4 m for their hedge has a
4 m hedge. The kind picks the starting number and the icon; the user owns the
value.

The **label** is free text and drives nothing. "Die Buche vom Nachbarn" is worth
storing and is not a category.

## Raised beds — where the height actually pays off

A bed 80 cm above the ground stands above a 1.2 m fence. The shading model
compares a shadow's reach to a point on the ground, so it currently shades a
raised bed exactly as hard as a border, which is wrong in the direction that
matters: it makes the sunniest beds in a small garden look shaded.

`bed.height_above_ground` therefore enters the light computation. An obstacle
shades a bed by its height **above that bed**, so a 1.2 m fence casts nothing
onto a 1.3 m raised bed.

Wave 9's sightlines need the same number, which is why it is stored rather than
derived.

## Scope: circles now, polygons later

An obstacle is a vertical cylinder. That fits a tree and approximates a shrub;
it is a poor model of a building or a straight hedge, both of which want a
footprint. Giving them one means polygon shadow casting, which is a piece of
geometry in its own right and not something to smuggle into a labelling feature.

So buildings and hedges are labelled and sized here, and still shade as
cylinders. Recorded under Known Issues, with the consequence stated: a long
hedge is currently modelled by the circle that contains it, which overstates its
shade at the ends.

## Business Rules

- **The kind is a closed set**, validated server-side. A free string means the
  shading table silently misses a value and no one finds out.
- **A default is a starting value, not a constraint.** Changing the kind of an
  object whose height the user already set does not overwrite it.
- **Editing is reachable both ways**: clicking the object on the plan, and from
  the list. The canvas is the pointer path, not the only path.
- **Height above ground defaults to 0** and every existing bed keeps that, so no
  stored light value changes meaning under the migration.

## Security

`kind` is validated against the enum by FastAPI before it reaches any query.
Labels are stored parameterised and rendered as text — they are user content,
and the same rule as the Wikipedia extract applies.

## Known Issues

- **A hedge or building still shades as a circle.** The cylinder that contains a
  long hedge overstates its shade at the ends. Polygon shadow casting is its own
  piece of geometry and is not smuggled into a labelling feature; the kinds and
  their heights are stored correctly for when it arrives.
- **Obstacles are still placed through the form**, not drawn on the plan. Feature
  1 draws bed polygons; placing a point obstacle by clicking is the same
  machinery and was left out to keep that feature to one shape.

## Bugs

None new. Two shapes of trouble were avoided by writing the tests first: the
`is_shaded` change defaults `height_above_ground` to 0, so a test asserts a
ground-level bed behaves *exactly* as before and the migration cannot change the
meaning of a stored light value.

One thing repeated from Wave 6 and is worth naming as a pattern rather than a
bug: giving a Pydantic response field a default (`height_above_ground: float =
0.0`) makes it optional in the generated OpenAPI, and the TypeScript client then
sees an optional property that `exactOptionalPropertyTypes` refuses. Response
fields the server always sends must be declared required. This is the second
time — `bird_partners` was the first.
