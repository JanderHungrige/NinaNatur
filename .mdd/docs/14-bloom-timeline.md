---
id: 14-bloom-timeline
title: Bloom Timeline and Forage Gaps
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-4
wave_status: complete
depends_on: [12-planting-model, 05-insect-checklist-de]
relates: [15-timeline-ui]
source_files:
  - ninanatur/bloom/__init__.py
  - ninanatur/bloom/timeline.py
  - ninanatur/api/gardens.py
  - ninanatur/api/schemas.py
routes:
  - GET /api/v1/gardens/{token}/timeline
models: []
test_files:
  - tests/test_bloom_timeline.py
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [timeline, phenology, gaps, forage, insects]
path: Garden/Timeline
integration_contracts:
  - function: garden_timeline(conn, garden, mode)
    when: showing the bloom year or detecting gaps
    note: months, never half-months — the source data is integer month bounds
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 14 — Bloom Timeline and Forage Gaps

## Purpose

Twelve months of the garden's flowering, per bed and in total, with the months
that fall short marked as gaps.

## Months, not half-months

Measured before designing: every `flowering_start_month` in the catalogue is an
integer. Half-month buckets would be the same invented precision this project
refuses for flower colour and for sun hours. Twelve buckets, no more.

## Wrapping intervals

**132 species have a start month after their end month** — November to February
and similar. `range(start, end + 1)` yields nothing for exactly those, which are
the species covering the hardest part of the year. The interval expansion handles
the wrap explicitly and a test pins it, because the failure is silent: a species
simply never appears, and the timeline looks plausible.

## Two weightings, one computation

| Mode | A month's coverage counts | Default |
|---|---|---|
| **forage** | plantings weighted by their counted German insect partners | ✅ |
| **visual** | plantings counted equally | |

The user switches with a checkbox. Forage is the default because it is the point
of the product: a month full of nectarless double-flowered cultivars is correctly
a gap, and only the weighted view can say so.

A species with **no interaction data** contributes its plain quantity in forage
mode rather than zero. Unknown is not the same as worthless — the rule this whole
project runs on. The response reports how many plantings that applied to, so a
timeline built mostly on unknowns is visible rather than merely optimistic.

## Gaps

A gap is a run of consecutive months **within March–October** whose coverage is
below `GAP_THRESHOLD` — a documented constant with its reasoning beside it, like
the sun-hour mapping.

The winter trough is not a finding, so the season bounds the search. Reporting
"nothing flowers in January" as a problem would train users to ignore the feature.

## Business Rules

- **An empty garden yields an empty timeline, not twelve zero-coverage gaps.**
  A plan with nothing planted has no gaps; it has nothing.
- **Every month reports which species contributed**, so a gap can explain itself.
- Coverage is relative to the garden's own best month, so the numbers mean
  "compared to your peak" rather than an absolute nobody can interpret.

## Known Issues

- Coverage counts plantings and quantities, not area. Three plants of one species
  weigh the same as three of another regardless of how much ground they cover.
  Area per planting would need a size-per-species figure the catalogue lacks.
- `GAP_THRESHOLD` is a judgement call, like the sun-hour mapping. Relative to the
  garden's own peak, so a uniformly sparse garden reports no gaps at all — which
  is arguably right (nothing stands out) and arguably wrong (everything is thin).

## Verified against real species

A deliberately summer-heavy planting — Achillea millefolium, Salvia pratensis,
Origanum vulgare, Centaurea jacea — produces genuinely different answers in the
two modes:

| Mode | Gaps |
|---|---|
| forage | March-May, September-October |
| visual | March-April, October |

May holds only *Salvia pratensis* (214 German partners). Against a July peak of
Achillea, Origanum and Centaurea together (959 + 431 + 643), that is a quarter of
the flowering but far less of the forage — so the weighted view flags it and a
plain bloom count does not. That difference is the reason the feature exists.

## Bugs

(none yet)
