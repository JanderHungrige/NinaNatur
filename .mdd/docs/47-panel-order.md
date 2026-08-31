---
id: 47-panel-order
title: The Tools Above the Plan They Operate
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-12
wave_status: complete
depends_on: [43-shape-tools]
relates: [48-garden-soil, 52-element-list]
source_files:
  - frontend/src/App.tsx
  - frontend/src/components/BedPanel.tsx
routes: []
models: []
test_files:
  - frontend/src/components/BedPanel.test.tsx
data_flow: reads-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [layout, panels, cleanup]
path: Canvas/Layout
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# The tools above the plan they operate

## What this is

The drawing tools move to the top of the left column, directly under the garden
ID. The two forms that predate drawing — *Beet hinzufügen* and *Hindernis
hinzufügen* — go.

## Decisions

### Two ways to put a thing on a plan is one more than anybody wants

Both forms were the only way to add anything before Wave 11. They are now the
slower way to do what a drag does, and they ask for coordinates the user would
have to work out from a drawing they are looking at.

The bed list stays. It is how a bed is selected for planting, and feature 52
turns it into the list of everything.

### Soil and moisture leave with the form, but not out of the product

They were fields on *Beet hinzufügen*, and removing that form would remove them.
Feature 48 is where they land: asked once per garden, defaulted into every bed,
changeable per bed afterwards. Doing it in this feature would mean deleting them
first and adding them back in the next commit.

## Definition of done

The tools sit under the garden ID, neither form is on the page, and a bed can
still be selected from the list.
