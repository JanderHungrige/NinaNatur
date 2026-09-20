---
id: 100-the-switch
title: The Switch Between Plan Styles
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-24
wave_status: active
depends_on: [96-a-theme-is-a-thing, 97-draft-sketch-in-svg]
relates: [99-paper-bleed-and-a-real-shadow, 91-a-sheet-from-below]
source_files:
  - frontend/src/themes/index.ts
  - frontend/src/themes/usePageTheme.ts
  - frontend/src/components/ThemePicker.tsx
  - frontend/src/components/SiteHeader.tsx
  - frontend/src/App.tsx
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/themes/themeChoice.test.ts
  - frontend/src/components/ThemePicker.test.tsx
data_flow: greenfield
last_synced: 2026-09-20
status: draft
phase: all
mdd_version: 11
tags: [theme, plan, preferences, accessibility, draft-sketch]
path: Plan/Theme switch
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 100 — The Switch Between Plan Styles

## Purpose

A theme that can be switched is one that can be improved (doc 96). Until now
the second style has been reachable only by typing `?theme=draft-sketch` on the
preview. This gives the gardener the choice, in the one menu that already holds
what acts on the whole garden, and remembers it for them.

## What decides which style is drawn

Three things, in this order — the last one wins:

1. **What the viewer chose**, remembered in their own browser
   (`localStorage`, key `ninanatur.plan-theme`). A browser that refuses
   storage is not an error: the choice then lasts the page.
2. **What the address asks for** (`?theme=…`), which still works and is what
   the contact sheet and every probe use.
3. **What the deployment allows.** Draft Sketch is served only where its files
   are (`assets/draft-sketch/`, doc 97) — the preview. Elsewhere the list has
   one entry and no picker is drawn, and a remembered choice for a style that
   is not on offer falls back to Technisch rather than to an empty plan.

And one override above all of them: with **`prefers-contrast: more` or
`forced-colors: active` the plan is Technisch**, whatever was chosen. A style
whose whole substance is washes, grain and pencil ink is the wrong answer to
"I need this to be clearer", and patching it — as doc 98 did, by hiding the ink
— leaves a drawing with its shapes and none of its marks. The picker says so
where it stands rather than silently disagreeing with the plan.

## Where it stands

In the header's *more* slot, beside the sun map and undo: a `<fieldset>` of
radio buttons, one per theme, labelled by the theme's own `label`. Not a
`<select>`, because there are two of them and the choice is worth seeing; not a
toggle, because a third style is meant to fit (doc 96's seam is a list).

The picker is drawn only when more than one theme is on offer, so production
carries no control for something it will not serve.

## The third slot

`THEMES` in `frontend/src/themes/index.ts` is the list, and everything in the
app reads from it: the picker, `themeById`, the contact sheet's `--theme`. A
third style needs a `PlanTheme` (doc 96's seam), an entry in that list, and its
own `theme.css`; nothing else knows how many there are. A style whose files are
not served everywhere also needs a line in `delivery.py`, as Draft Sketch has.

## Business Rules

1. **The plan Technisch draws never changes**, and doc 95's record is what says
   so: a switch is a switch, not a redesign.
2. **A choice is a preference, not data.** It lives in the viewer's browser,
   never on the server and never in a garden: two people looking at one shared
   garden each see it in their own hand.
3. **High contrast and forced colours take the choice away**, visibly.
4. **Nothing offers a style the deployment will not serve.**

## Dependencies

Doc 96 (the seam and `THEMES`), doc 97 (the chunk and the preview-only gate),
doc 91 (the header's menu).

## Security

A remembered theme id is read from `localStorage`, and an unknown one resolves
through `themeById` to Technisch. Nothing is fetched by name from it: the
chunk's import is a fixed branch, not a computed path.

## Known Issues

## Bugs
