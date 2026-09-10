---
id: ninanatur-wave-23
title: "Wave 23: The plan is the page"
initiative: ninanatur
initiative_version: 23
status: planned
depends_on: ninanatur-wave-20
demo_state: "Der Plan füllt den Bildschirm — Werkzeuge links, Details zur Auswahl rechts, die Zeit unten. Beet wählen, Art wählen, die Pflanze im Plan sehen: ohne dass die Seite scrollt, am Schreibtisch wie auf dem Telefon, wo die Details als Blatt von unten kommen. Und der Plan schrumpft nie mehr zu einem Strich."
created: 2026-09-07
hash: 2e4e08fd
---

# Wave 23: The plan is the page

## Demo-State

Der Plan füllt den Bildschirm — Werkzeuge links, Details zur Auswahl rechts,
die Zeit unten. Beet wählen, Art wählen, die Pflanze im Plan sehen: ohne dass
die Seite scrollt, am Schreibtisch wie auf dem Telefon, wo die Details als
Blatt von unten kommen. Und der Plan schrumpft nie mehr zu einem Strich.

*(This wave is not complete until this can be manually demonstrated.)*

Detailed plan, in German, with every measurement:
`.mdd/plans/05-planseite-als-arbeitsplatz.md`.

## Why this is a wave

The owner's complaint — *man muss viel hoch und runter scrollen* — is
measurable, and it was measured on 2026-09-07 against the built bundle on the
garden *Schattencheck* (7 elements, 3 beds), by DOM measurement because the
Browser pane cannot capture this SVG:

| Situation | Document height | Screens | Note |
|---|---|---|---|
| Desktop 1280×720, tab *Zeichnen* | 1 835 px | **2.5** | left column 1 638 px, right column 606 px |
| Mobile 375×812, tab *Zeichnen* | 2 683 px | 3.3 | the plan starts at **1 945 px** — 2.4 screens down |
| Mobile 375×812, tab *Säen*, one bed selected | **8 747 px** | **10.8** | the *Vorschläge* panel alone is **6 725 px** |

Three structural reasons, not one:

1. **The core loop spans both tabs and both columns.** Select a bed (left,
   *Zeichnen*) → switch tab → pick a plant (left, *Säen*, in a 6 700 px list) →
   look at the plan (right, top). From row three of the list the plan is off
   screen; every *Pflanzen* means three screens back up to see what happened.
2. **The right column is mostly empty, the left one too full.** A fresh garden
   shows two "Noch nichts gepflanzt" boxes under the plan while 1 600 px of
   forms stack on the left. The wide column does no work.
3. **One-time questions stay forever.** *Boden im Garten* is asked once per
   garden (doc 48) and remains a 448 px form in the sidebar for good.

On a phone there is one column with the plan at the bottom: tools and plan are
never on screen together.

**And a real bug found on the way.** The plan SVG measured **27 px high** on
desktop and 12 px on mobile. `useViewport` measures the SVG's own rect,
`viewBox(view)` derives the aspect ratio from it, and `.canvas { height: auto }`
lets the viewBox decide the rendered height — a loop. One transiently short
measurement (background tab, short window, mobile address bar, keyboard) locks
in as the aspect ratio and never recovers until reload. Observed viewBox:
`-20 -0.6 40 1.2`.

## What is already there

| Piece | State |
|---|---|
| Two-column grid, tabs *Zeichnen* / *Säen*, eleven panels left | done — waves 12, 13 |
| One selection source of truth across list, plan and menu | done — docs 49, 51, 52 |
| Keyboard operability of every panel, `role=tablist`, Escape semantics | done, hard-won — keep |
| Element menu as a popover anchored to the shape | done — doc 51 |
| Suggestion list: full render, ~240 px per row, two buttons per row | done, and the reason for 6 725 px |
| `App.tsx` | **1 455 lines** against a 300-line rule; the wave is the moment to split it |
| Load waterfall on open (eight sequential awaits) | fixed by Wave 20 (plan 01, O2) before this wave starts |

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | the-plan-that-stayed-a-strip | — | planned | — |
| 1 | a-workspace-not-a-page | — | planned | 0 |
| 2 | what-the-selection-shows | — | planned | 1 |
| 3 | three-steps-in | — | planned | 2 |
| 4 | a-list-that-fits-a-window | — | planned | 2 |
| 5 | a-sheet-from-below | — | planned | 2 |
| 6 | one-panel-one-style | — | planned | 1 |

