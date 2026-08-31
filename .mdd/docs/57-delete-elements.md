---
id: 57-delete-elements
title: Taking Something Off the Plan
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-14
wave_status: complete
depends_on: [51-element-context-menu]
relates: [45-relabel-and-skin]
source_files:
  - ninanatur/garden/elements.py
  - ninanatur/api/gardens.py
  - frontend/src/components/ElementMenu.tsx
  - frontend/src/App.tsx
routes: ["/api/v1/gardens/{token}/obstacles/{obstacle_id}"]
models: [element, planting]
test_files:
  - tests/test_object_editing.py
  - frontend/src/components/ElementMenu.test.tsx
data_flow: writes-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [delete, canvas, confirmation]
path: Canvas/Delete
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# Taking something off the plan

## What this is

Delete an element from the right-click menu, where its kind and label already
are. Nothing could be removed from a plan until now — a shape drawn by mistake
stayed on it.

## Decisions

### It asks, and the confirming button says what it does

"Endgültig löschen", not "Ja". The same rule the garden list follows: a button
that names its action is the difference between confirming and clicking on. An
element cannot be got back, and this menu is one right-click away from every
shape on the plan.

### A planted bed says what it costs first

The same warning re-labelling gives, for the same reason — the plants go with
it, and nobody should find that out afterwards.

### The endpoint returns the garden, not a 204

Deleting a bed changes what every other bed gets: the thing that shaded it is
gone and the light is recomputed. Handing back 204 would make the caller ask a
second time for a result the server already has.

### Plantings cascade, and that is the schema's job

`planting` hangs off `element_id` with `ON DELETE CASCADE`. A row whose parent
is gone is a query that fails at the worst moment, so this is enforced by the
foreign key rather than by remembering to delete twice.

## Definition of done

An element can be deleted from the menu after confirming, a planted bed says
how many plants go with it, and deleting one recomputes the light.
