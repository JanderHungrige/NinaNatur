---
id: ninanatur-wave-3
title: "Wave 3: The garden as a floor plan"
initiative: ninanatur
initiative_version: 4
status: planned
depends_on: ninanatur-wave-2
demo_state: "A user draws beds on a garden plan, places obstacles, and each bed gets a computed light value from the real sun path — reload the page and it is all still there"
created: 2026-08-27
hash: def3f120
---

# Wave 3 — The garden as a floor plan

## Demo-State

A user draws beds on a garden plan, places obstacles, and each bed gets a
computed light value from the real sun path — reload the page and it is all
still there.

*(Not complete until this can be demonstrated against the running app.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | solar-geometry | .mdd/docs/07-solar-geometry.md | complete | — |
| 2 | garden-model | .mdd/docs/08-garden-model.md | complete | — |
| 3 | garden-api | 09-garden-api | planned | 07, 08 |
| 4 | web-client | 10-web-client | planned | 09 |
| 5 | garden-canvas | 11-garden-canvas | planned | 10 |

### 1 — solar-geometry

Sun altitude and azimuth for a location and moment (NOAA solar position
algorithm — pure arithmetic, no dependency, no network), then shadow casting from
obstacles onto beds, sampled across the growing season to give direct-sun hours
per bed.

**The mapping to Ellenberg L is the honest weak point** and must be written down
as a table with its reasoning, not buried in a formula. Sun hours are a physical
quantity; Ellenberg L is an ecological indicator derived from where plants are
found growing. The conversion is a convention, so it belongs in one documented
place where it can be argued with and adjusted — not spread across the code.

**Location is rounded to 0.1°** (~11 km) before storage. Solar angles vary
negligibly over that distance, so the precision is worthless to the computation
and the coarser value is meaningfully less personal.

*Later:* the 3dmap project (`/opt/3dmap2`) has height-profile logic that could
replace hand-placed obstacle heights with real terrain. Deliberately out of scope
here — get the sun path right against simple obstacles first.

### 2 — garden-model

Schema for gardens, beds and obstacles, and persistence.

- **`owner_id` is nullable and present from this first migration.** Accounts are
  not being built (initiative decision), but adding the column later would mean
  migrating live plans. It costs one empty column now.
- Access is by unguessable share token, not by login. The token is the capability
  — anyone holding it can edit — so it must be generated with `secrets`, never
  from a sequence or a timestamp.
- Beds store their polygon, their derived site vector, and the inputs it came
  from, so a light value can always be traced back to the obstacles that produced
  it rather than appearing as an unexplained number.

### 3 — garden-api

CRUD under `/api/v1/gardens`, plus recomputing a garden's light values when its
obstacles change. Same rules as Wave 2: validation failures are 422, unknown is
`null` with a reason, `/healthz` still touches nothing.

### 4 — web-client

The typed frontend/backend contract deferred from Wave 2. Types generated from
FastAPI's OpenAPI schema rather than hand-written, so the two cannot drift.

### 5 — garden-canvas

React + TypeScript (Vite), strict, no `any`. Draw and edit bed polygons, set
scale, place obstacles with heights, edit soil and moisture per bed.

Soil is entered the way a gardener thinks — sand / loam / clay / humus, and dry /
fresh / moist / wet — and mapped to the M, N and R axes behind the scenes. The
user is never asked for an Ellenberg value.

## Risks

- **The Dockerfile gains a Node build stage.** Wave 1's image is Python only.
  This is the first change to a deployment path that currently works, and it is
  worth verifying in CI before assuming it still builds — there is no Docker on
  the dev machine to check locally.
- **Canvas interaction is where accessibility usually dies.** Every drawing
  action needs a keyboard path and every bed an accessible name, decided while
  building rather than retrofitted.
- **Sun-hour computation over many samples can get slow.** Compute on save, store
  the result, and recompute only when obstacles or location change — not per
  request.

## Open Research

None blocking. The light-derivation question is settled: real solar position.

## Definition of done

A user opens the app, sets a location, draws beds, places a wall and a tree,
sees each bed's light value change accordingly, reloads, and finds everything
intact — with the Wave 2 plant suggestions responding to the computed values.
