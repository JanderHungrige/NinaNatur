---
id: 45-relabel-and-skin
title: Click It and Say What It Is
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-11
wave_status: complete
depends_on: [42-element-model]
relates: [41-garden-style, 43-shape-tools]
source_files:
  - frontend/src/components/ObjectEditor.tsx
  - frontend/src/kinds.ts
  - ninanatur/garden/store.py
  - ninanatur/garden/plantings.py
routes: ["/api/v1/gardens/{token}/obstacles/{obstacle_id}"]
models: [element, planting]
test_files:
  - tests/test_relabelling.py
  - frontend/src/components/ObjectEditor.test.tsx
data_flow: writes-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [relabel, kinds, skin, plantings, warning]
path: Canvas/Relabel
integration_contracts:
  - from: 42-element-model
    function: kind is a column, not a table
    when: an element is re-labelled
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# Click it and say what it is

## What this is

Click any element, choose what it is, and the plan redraws it: a bed takes soil
colour, a gravel path takes the stipple, a pool takes water. The symbols were
already there from Wave 10 — this is what points them at a decision made after
drawing rather than before.

## Decisions

### The kind is always offered

Wave 10's editor hid the kind selector on a bed. That was the two-table split
showing through the interface: a bed could not become anything else, so there
was nothing to offer. Since feature 42 it can, and hiding the control would be
the schema's old shape outliving the schema.

The kind is sent on every save, unchanged or not. A save that quietly omitted an
unchanged kind would work until the day something relied on it.

### Re-labelling away from a bed warns, then deletes

The user sees *"Hier stehen 7 Pflanzen. Beim Speichern als „Teich" gehen sie
verloren"* before it happens, and the count comes from the plants the browser is
already displaying rather than from a second answer computed on the server.

Chosen over refusing the change — a dead end in the middle of drawing is worse
than a warned loss — and over keeping the plantings hidden, which would leave
rows that nothing displays and nothing can reach.

The deletion is the store's, not the interface's: `update_obstacle` drops them
whenever the kind stops being a planting site, so the invariant holds whatever
the entry point. That is the same rule `add_bed` follows for light.

## Definition of done

A drawn shape can be labelled as anything, its drawing changes to match, and
re-labelling a planted bed says what it will cost first.
