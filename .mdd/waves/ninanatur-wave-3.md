---
id: ninanatur-wave-3
title: "Wave 3: The garden as a floor plan"
initiative: ninanatur
initiative_version: 2
status: planned
depends_on: ninanatur-wave-2
demo_state: "A user draws beds on a garden floor plan, sets each bed's conditions, and the plan persists"
created: 2026-08-27
hash: 0bfea88a
---

# Wave 3 — The garden as a floor plan

## Scope

**In:**
- Garden canvas: draw and edit bed polygons, set scale
- Per-bed properties: orientation, shading obstacles, soil type, moisture
- Derive each bed's site-condition vector from those inputs, so the user answers
  gardener questions ("north wall, heavy clay") rather than ecologist questions
- Persistence: save, load, and share a plan

## Key decisions

- **Sun hours from geometry.** Orientation plus obstacle heights can be computed
  into a light value, or the user can simply pick "sunny/partial/shade". The
  computed route is better and much more work — decide before building the editor.
- **Sun hours** remains open (see below).

Persistence is settled: shareable unguessable link, no accounts. **The plan table
carries a nullable `owner_id` from the very first migration** — adding it later
means migrating live plans, adding it now costs one column that stays empty until
accounts exist.

## Definition of done

A user draws a garden, defines beds, reloads the page, and everything is still
there — with each bed carrying the site vector Wave 4 will match against.
