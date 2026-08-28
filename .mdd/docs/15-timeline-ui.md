---
id: 15-timeline-ui
title: Timeline and Suggestions UI
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-4
wave_status: complete
depends_on: [13-bed-suggestions, 14-bloom-timeline]
relates: [11-garden-canvas]
source_files:
  - frontend/src/api/client.ts
  - frontend/src/api/types.ts
  - frontend/src/components/BloomTimeline.tsx
  - frontend/src/components/SuggestionList.tsx
  - frontend/src/components/BedPanel.tsx
  - frontend/src/App.tsx
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/components/BloomTimeline.test.tsx
  - frontend/src/components/SuggestionList.test.tsx
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [react, timeline, suggestions, accessibility, gaps]
path: Frontend/Timeline
integration_contracts: []
satisfies_contracts:
  - from: 14-bloom-timeline
    function: GET /api/v1/gardens/{token}/timeline
    when: rendering the bloom year
    status: done
    verified_at: "frontend/src/App.tsx:44"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 15 — Timeline and Suggestions UI

## Purpose

Make the bloom year visible, and let a user act on it by planting a suggestion
into a bed.

## Accessibility of a chart

A bar chart is where information usually becomes visual-only, so this is decided
rather than retrofitted:

- **The bars are a table underneath.** Each month is a row with its coverage as a
  number and its species listed, so nothing is knowable only by looking.
- **Gaps are marked by text as well as colour**, because a red bar means nothing
  to a screen reader and little to a colour-blind user.
- **The mode checkbox is a real `<input type="checkbox">`** with a label, not a
  styled div, and switching it announces the new gap count through a live region.

## The empty state teaches

A new garden's timeline is twelve empty bars — the first thing a user sees and
the least useful. It is replaced with a sentence explaining what to do, because a
chart of nothing looks broken rather than empty.

## Business Rules

- **Coverage renders as a share of the garden's own peak**, labelled as such.
  An unlabelled 0.44 invites the reader to invent a unit.
- **Unknown stays unknown** — a bed without computed light says so, and a
  suggestion without a colour shows neutral with a label.
- **Planting re-renders from the server's response.** The timeline depends on
  data only the server has; guessing locally would show a number the data does
  not support.

## Known Issues

- Plantings cannot be removed from the UI. The endpoint and client method exist;
  only the button is missing.
- The timeline is garden-wide only. Per-bed detail is in the API response but not
  yet rendered.

## Verified in the running app

Garden created, bed added (light computed immediately at 12.6 h/day, L 8),
suggestions fetched from the bed's own conditions, two species planted, and the
timeline filled in: April-May at 100% from *Ranunculus muricatus*, July-September
at 66% from *Eryngium alpinum*, with a **forage gap in June** between them — and
March and October flagged while January and November correctly are not.
Unchecking the weighting relabels the gaps and announces the new count.

## Bugs

(none yet)
