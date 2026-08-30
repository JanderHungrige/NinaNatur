---
id: 34-sightlines
title: What You Can Actually See From Where You Stand
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-9
wave_status: complete
depends_on: [27-object-labelling]
relates: [12-bed-light, 32-object-heights]
source_files:
  - ninanatur/garden/sightlines.py
  - ninanatur/api/planning.py
  - ninanatur/ingest/db.py
  - frontend/src/components/Sightlines.tsx
  - frontend/src/components/CanvasScene.tsx
routes:
  - POST /api/v1/gardens/{token}/sightlines
models:
  - obstacle
test_files:
  - tests/test_sightlines.py
  - tests/test_sightlines_api.py
  - frontend/src/components/Sightlines.test.tsx
data_flow: reads-existing
last_synced: 2026-08-30
status: complete
phase: all
mdd_version: 11
tags: [sightlines, visibility, geometry, provenance, raised-bed]
path: Garden/Sightlines
integration_contracts:
  - function: visibility(eye, target, blockers)
    when: a viewpoint is placed on the plan
    note: an answer resting on an estimated height says so — the same rule as a filter reporting what it dropped
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 34 — What You Can Actually See From Where You Stand

## Purpose

Place a viewpoint and get an answer instead of a guess. "Will I actually see
this plant" is the question that decides where things go.

The same cylinders the shading model already uses, seen from an eye rather than
from the sun — so a hedge blocks sight exactly as it blocks light, and Wave 7's
`height_above_ground` per bed raises a bed above both.

## More than a yes or no

The answer carries **from what height** the target would clear everything in the
way: *"verdeckt — sichtbar ab 2,3 m"*. That is the sentence a person can act on,
because it names the plant that would work there.

## Confidence travels

Wave 8 places buildings whose heights are mostly assumed — zero of 4,912
suburban buildings carry an OSM `height`. **A sightline computed from a guessed
height must not be drawn as though it were surveyed**, so `obstacle` gained a
`height_source` column and an answer says when it rests on one.

Wave 8 reported that provenance in its creation response and then threw it away.
This is where it had to be stored, and correcting a height in the object editor
now makes it the user's word on it rather than leaving every sightline through
it marked as an assumption.

## Business Rules

- **Only blockers that actually block affect the confidence.** An estimated
  height nowhere near the line of sight must not make a certain answer look
  uncertain.
- **Standing inside something is not standing behind it** — you are under the
  tree.
- **A plant with no recorded height gets no answer**, not a guessed one. Height
  is recorded for 44% of the catalogue.
- **The tallest blocker is the one named**, since that is the one to move.

## Known Issues

- **A bed is a point.** Visibility is computed from the bed's centroid, so a long
  border is either visible or not rather than partly. Wave 7's plantings have no
  position within their bed, which is the same gap that keeps a planted tree from
  shading its own bed.
- **A target inside a blocker is treated as visible.** A bed under a hedge's
  canopy is a case the cylinder model cannot express well either way.

## Bugs

(none. Two test fixtures were wrong and the code was right: a "tall" perennial
of 2.4 m behind a 2 m hedge 4 m from the eye, which correctly needs 2.6 m; and a
browser check where a radius-4 hedge swallowed the bed it was meant to hide.)
