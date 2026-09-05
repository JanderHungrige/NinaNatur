---
id: 65-the-shade-switch
title: The Shade Switch, and a Day Watched Through
edition: MDD
initiative: ninanatur
depends_on: [64-light-across-the-bed]
relates: [64-light-across-the-bed, 67-sun-plant-in-a-shade-spot]
source_files:
  - frontend/src/components/ShadeSwitch.tsx
  - frontend/src/components/SunMap.tsx
  - frontend/src/components/CanvasScene.tsx
  - ninanatur/solar/day.py
  - ninanatur/api/light.py
routes:
  - GET /api/v1/gardens/{token}/light
  - GET /api/v1/gardens/{token}/shadows
models: [light_grid]
test_files:
  - frontend/src/components/ShadeSwitch.test.tsx
  - tests/test_light_api.py
data_flow: reads-existing
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [shading, ui, heatmap, animation, contrast]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# The Shade Switch, and a Day Watched Through

## The switch

One toggle over the plan, and two ways to read the same grid. **Sonnenstunden**
darkens what has little sun; **Schattenstunden** darkens what has much. They are
the same numbers inverted, and both exist because gardeners ask the question in
both directions: *where can this sun-lover go* and *what do I do with that dark
corner*.

The legend is banded and every band carries its hours, because "Halbschatten" is
a word people use for different things and 2.5–4 h is not:

| Band | Hours |
|------|-------|
| volle Sonne | ab 6 h |
| sonnig | 4–6 h |
| Halbschatten | 2.5–4 h |
| Schatten | 1.5–2.5 h |
| tiefer Schatten | 0–1.5 h |

Cells scale against the garden's own brightest cell rather than an absolute, so
a shaded courtyard still shows its structure instead of going uniformly black.

### The colour took three tries

The first wash was near-black, which measures 1.09 contrast against the dark
theme's `#12160f` — invisible. Two more candidates landed at 1.02 and 1.22. What
works is a *lighter* cool grey (`#5b6c80`, 2.36): on a dark page shade has to be
drawn with light, not with more dark.

## The day

`GET .../shadows?month=` returns the shadows of one middling day — the 15th, at
every half hour the sun is above 5°. The play button walks the plan through it.

Computed rather than stored: one day is a fraction of a season's work, and
nobody watches the same day twice in a row.

The 15th rather than the 1st or the 31st because a month's edges differ by a
fortnight of sun, and the middle is the one that represents the month.

## A thing that had to be learned twice

The map was fetched in `refresh` only — and a garden opened from its share link
never goes through `refresh`. That function already carried a comment warning
about exactly this, written after the last feature it happened to. The comment
now names its second victim.
