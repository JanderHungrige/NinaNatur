---
id: 96-a-theme-is-a-thing
title: A Theme Is a Thing
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-24
wave_status: complete
depends_on: [95-look-before-you-argue, 41-garden-style, 58-painted-plan]
relates: [95-look-before-you-argue, 41-garden-style]
source_files:
  - frontend/src/themes/types.ts
  - frontend/src/themes/index.ts
  - frontend/src/themes/context.tsx
  - frontend/src/themes/technisch/index.ts
  - frontend/src/themes/technisch/symbols.tsx
  - frontend/src/components/PlanObjects.tsx
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/canvas/viewport.ts
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/themes/themes.test.tsx
  - tests/test_theme_provenance.py
data_flow: reads-existing
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [themes, svg, patterns, provenance, contact-sheet, draft-sketch]
path: Canvas/Style
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# 96 — A Theme Is a Thing

## Purpose

Feature 0 of Wave 24, built second. Stage 2 draws the plan in Warren Davison's
Draft Sketch; until now nothing about the plan's look could be swapped, because
it was decided in four places at once — `GardenSymbols`, a fill attribute in
`CanvasScene`, a filter in the stylesheet, and the stylesheet's tokens. This
gives the look one seam, a `PlanTheme`, and moves today's plan behind it as the
theme **Technisch** without changing a pixel. Technisch is also what the plan
falls back to should the permission ever end.

## Architecture

```
PlanThemeProvider (default: technisch)
        │
CanvasScene ── <g class="plan-theme plan-theme--{id}">   scope for the theme's tokens
        ├─ <defs> theme.Defs + the grid                  patterns and filters, once
        ├─ grid, relief, compass
        ├─ PlanObjects ── <g class="canvas__objects" filter={theme.objectsFilter}>
        │        fill = theme.fill(symbol of kind, lod)   lod = theme.lodAt(m per px)
        └─ sun map, found trees, shadows, plantings, viewpoint, draft — unfiltered
```

## The interface (`themes/types.ts`)

| Member | What it decides | Technisch |
|---|---|---|
| `id`, `label` | the picker's key and word; `plan-theme--{id}` scopes the theme's tokens | `technisch`, "Technisch" |
| `provenance` | who made its marks | `NinaNatur` |
| `Defs` | every pattern and filter the layers refer to by id | the twelve symbol patterns and `#watercolour`, moved unchanged |
| `fill(symbol, lod)` | the paint for an element `kinds.ts` draws as `symbol`, at a level of detail | `url(#symbol-{symbol})`, one level |
| `bedFill(lod)` | the paint for a bed — its own member, because a bed's look is part of what it says (selected, raised, planted) | none: the stylesheet's `.bed`, as always |
| `objectsFilter` | the one filter chain over the objects layer | `url(#watercolour)` |
| `lodAt(metresPerPixel)` | which level of detail a scale gets | `near`, always |

It holds what Technisch uses and what stage 2 cannot start without. The rules
the wave lists for Draft Sketch — overshoot, splotches, the shadow moment, the
label style — join it with the features that draw them; an interface member
nobody reads is a guess about a future that has not been looked at.

**What stays out of the theme, deliberately.** The grid (a measurement, not a
style); the sun map, relief and day shadows (statements — doc 65 — with their
own inks); selection, focus and handles (accessibility); the kind → symbol
table (`kinds.ts`, mirrored by the server and guarded by
`test_kind_vocabulary.py` — a theme draws a symbol, it does not decide what a
kind is).

## Business Rules

1. **No visible change.** `npm run plan:sheet -- --check` passes: all 24 cells
   of doc 95's record, light and dark, pixel-identical.
2. **The filter moves from the stylesheet to the theme.** The objects group
   carries `filter="url(#watercolour)"` as an attribute; the stylesheet's rule
   goes. `prefers-contrast: more` and `forced-colors` still set `filter: none`,
   and a stylesheet property beats a presentation attribute, so both keep
   working unchanged.
3. **Only the objects layer is filtered.** Plantings, handles, vertices and
   every overlay stay outside the theme's filter, so a hit target is never
   displaced from what is drawn.
4. **The provenance rule.** Every theme's symbol file (`themes/*/symbols.*`,
   `themes/*/*.svg`) opens with a comment carrying `Provenance:` and one of:
   `NinaNatur` · `Warren Davison (Draft Sketch)` · `adapted from Draft Sketch` ·
   `NinaNatur, in the style of Draft Sketch`. A test refuses a file without one.
   It replaces the first plan's clean-room rule, now that the marks are used with
   permission: the question is no longer "is it ours" but "whose is it".
5. **The file-length rule.** `CanvasScene.tsx` was 390 lines; the objects layer
   moves to `PlanObjects.tsx`, where the theme is applied.

## Dependencies

- 95 — the record that proves rule 1.
- 41, 58 — the look being moved.

## Security

No new input. A theme is code in the bundle; nothing is loaded at runtime.

## Built (2026-09-18)

`npm run plan:sheet -- --check` against the record doc 95 took before this
feature: **all 24 cells as recorded**, light and dark. In Chromium the objects'
filter computes to `url("#watercolour")`, and to `none` under both
`prefers-contrast: more` and `forced-colors: active` — the stylesheet still
wins over the attribute. 877 vitest pass, among them six for the seam and the
existing style tests unchanged; the provenance test holds `technisch/symbols.tsx`
to its header.

**Since 2026-09-21** Technisch is no longer pixel-identical to the plan before
Wave 24, on purpose: the garden's own ground is a flat grass wash (#10), its
outlines are screen pixels and its wobble is capped at 7 px (#1, doc 112), and
the sun map is drawn as paths (#11, doc 113). Doc 95's record was retaken for
all three. Rule 1 held for this feature.

One thing the existing tests caught on the way: the first Technisch left
`planting` unfilled to keep real beds as they were, and an element of kind
`bed` — which the style test draws as an obstacle — lost its fill with it. The
difference is bed against element, not the symbol, so a bed got its own member.

## Known Issues

## Bugs

(none yet — populated by /mdd bug when issues are reported)
