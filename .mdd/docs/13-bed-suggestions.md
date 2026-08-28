---
id: 13-bed-suggestions
title: Plant Suggestions for a Bed
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-4
wave_status: complete
depends_on: [12-planting-model, 06-plants-api]
relates: [03-niche-fit, 15-timeline-ui]
source_files:
  - ninanatur/api/gardens.py
  - ninanatur/api/search.py
  - ninanatur/api/schemas.py
routes:
  - GET /api/v1/gardens/{token}/beds/{bed_id}/suggestions
models: []
test_files:
  - tests/test_bed_suggestions.py
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [suggestions, fit, growth-form, api, gardens]
path: API/Suggestions
integration_contracts: []
satisfies_contracts:
  - from: 03-niche-fit
    function: score_species(site, species)
    when: ranking suggestions for a bed
    status: done
    verified_at: "ninanatur/api/search.py:150"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 13 — Plant Suggestions for a Bed

## Purpose

Run the Wave 2 plant search against a bed's own derived site vector, so the user
never types an Ellenberg number.

**This closes a gap that has been open since Wave 2.** The search endpoint exists
and the typed client method exists, and nothing has ever called either. It is the
smallest step to the first genuinely useful moment in the product.

## Endpoint

`GET /api/v1/gardens/{token}/beds/{bed_id}/suggestions`

| Parameter | Default | Notes |
|---|---|---|
| `limit` | 20 | ≤ 100 |
| `colour` | — | soft, as everywhere |
| `include_trees` | `false` | see below |
| `exclude_planted` | `true` | already in the bed, so not a suggestion |

The bed's own `ellenberg_l/m/n/r` become the site vector. A bed with no computed
light is still usable — the axes it has are scored and the response names them,
which is the `03-niche-fit` rule, not a special case here.

## Growth form is filtered by default

A shady damp bed currently returns *Tsuga canadensis* — a hemlock tree — ahead of
the woodland sedges. Correct fit, useless suggestion. Noted as a known issue in
`06-plants-api` and fixed here, where a bed has a size to judge against.

Trees and shrubs are excluded unless `include_trees=true`. **Excluded, not
down-ranked**: someone planning a 3 m² bed does not want a hemlock at rank 40
either. The flag exists because a large garden legitimately wants them.

Species whose growth form is unrecorded are **kept**. Absent data is not a
property of the plant — the same rule that keeps flower colour a soft filter.

## Business Rules

- **Already-planted species are excluded by default.** Suggesting what is already
  in the bed wastes the list; `exclude_planted=false` is there for comparison.
- **The bed must belong to the token's garden**, or 404. A bed id is not a
  capability.
- **Every suggestion carries its fit explanation**, so the UI can say *why*
  without recomputing.

## Known Issues

- **Climbers slip through.** Growth form only marks `tree` and `shrub`, so
  *Vitis riparia* — a liana — still appears for a shady damp bed. GIFT carries a
  separate `Climber_1` trait that is not ingested; adding it would close this.
- The bed's own polygon area is not used. A 1 m² bed and a 40 m² bed get the same
  suggestions, when the larger one could reasonably include a shrub without the
  flag.

## Bugs

(none yet)
