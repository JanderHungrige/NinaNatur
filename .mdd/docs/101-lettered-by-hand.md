---
id: 101-lettered-by-hand
title: Lettered by Hand
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-24
wave_status: active
depends_on: [97-draft-sketch-in-svg, 98-what-the-style-has-not-drawn]
relates: [100-the-switch, 99-paper-bleed-and-a-real-shadow]
source_files:
  - frontend/src/themes/draft-sketch/theme.css
  - frontend/src/themes/draft-sketch/ours/Furniture.tsx
  - THIRD_PARTY.md
routes: []
models: []
test_files:
  - tests/test_theme_provenance.py
data_flow: greenfield
last_synced: 2026-09-20
status: draft
phase: all
mdd_version: 11
tags: [draft-sketch, typography, font, accessibility, contrast, licence]
path: Plan/Draft Sketch/Lettering
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 101 — Lettered by Hand

## Purpose

A drawing in someone's hand with the interface's own type on it is two
drawings. The plan's own lettering — the title block, the scale bar's numbers,
and anything the plan writes on itself — should be written the way the rest of
it is drawn. The interface around the plan keeps the system font: that is a
control panel, not a drawing.

## What his file settles, and what it does not

**Nothing.** Draft Sketch has no lettering at all: 97 symbols — 48 polygons,
35 lines, 14 points (his trees, an arrow, an asterisk) — and not one
`fontFamilyName`, `CIMTextSymbol` or `CIMCharacterMarker` among them. Doc 97
planned to check whether his font was free enough to bundle; the question does
not arise, and there is no hand of his to match.

So the hand is ours to choose, and it is chosen for the plan, not for him.

## The choice, and what constrains it

- **A free licence that allows bundling.** The SIL Open Font Licence does;
  the font's own licence file ships beside it, and `THIRD_PARTY.md` names it.
- **No CDN.** The policy is `font-src 'self'` (Wave 20), so the file lives in
  this repository and is served by this server. That is also why it is a
  decision worth asking about: it is a third-party file in a public repository.
- **Legible at a title block's size** — eleven or twelve pixels — and complete
  enough for German: ä, ö, ü, ß.
- **Upright rather than cursive.** A draughtsman letters upright; a sloping
  hand reads as a note stuck to the plan.

Two candidates, both OFL: *Patrick Hand*, which is upright and plain, and
*Caveat*, which is faster and more slanted. The owner picks.

## Contrast, measured

The lettering the plan already has, against what it sits on (WCAG 1.4.3 asks
4.5:1 for text this size):

| What | Ratio | |
|---|---|---|
| title block and scale bar, on the block's paper | 15.3 | passes |
| the same ink where his paper grain is darkest (`#e1e1e1`) | 12.2 | passes |
| his credit, light page | 5.5 | passes |
| his credit, dark page | 7.6 | passes |
| the tool hint on its chip, light / dark | 5.7 / 6.8 | passes |

A hand font changes none of these colours, but it changes the stroke: the
measurement is repeated once the font is in, because a thin hand at 11 px is a
different thing from a system sans at 11 px.

The bloom dabs and the sun map are colour, not text, and are read as a group
rather than individually; they are covered by doc 96's rule that
`prefers-contrast: more` and `forced-colors` draw the plan in Technisch
instead (doc 100), which is the honest answer rather than a recoloured
watercolour.

## Business Rules

1. **The plan's lettering only.** Interface text stays the system font.
2. **Bundled, never fetched.** No CDN, no remote font, and the licence file
   ships with it.
3. **A font that cannot write German is not a candidate.**
4. **Contrast is measured again after the font lands**, at the title block's
   real size.

## Dependencies

Docs 97–100. Wave 20's content security policy for `font-src`.

## Security

A bundled font is a static asset served from this origin; nothing about it is
computed from user input.

## Known Issues

- **Waiting on the owner:** which hand, and whether to bundle a third-party
  font in the public repository at all.

## Bugs