Four stages, and the first one ships alone:

- **Stage 0 — stop the bleeding:** 0. A bug fix and twenty lines of CSS; goes
  to production before anything else here is started.
- **Stage 1 — the shell:** 1, 2. The layout and what fills it.
- **Stage 2 — the content:** 3, 4. Fewer panels, a list that fits.
- **Stage 3 — the phone and the polish:** 5, 6.

## What each one is

### 0. the-plan-that-stayed-a-strip

Three small things, none of them optional.

- **Break the loop.** The stage (`.canvas-stage`) gets a height of its own —
  `height: min(75vh, 0.75 × width)` or `aspect-ratio` on the wrapper — the SVG
  fills it (`width: 100%; height: 100%`), and `useViewport` measures the
  **stage**, never the SVG. The plan's height must not depend on its own
  measurement.
- **The quick win.** The right column becomes `position: sticky; top: <header>`.
  The plan then stays in view while the left column scrolls — about seventy per
  cent of the complaint for twenty lines of CSS, and it holds even if the rest
  of the wave were never built.
- **The status line moves.** `.status` sits at the page bottom and is invisible
  while scrolling a list; only screen readers hear it. It becomes a toast at the
  viewport edge, `role="status"` and `aria-live` kept.

Tests: a vitest for `viewBox()` — no measurement with height 0 may yield an
aspect ratio below 0.3; a manual check in the real browser: open a garden in a
200 px high window, then maximise — the plan must grow with it.

### 1. a-workspace-not-a-page

No framework change, no rewrite. The pattern of every drawing tool: **the plan
fills the viewport; everything else docks to it and scrolls inside itself.**

```
┌───────────────────────────────────────────────────────────────┐
│ Header: brand · garden name/ID · ↶ ↷ · shade switch · account  │  sticky, 56 px
├────┬──────────────────────────────────────────┬───────────────┤
│ T  │                                          │ Inspector     │
│ o  │              PLAN                        │ (by selection,│
│ o  │        100dvh − header − dock            │  scrolls in   │
│ l  │        pan/zoom inside the element       │  itself,      │
│ s  │                                          │  360–420 px,  │
│    │                                          │  resizable)   │
├────┴──────────────────────────────────────────┴───────────────┤
│ Dock: bloom months · ▶ year · day playback · sun-map legend    │  collapsible
└───────────────────────────────────────────────────────────────┘
```

- **Header (sticky):** brand, garden name with the ID fold-out (today a 68 px
  panel), undo/redo, the shade switch as a toggle, feedback, account. The version
  badge stays.
- **Tool rail (left, 56 px, vertical, `role="toolbar"`, arrow keys):** select,
  rectangle, circle, triangle, polygon, freehand, the stamp palette as a fly-out,
  viewpoint. Replaces the *Zeichnen* panel (254 px) and the stamp palette.
- **Plan (centre):** full height. Zoom buttons and the grid scale as a small
  overlay in one corner rather than a row above the plan. The sun map and the
  day playback are layers *on* the plan, switched from the header.
- **Inspector (right, `<aside aria-label="Details">`):** its own scroll region.
  What it shows is feature 2.
- **Dock (bottom, collapsible):** the bloom year as a month strip, *Jahr
  abspielen*, the day slider, the sun-map legend. Everything that is *time* in
  one place, and the plan above reacts to it.

The two tabs go. *Zeichnen* and *Säen* are not two activities but two ends of
one loop; with the inspector the split has nothing left to do.

`App.tsx` is split along these seams: `GardenWorkspace` (layout), `ToolRail`,
`Inspector`, `TimelineDock`, and a `useGarden` hook holding state and effects.
The existing components (`BedPlantings`, `SuggestionList`, `ShadeSwitch`,
`ElementMenu`, `BloomTimeline`, `InsectScore`, `ElementList`) are **rehung,
not rewritten**.

Tests: structure — landmarks (`banner`, `main`, `complementary`, `contentinfo`),
one selection source of truth still holds, every rail tool reachable by arrow
keys, Escape semantics from doc 49 unchanged. No file over 300 lines afterwards.

