---
id: 23-catalogue-filters
title: Filters That Say What They Dropped
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-6
wave_status: complete
depends_on: [21-german-names]
relates: [22-species-info, 24-month-suggestions]
source_files:
  - ninanatur/api/search.py
  - ninanatur/api/planning.py
  - ninanatur/api/schemas.py
  - ninanatur/api/candidates.py
  - ninanatur/api/filters.py
  - frontend/src/components/FilterBar.tsx
  - frontend/src/components/FilterControls.tsx
  - frontend/src/components/SuggestionList.tsx
  - frontend/src/App.tsx
routes:
  - GET /api/v1/gardens/{token}/beds/{bed_id}/suggestions
models: []
test_files:
  - tests/test_search_filters.py
  - tests/test_planning_api.py
  - frontend/src/components/FilterBar.test.tsx
  - frontend/src/components/FilterControls.test.tsx
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [filters, height, colour, growth-form, flowering, coverage, ranking]
path: Search/Filters
integration_contracts:
  - function: rank_plants(candidates, site, filters, colour)
    when: any ranked list of species is produced
    note: filters report what they excluded and why; a filter never silently empties the catalogue
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 23 — Filters That Say What They Dropped

## Purpose

Height, colour, flowering window, growth form and nativeness as filters over the
existing ranking. Most of the machinery already exists in `search.py`; almost
none of it is reachable from the API. This feature exposes it — and fixes what
exposing it would otherwise have shipped.

## The problem this feature actually solves

`SearchFilters` already carries `height_min`, `height_max` and
`flowering_month`. The suggestions route never passes them. So the filters were
written, tested against their own unit tests, and were dead. Two defects sat in
that dead code, and both would have gone live the moment a query parameter
reached them.

### Wrapping flowering intervals

```python
not start <= filters.flowering_month <= end   # False for every wrapping species
```

**132 of 3,560** flowering German species have `start > end` — *Bergenia
crassifolia* flowers 12 → 7. The comparison excludes them from **every** month,
including the months they actually flower. `bloom/timeline.py` has solved this
since Wave 3 with `flowering_months(start, end)`; the filter has to use it
rather than re-implement the comparison and get it wrong.

Measured against the shipped catalogue, per month:

| Month | Before | After | Recovered |
|---|---|---|---|
| Jan | 39 | 171 | +132 |
| Feb | 103 | 229 | +126 |
| Mar | 265 | 385 | +120 |
| Apr | 861 | 982 | +121 |
| May | 1,341 | 1,448 | +107 |
| Jun | 2,115 | 2,219 | +104 |
| Jul | 2,378 | 2,467 | +89 |
| Aug | 1,750 | 1,827 | +77 |
| Sep | 654 | 716 | +62 |
| Oct | 269 | 327 | +58 |
| Nov | 64 | 111 | +47 |
| Dec | 48 | 180 | +132 |

January returned **39 species where 171 flower**, December 48 where 180 do. The
error is worst exactly where the product is most useful — the winter months are
the ones a bloom-gap tool exists to fill.

### Unknown silently dropped

The module's own comment states the rule twice — *"absent data is not a property
of the plant"* — and then the height filter breaks it:

```python
if filters.height_min is not None and (height is None or height < filters.height_min):
    return False
```

Height is recorded for **3,952 of 8,939** German species. Filtering to "under
50 cm" therefore discards **4,987 species** without saying so, and the ones it
discards are not a random sample: coverage correlates with how well-studied a
plant is, so a coverage-blind filter quietly favours the familiar.

## Business Rules

- **A filter excludes known mismatches, never unknowns.** Unknown is a gap in
  the data. Same rule as flower colour, now applied consistently.
- **Unknowns are counted and reported, not merged into the results.** The
  response carries `matched`, `unknown` and `excluded` per active filter. The
  list shows matches; including unknowns is an explicit, removable choice.
  Silently dropping them and silently mixing them in are both dishonest — the
  fix for both is to say the number.
- **Colour ranks, never excludes.** Recorded for 6.6% of the catalogue. As an
  exclusion it would discard 93% of it, including the best forage plants.
- **Flowering windows wrap.** The filter calls `flowering_months`; it does not
  compare integers.
- **Every active filter is visible and removable in the UI**, with its own
  result count. A filter the user cannot see is a filter they cannot distrust.

## Coverage, measured

| Trait | German species | Coverage |
|---|---|---|
| `native_de` | 8,939 | 100% |
| `woodiness` | 4,640 | 51.9% |
| `growth_form` | 4,345 | 48.6% |
| `height_max_m` | 3,952 | 44.2% |
| `flowering_start_month` | 3,671 | 41.1% |
| `flower_colour` | 590 | 6.6% |

These numbers are the reason for the rules above, and they belong in the UI as
well: a filter over a 6.6%-covered trait must not look like a filter over a
100%-covered one.

## API

`GET /gardens/{token}/beds/{bed_id}/suggestions` gains:

| Parameter | Type | Meaning |
|---|---|---|
| `height_min` / `height_max` | float (m) | Known heights outside the range are excluded |
| `flowering_month` | int 1–12 | Wrap-aware |
| `growth_form` | string | `forb`, `graminoid`, `shrub`, `tree`, `subshrub`, `herb` |
| `include_unknown` | bool, default `false` | Include species whose filtered trait is unrecorded |

Response gains a `filters` block reporting, per active filter, how many species
matched, how many were unknown, and how many were excluded.

## Security

Query parameters are typed and bounded by FastAPI. `growth_form` is matched
against a closed set rather than interpolated; no filter value reaches SQL —
filtering happens in Python over an already-loaded candidate set.

## Known Issues

- **GIFT records 0.1 m for *Periploca graeca***, a liana that climbs to 9 m, so
  it appears under "höchstens 0,5 m". Not systematic — 0 of the 204 species
  recorded as `tree` have a height below 1 m — but climbers are evidently
  measured as something other than maximum height. Found by reading the top of
  a filtered list rather than by any test.
- `matched + unknown + excluded` does not sum to the candidate count for
  `colour`, by design: a known mismatch is ranked down rather than removed and
  so belongs to none of the three. The UI derives it if it needs it.

## Bugs

Two, both live in `GET /api/v1/plants` since Wave 2, both fixed here. See
"The problem this feature actually solves" for the measured impact — the
flowering-window comparison was returning 39 species for January where 171
flower.

A third, found in the browser rather than in a test: `.filter-controls__toggle`
lost the specificity contest against `.filter-controls label`, so the "Gehölze
mitzeigen" checkbox rendered above its own text instead of beside it.
