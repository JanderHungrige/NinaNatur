---
id: 24-month-suggestions
title: From Seeing a Gap to Filling It
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-6
wave_status: complete
depends_on: [23-catalogue-filters]
relates: [15-timeline-ui, 19-swap-suggestions]
source_files:
  - frontend/src/components/BloomTimeline.tsx
  - frontend/src/components/SuggestionList.tsx
  - frontend/src/App.tsx
  - frontend/src/plural.ts
routes: []
models: []
test_files:
  - frontend/src/components/BloomTimeline.test.tsx
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [timeline, month, gap, suggestions, filter]
path: Bloom/MonthSuggestions
integration_contracts:
  - function: FilterBar / SuggestionFilters.floweringMonth
    when: a month is selected in the bloom year
    note: the month filter is the same one the filter bar shows and can remove — one filter, two ways in
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 24 — From Seeing a Gap to Filling It

## Purpose

Clicking a month in the bloom year restricts suggestions to species flowering
then. This is the shortest path from *seeing a gap* to *fixing it*, and it is
the reason the timeline exists at all.

Until now the timeline could tell a user that April is empty and offer them no
way to act on it. The suggestion list sat directly below, ranked by site fit and
completely indifferent to the month they had just been told about.

## The design decision: one filter, two ways in

A month click does **not** introduce a second, parallel notion of "the selected
month". It sets `floweringMonth` — the same filter Wave 6 feature 3 already
added, shown by the same chip, removable by the same button.

The alternative, a separate `selectedMonth` piece of state that the suggestion
query also consults, is how two sources of truth get created: the chip would say
one thing and the timeline another as soon as either could be cleared
independently. There is one month filter, and the timeline is a second way to
set it.

## Business Rules

- **Clicking a month sets the flowering filter; clicking it again clears it.**
  A toggle, because the same click that expresses "show me April" is the one a
  user reaches for to undo it.
- **The selected month is marked in the timeline**, not only in the filter bar.
  The user clicked there, so that is where they look for confirmation.
- **A gap month is the interesting click**, and is styled to invite it. Gaps are
  already marked; making them the obvious target costs nothing.
- **Wrapping intervals are honoured**, because the filter is the one fixed in
  feature 3 — a November-to-March species belongs in the March list, and is
  reachable by clicking March.
- **Months outside the season are still clickable.** The gap analysis runs
  March–October, but a user asking what flowers in December is asking a real
  question and now gets 180 answers rather than 48.

## Accessibility

The month cell becomes a real `button` inside the table row, not a click handler
on a `tr`. It carries an `aria-pressed` state so the selection is announced,
and the label names the month in full rather than the abbreviation the column
shows.

## Known Issues

(none yet)

## Bugs

None new. One pre-existing wart cleaned up while working here: the coverage
note read "Für 3 Pflanzung(en)" — the parenthetical dodge around the German
plural bug this project has now hit three times. `plural.ts` gained
`plantings()` and the timeline uses it.
