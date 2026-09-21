---
id: 13-bed-suggestions
title: Plant Suggestions for a Bed
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-4
wave_status: complete
depends_on: [12-planting-model, 06-plants-api]
relates: [03-niche-fit, 15-timeline-ui, 23-catalogue-filters, 25-woody-and-birds, 67-sun-plant-in-a-shade-spot]
source_files:
  - ninanatur/api/suggestions.py
  - ninanatur/api/search.py
  - ninanatur/api/filters.py
  - ninanatur/api/schemas_plants.py
  - ninanatur/garden/light_state.py
  - frontend/src/components/SuggestionList.tsx
  - frontend/src/components/SuggestionLight.tsx
  - frontend/src/garden/useComputeShade.ts
routes:
  - GET /api/v1/gardens/{token}/beds/{bed_id}/suggestions
models: []
test_files:
  - tests/test_bed_suggestions.py
  - tests/test_light_suggestions.py
  - frontend/src/components/SuggestionList.light.test.tsx
  - frontend/src/garden/useComputeShade.test.ts
data_flow: reads-existing
last_synced: 2026-09-21
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
    verified_at: "ninanatur/api/search.py:90"
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
| `limit` | 20 | ≤ 100 (the frontend asks for 50, doc 90) |
| `colour` | — | soft, as everywhere |
| `height_min`, `height_max`, `flowering_month`, `growth_form`, `include_unknown` | — | `23-catalogue-filters` |
| `include_trees` | `true` | woody plants in a shortlist of their own since Wave 6 (`25-woody-and-birds`) |
| `include_introduced` | `false` | the product promises native plants (`16-nativeness`) |
| `exclude_planted` | `true` | already in the bed, so not a suggestion |
| `include_light_unsuitable` | `false` | see "The light" below |

The bed's own `ellenberg_l/m/n/r` become the site vector. A bed with no computed
light is still usable — the axes it has are scored, which is the `03-niche-fit`
rule — and the response says so in `light_state`, below. Until 2026-09-21 it
said so only in `site_axes`, which the frontend never read: the list claimed
"gewertet nach den Standortwerten dieses Beetes" for a ranking on soil alone.

## The light (owner review #9, 2026-09-21)

The owner asked whether suggestions follow the sun calculation, since
half-shade plants should not go in full sun. They did rank by it, but a light
mismatch only lowered a species' score, so narrow filters brought shade plants
back up. Three changes:

- **Too bright is refused, too dark is priced.** A species whose L band is
  *unsuitable* (more than 1.5 niche half-widths away, `03-niche-fit`) *and*
  whose L is below the bed's is left out. A shade plant in full sun scorches
  and dries out, which is usually fatal; a sun plant in shade lives, flowers
  less and gets leggy, so it stays in and the geometric mean ranks it down. A
  species with no L value stays, whatever `include_unknown` says: a gap in the
  data is not a mismatch. The cut is counted under the filter-report key
  `light` (`excluded`: left out; `unknown`: kept without an L value), and the
  list says "N Arten, denen es hier zu hell ist, sind ausgeblendet".
  `include_light_unsuitable=true` shows them, ranked last; FilterControls
  offers it as "auch Arten zeigen, denen das Licht zu hell ist". The planting
  improvements (`19-swap-suggestions`) apply the same cut; the catalogue
  search, `GET /plants`, does not.
- **The woody shortlist takes only what the light suits,** in either direction,
  before it is ordered by animal value. Ranking down means nothing in a list
  ordered by partners: it once gave a full-sun bed, a semi-shade bed and a bed
  with no light the same eight willows.
- **`light_state`: `missing`, `stale` or `current`.** Missing: the bed has no
  light value — drawn after the last press of the button, since nothing
  computes light on a write (`lighting.py`). Stale: the stored sun map's
  signature no longer matches the garden's — the comparison the map's own
  `stale` flag makes (`api/light.py::_read`, which spells the same two lines
  out rather than calling `light_state.current_signature`; see Known Issues).
  Also stale when there is no stored map to say what the value was computed
  from. Measured on 2026-09-21 at about 4 ms per request
  (a real 200 × 200 terrain window, 40 houses, 20 beds of 10 plantings),
  nearly all of it decoding the terrain window. A cheaper timestamp test was
  not available: `garden.updated_at` is not touched when an element moves.
  The list replaces "gewertet nach den Standortwerten" with the reason and a
  „Schatten berechnen“ button — the sun panel's rebuild, then the list and
  the garden re-read once the new map has arrived. Light is **not** computed
  inside the suggestion request: that costs seconds on a big garden.

The signature counts every planting, so the list turns stale after every
planting — as the sun map already does (see Known Issues). Two things the
owner still has to decide are left alone: the hours→L table sits on
classic-looking rungs (3–8) against EIVE's 0–10 species values, and a bed's
light is the mean over its cells, which a bed half in sun and half in shade
does not have anywhere.

## Growth form (the Wave 4 rule, since inverted)

A shady damp bed currently returns *Tsuga canadensis* — a hemlock tree — ahead of
the woodland sedges. Correct fit, useless suggestion. Noted as a known issue in
`06-plants-api` and fixed here, where a bed has a size to judge against.

Wave 4 excluded trees and shrubs unless `include_trees=true`. Wave 6 inverted
it: the catalogue's best forage plants are woody, so they are in by default,
in a shortlist of their own beside the main list (`25-woody-and-birds`), and
`include_trees=false` removes them.

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
- The bed's own area was not used, until Wave 6: the room check (`space`) now
  ranks each plant against it (`23-catalogue-filters`).
- **The light cut sits on an unsettled scale.** See "The light": the hours→L
  rungs and the mean over a bed's cells decide which species are too bright,
  and both wait for the owner.
- **Planting a perennial makes the light "stale".** `lightgrid.signature_of`
  hashes every planting, though only woody ones cast shade
  (`lightview._planted_obstacles`). So after planting a Salbei from the list,
  the list and the sun map both say the shade is out of date when it cannot
  be. Hashing only the plantings that shade would end the false alarm in both
  (every stored map would turn stale once); `lightgrid.py` was out of reach
  for this change.
- **Two copies of "the current signature".** `api/light.py::_read` should call
  `light_state.current_signature` instead of repeating it, so the map and the
  list cannot drift apart. Left for now: that file is over the length limit
  and was being changed in parallel on 2026-09-21.

## Bugs

- **2026-09-21 — "Gehölze ausblenden" never reached the server.** Wave 6 made
  `include_trees` default to true, and the client went on sending only `true`,
  so switching woody plants off changed the header's sentence and not the list.
  The client now sends `include_trees=false`.
