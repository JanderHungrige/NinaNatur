---
id: 51-element-context-menu
title: Saying What a Thing Is, at the Thing
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-12
wave_status: complete
depends_on: [45-relabel-and-skin]
relates: [52-element-list]
source_files:
  - frontend/src/components/ElementMenu.tsx
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/App.tsx
routes: []
models: [element]
test_files:
  - frontend/src/components/ElementMenu.test.tsx
data_flow: writes-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [context-menu, labelling, keyboard, accessibility]
path: Canvas/Menu
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# Saying what a thing is, at the thing

## What this is

Right-click an element and name it, where it is. The editor panel does the same
job across the page; this is the short way, and it is not the only way.

## Decisions

### The keyboard reaches it too

`Shift+F10` and the context-menu key open the same menu, positioned at the
element rather than at a pointer that does not exist. A menu only a right-click
can reach leaves out everyone working from the keyboard — and every element on
this plan has been focusable and named since Wave 10, so there was nothing to
build but the binding.

Focus moves into the menu when it opens and Escape closes it. Without both it is
a trap rather than a shortcut.

### The panel stays

Two ways to name a thing is one more than the tools needed, but not one more
than the *naming* needs: the menu is fast and small, and the panel holds the
things a menu should not — height, soil, moisture, the width of a path.

### An armed tool suppresses it

Right-clicking while drawing would open a menu over the shape being drawn. The
same rule as feature 49: while a tool is armed, the plan takes the interaction.

## Definition of done

Right-click names an element; the keyboard opens the same menu; Escape closes
it; and neither happens while a drawing tool is armed.
