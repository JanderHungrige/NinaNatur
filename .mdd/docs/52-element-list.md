---
id: 52-element-list
title: Everything Drawn, as a List
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-12
wave_status: complete
depends_on: [51-element-context-menu]
relates: [47-panel-order]
source_files:
  - frontend/src/components/ElementList.tsx
  - frontend/src/App.tsx
routes: []
models: [element]
test_files:
  - frontend/src/components/ElementList.test.tsx
data_flow: reads-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [list, selection, overlap]
path: Canvas/List
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# Everything drawn, as a list

## What this is

Every element beside the plan, selectable by name. The user's own suggestion,
and the right one: it is the answer to shapes lying on top of each other.

## Decisions

### Draw order helps with two, and nothing helps with three

Feature 47's ordering fix stopped beds burying objects, which is the common
case. It does nothing for a pond under a lawn under a terrace. A list reaches
any of them, including one entirely covered.

### One selection, whichever way it was reached

Clicking a row selects exactly what clicking the shape selects, and the editor
beside the list is where naming happens. A third editing surface would be a
third place for the panels to disagree about what is selected — which is the
risk this wave's plan named for the menu and the list together.

### Each row says what it covers

Two beds are two rows reading "Blumenbeet". The area tells them apart without
clicking either, and it comes from the footprint the server already computed
rather than a fourth answer to what ground an element covers.

### It scrolls on its own

**This answers the wave's open research question.** A real garden can hold a
hundred elements, and the plan beside the list should not have to grow to match
— so the list caps its height and scrolls, while the drawing keeps the space it
had.

## Definition of done

Every drawn element appears; selecting a row selects it on the plan; an element
buried under two others is reachable; and a long list does not push the plan
down the page.
