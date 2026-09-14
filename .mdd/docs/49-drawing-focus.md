---
id: 49-drawing-focus
title: An Armed Tool Takes the Click
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-12
wave_status: complete
depends_on: [43-shape-tools]
relates: [50-polygon-closing, 88-what-the-selection-shows]
source_files:
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/canvas/useEscapeKey.ts
routes: []
models: []
test_files:
  - frontend/src/components/GardenCanvas.focus.test.tsx
  - frontend/src/canvas/useEscapeKey.test.ts
data_flow: reads-existing
last_synced: 2026-09-14
status: complete
phase: all
mdd_version: 11
tags: [selection, modes, escape, canvas]
path: Canvas/Focus
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Since doc 88 (Wave 23, 2026-09-14) Escape typed into a text field — a text or number input, a textarea, an editable element — belongs to that field: the details show the selection, and dropping it would take the half-typed field away with its view. From anywhere else Escape still puts the tool down, clears the draft and drops the selection, and that now includes a bed selected for planting, which used to stay selected."
---

# An armed tool takes the click

## The bug

Clicking the canvas to draw first selected the garden-wide bed. The page then
scrolled to the plant suggestions, the user clicked again, and the second click
drew. The tool looked like it needed two attempts.

## Decisions

### Not attached beats not clickable

While a tool is armed, the shapes on the plan get no click handler, no
`tabIndex` and no button role at all — rather than a `pointer-events: none` laid
over them. Not attaching is a guarantee; a CSS property is a hope that nothing
else ever sets it back, and it is invisible to a test in jsdom, which does no
hit testing.

### Escape is the one way out

It puts the tool down, clears the half-drawn outline, and drops the selected
element. The listener is always mounted rather than only during a drawing mode:
a selection outlives every mode, and its handles stay on the plan until
something removes them.

## Definition of done

A first click with a tool armed draws and selects nothing; with no tool armed
the beds work as before; Escape gets out of all of it.