### 2. what-the-selection-shows

The inspector is a router over the selection — the same selection docs 49/51/52
made singular, now also deciding what stands on the right.

| Selection | Inspector shows |
|---|---|
| nothing | the garden: soil as one line + *ändern*, light summary, bloom-year miniature, insect score, tree suggestions as a card, the element list |
| a bed | its values, what is planted in it, **the suggestions** (feature 4), the existing-planting form |
| an obstacle | the element menu — today a popover, now inspector content with the same fields |
| a planting | species info with the colour note |

*Pflanzen* highlights the new cluster on the plan; nothing scrolls. Selecting
on the plan, in the list, or in the inspector must leave all three agreeing —
a vitest asserts it, because three views on one selection is the obvious way
for them to disagree.

### 3. three-steps-in

The sidebar loses its permanent residents:

- **Boden im Garten** becomes part of a **three-step start** on first open —
  soil · compute shade · draw the first bed — and afterwards one line in the
  garden inspector with *ändern*. Doc 48's rule (one question per garden) is
  unchanged; only where it is asked.
- The two empty "Noch nichts gepflanzt" boxes become one line pointing at the
  next step.
- Sightlines become a rail tool; tree suggestions become a mark on the plan
  (*3 gefundene Bäume*) with a card in the inspector; *Konto zuordnen* moves to
  the header menu.

Decided with the owner before building: the start as an empty inspector with
prompts (recommended — no modal before the first look) or as an overlay.

### 4. a-list-that-fits-a-window

The suggestion list is virtualised (only the visible ~20 rows in the DOM),
rows become compact — name · colour dot · bloom months as a strip · fit badge ·
*+* — filters become chips in a sticky header **inside** the panel, and the
woody list keeps its own heading. The 6 725 px become a window. Nothing about
what is ranked changes; `rank_plants` is untouched.

Tests: fifty suggestions render fewer than thirty rows; keyboard navigation
through the virtual list reaches every item; the *Pflanzen* button of row forty
is reachable without page scroll.

### 5. a-sheet-from-below

On a phone the plan is full screen; the inspector is a **bottom sheet** with
three snap points (25 / 60 / 90 %); the tool rail becomes a bottom bar; the dock
a strip above the sheet handle. `touch-action: none` on the plan exists already;
the sheet needs a focus trap and Escape. Someone plants three species on a
phone without losing the plan — that is the manual check.

### 6. one-panel-one-style

Tokens for spacing and type scale, one panel style, keyboard-shortcut help on
`?`, empty states that say the next step. Nothing here changes behaviour; it is
what makes the shell read as one thing rather than nine panels rehung.

## Acceptance — measured, not tasteful

- The core loop (select bed → choose a species → see it on the plan) needs
  **no page scroll** at 1280×720 **and** at 375×812. Scroll exists only inside
  panels.
- `documentHeight ≤ innerHeight + 1` on the workspace.
- The plan is never below 40 % of the viewport height, and its height never
  depends on its own measurement (feature 0's test).
- A Playwright smoke test (the `create-e2e` skill is available) measures exactly
  those three numbers on a fixture garden with fifty suggestions — the
  regression test for the complaint itself. jsdom cannot do layout; the vitest
  suite covers structure and keyboard.
- A person opens the garden on a phone and plants three species without losing
  sight of the plan.

## What will not be solved here

- **Rendering the plan in the Browser pane.** It cannot capture this SVG (doc 58,
  confirmed again 2026-09-07). Every visual judgement in this wave happens in a
  real browser; the numbers come from DOM measurement.
- **Whether Playwright runs in CI.** Installing Chromium adds about two minutes
  to the workflow. Decide when feature 0's test exists: run it in CI, or keep it
  as a manual gate the release checklist names.

## Open Research

- Tabs removed entirely (recommended) or kept as inspector tabs?
- Inspector right (reading order plan → details) or left (tools close to hand)?
  Recommended: tools left, details right, as every editor does.
- Resizable inspector: a drag handle, or two fixed widths?

## Deliberately not in this wave

- A new drawing style. That is Wave 24, and it needs this shell to be stable
  first, because the theme interface lives in the canvas this wave rehangs.
- Any change to what is ranked, scored or suggested.
- A design system beyond tokens. One consistent panel is the goal; a component
  library is not.
