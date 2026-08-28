---
id: 20-score-ui
title: The Score, Made Arguable
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-5
wave_status: complete
depends_on: [18-insect-score, 19-swap-suggestions]
relates: [15-timeline-ui]
source_files:
  - frontend/src/components/InsectScore.tsx
  - frontend/src/plural.ts
  - frontend/src/App.tsx
  - frontend/src/styles.css
  - ninanatur/api/planning.py
  - ninanatur/api/schemas.py
routes:
  - GET /api/v1/gardens/{token}/score
  - GET /api/v1/gardens/{token}/improvements
models: []
test_files:
  - frontend/src/components/InsectScore.test.tsx
  - tests/test_gardens_api.py
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [react, score, suggestions, accessibility, plurals]
path: Frontend/Score
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Applying a swap is not wired — swaps are shown with their gain but only additions have a button. Removing a planting from the UI is missing generally (noted in 15-timeline-ui)."
sister_projects: []
---

# 20 — The Score, Made Arguable

## Purpose

Show the number, and everything needed to disagree with it.

## What the panel shows

- The score **with its scale** — `12 von 100`, never a bare number.
- The group breakdown, which is what turns a count into an argument:
  *54 Wildbienenarten, 10 Schmetterlingsarten*.
- Every contributing species with its partner count and origin, so a reader can
  find the one carrying the score.
- What would gain the most, each naming the gap it closes.

## Two deliberate choices

**Additions lead, swaps hide behind a disclosure.** A swap removes something, and
the score will happily recommend removing a well-connected plant whose month is
already saturated (see the known issue in `19-swap-suggestions`). The disclosure
carries that caveat in words rather than leaving the user to discover it.

**Improvements load with the garden, not on bed selection.** They are the point
of the score; requiring a click to reveal them buries the feature.

## Known Issues

- Applying a swap is not wired. Swaps show their gain, but only additions have a
  button — removing a planting has no UI at all yet.

## Verified in the running app

Planted *Eryngium alpinum* into a sunny bed: score 12/100, broken down as 54
Wildbienenarten / 10 Schmetterlingsarten / 1 Schwebfliegenart, with the species
listed at 75 partners and "Herkunft unbekannt". Suggestions: *Matricaria
chamomilla* +45, closing May and June.

Two things the run caught. `1 Schwebfliegenarten` was the same plural bug as
`1 Beete` in Wave 3 — the helper existed and was not used. And the verification
itself was briefly worthless: Vite HMR could not connect in the browser pane, so
the page was running a stale bundle and the score panel appeared to be missing.
The WebSocket errors were dismissed as irrelevant before being recognised as the
cause.
