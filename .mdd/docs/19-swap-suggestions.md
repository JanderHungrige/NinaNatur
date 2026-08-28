---
id: 19-swap-suggestions
title: What to Change to Raise the Score
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-5
wave_status: complete
depends_on: [18-insect-score, 13-bed-suggestions]
relates: [20-score-ui]
source_files:
  - ninanatur/bloom/improve.py
  - ninanatur/bloom/score.py
  - ninanatur/api/planning.py
  - ninanatur/api/schemas.py
routes:
  - GET /api/v1/gardens/{token}/improvements
models: []
test_files:
  - tests/test_improvements.py
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [swaps, greedy, submodular, marginal-gain, explanations]
path: Garden/Improve
integration_contracts: []
satisfies_contracts:
  - from: 18-insect-score
    function: garden_score(conn, garden)
    when: ranking any proposed change
    status: done
    verified_at: "ninanatur/bloom/improve.py:113"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 19 — What to Change to Raise the Score

## Purpose

A score without an action is a verdict. This turns it into "plant this instead of
that, and here is what it buys you".

## Two kinds of change

- **Additions** — a species to add, ranked by what it gains.
- **Swaps** — replace an existing planting with a better-suited one. This is the
  case a gardener with a full bed actually has.

Both are ranked by **marginal gain**: the score with the change, minus the score
now.

## Why greedy is allowed here

`18-insect-score` is submodular, and a test pins it. On a submodular objective a
greedy search is provably near optimal, so ranking single changes by their
individual gain is a defensible way to improve a planting — not merely a cheap one.

**If the score ever stops being submodular, this feature stops being justified.**
The dependency is stated here so a future change to `MONTH_SATURATION` or the
per-month shape is understood to reach this far.

## Computing the gain without rescoring the garden

Scoring the whole garden per candidate would mean thousands of walks over every
planting and several queries each. Instead the garden's **uncapped** per-month
forage is computed once, and a candidate's gain is:

```
gain = sum over its flowering months of
       min(current[m] + forage, SATURATION) - min(current[m], SATURATION)
```

O(months) per candidate instead of O(garden). The cap is what makes a candidate
worth nothing in an already-full month — the same property, arrived at directly.

## Explanations

Every suggestion carries one sentence, because the number does not tell anyone
what to do:

- gain concentrated in gap months → *"schließt die Lücke im April"*
- otherwise → *"bringt 40 Wildbienenarten mehr"*

The sentence names the reason the score moved, not the amount it moved by.

## Business Rules

- **Only species that fit the bed are proposed.** A swap that raises the score and
  kills the plant is not an improvement — candidates come through the same fit
  and nativeness filters as `13-bed-suggestions`.
- **A swap must beat leaving things alone.** Suggestions with a gain of zero or
  less are not shown; padding the list would train users to ignore it.
- **Species already planted are never proposed for the same bed.**
- The gain is reported alongside the resulting score, so a user can see both what
  changes and where it lands.

## Known Issues

- **A swap will happily remove a valuable plant from a saturated month.** Against
  the real catalogue, a garden of *Achillea millefolium* and *Origanum vulgare*
  is told to replace the Achillea — 959 German partners — with *Bellis perennis*,
  for +30.8. The model is right by its own rules: Achillea's July is already
  saturated by the Origanum, so its marginal value there is nil, while the daisy
  fills an empty spring.

  As garden advice it is questionable, and the UI should present **additions as
  the primary suggestion and swaps as the answer to "my bed is full"** — which is
  the only situation where removing something is actually the choice being made.

- A minimum fit threshold guards the candidate pool, but the pool is still a
  fixed 60 per bed. A garden with many beds does 60 evaluations each.

## Verified against the real catalogue

A garden of *Achillea millefolium* and *Origanum vulgare* — both summer — scores
35.9. The top additions are all spring bloomers, each naming the gap it closes:

| Gain | Species | Reason |
|---:|---|---|
| +34.1 | *Bellis perennis* | schließt die Lücke im April und Mai |
| +25.0 | *Ranunculus acris* | schließt die Lücke im Mai und Juni |
| +19.7 | *Cochlearia officinalis* | schließt die Lücke im März und April |

0.56 s over 2,549 candidates.

## Bugs

(none yet)
