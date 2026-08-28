---
id: 18-insect-score
title: The Insect Score
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-5
wave_status: complete
depends_on: [16-nativeness, 17-insect-groups, 14-bloom-timeline]
relates: [19-swap-suggestions]
source_files:
  - ninanatur/bloom/score.py
  - ninanatur/api/planning.py
  - ninanatur/api/schemas.py
routes:
  - GET /api/v1/gardens/{token}/score
models: []
test_files:
  - tests/test_insect_score.py
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [score, insects, submodular, forage, continuity]
path: Garden/Score
integration_contracts:
  - function: garden_score(conn, garden)
    when: rating a planting or ranking a swap
    note: must stay submodular — the greedy swap search in 19 is only defensible because it is
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 18 — The Insect Score

## Purpose

One number for what a planting is worth to insects, with every part of it
traceable to counted records.

## The shape of the score

Per species, reusing the timeline's weighting so the two never disagree:

```
forage(species) = (1 + sqrt(german_partners)) x origin_factor
```

The square root is deliberate: the difference between 5 and 50 partners matters
far more than between 500 and 545, and raw counts would let one well-studied
plant dominate a whole garden.

`origin_factor` — native `1.0`, unknown `0.85`, introduced `0.5`. A **stated
convention**, like the sun-hour mapping and the soil table: introduced species
are not worthless to insects, and pretending otherwise would be as dishonest as
ignoring origin altogether.

Per month of the growing season:

```
month_value = min( sum of forage flowering that month , MONTH_SATURATION )
score       = 100 x sum(month_value) / (months x MONTH_SATURATION)
```

## Why the saturation, and why it matters downstream

**The `min` is what makes the score submodular.** Adding a species to an already
saturated July gains nothing; adding one to an empty April gains the full amount.
Continuity is therefore not a multiplier bolted on afterwards — it falls out of
the shape of the function.

That property is the entire justification for the greedy swap search in
`19-swap-suggestions`: on a submodular objective, greedy is provably near
optimal. **If a later change breaks submodularity, the swap suggestions stop
being defensible** — which is why a test asserts it directly rather than trusting
the formula to stay this shape.

## Business Rules

- **Every component is reported.** Per-species forage, per-month value, the group
  breakdown, and how many plantings had no interaction data at all. A score a
  user cannot interrogate is decoration, and this one will be trusted more than
  it deserves.
- **A species with no interaction record contributes its base value**, not zero.
  Unknown is not worthless — the rule the whole project runs on.
- **An empty garden scores zero and says so**, rather than being called bad.
- Season months only, as in the timeline. A garden is not penalised for January.

## Known Issues

- The score rests on GloBI's research coverage, which is uneven. *Salix caprea*
  leads partly because willows are well studied. `MONTH_SATURATION` limits how far
  that can distort a single month, but the UI must still say what the number is
  and is not.
- `MONTH_SATURATION` and `ORIGIN_FACTOR` are conventions. They belong in one place
  with their reasoning, and moving them changes every score in the product.

## Verified against real species

Two plantings, same catalogue:

| Garden | Species | Score | Bees counted |
|---|---|---:|---:|
| summer-heavy | Achillea, Origanum, Centaurea | 48.4 | 457 |
| spread | Primula, Salvia, Origanum, Sedum | **65.8** | 247 |

**The spread garden wins with barely half the partner count.** Three summer
powerhouses saturate June to September and leave spring empty; a modest
succession carries April through September. That is the design working, not a
weighting chosen to produce it.

## Bugs

(none yet)
