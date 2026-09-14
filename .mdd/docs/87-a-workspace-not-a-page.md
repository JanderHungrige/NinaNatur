---
id: 87-a-workspace-not-a-page
title: A Workspace, Not a Page
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-23
wave_status: active
depends_on: [86-the-plan-that-stayed-a-strip, 11-garden-canvas, 47-panel-order, 49-drawing-focus, 52-element-list]
relates: [51-element-context-menu, 53-account-in-header, 65-the-shade-switch, 29-bloom-playback, 30-landing-and-garden-id, 90-a-list-that-fits-a-window]
source_files:
  - frontend/src/App.tsx
  - frontend/src/useStatus.ts
  - frontend/src/useAccount.ts
  - frontend/src/useRemembered.ts
  - frontend/src/garden/useGarden.ts
  - frontend/src/garden/useDerived.ts
  - frontend/src/garden/useSuggestions.ts
  - frontend/src/garden/useClipboard.ts
  - frontend/src/garden/useElements.ts
  - frontend/src/garden/useGeometry.ts
  - frontend/src/garden/useLight.ts
  - frontend/src/components/GardenWorkspace.tsx
  - frontend/src/components/SiteHeader.tsx
  - frontend/src/components/ToolRail.tsx
  - frontend/src/components/Inspector.tsx
  - frontend/src/components/TimelineDock.tsx
  - frontend/src/components/PlanArea.tsx
  - frontend/src/components/InspectorPanels.tsx
  - frontend/src/components/GardenId.tsx
  - frontend/src/components/ShadeSwitch.tsx
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/App.test.tsx
  - frontend/src/components/ToolRail.test.tsx
  - frontend/src/components/Inspector.test.tsx
  - frontend/src/components/TimelineDock.test.tsx
  - frontend/src/useRemembered.test.ts
  - tests/test_workspace_layout.py
  - tests/test_stylesheet.py
  - tests/test_plan_stage.py
data_flow: mixed
last_synced: 2026-09-14
status: complete
phase: all
mdd_version: 11
tags: [workspace, layout, landmarks, toolbar, keyboard, state, refactor, accessibility]
path: Workspace/Shell
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Deferred to feature 6: the dock shows the bloom year's table rather than the compact month strip plan 05 drew, and the day slider and the sun map's legend stay in the player and the shade switch."
  - "Deferred to feature 5: below 66rem the workspace is a stacked page, and text inputs are 0.9rem — iOS zooms into anything under 16 px."
  - "Component and hook bodies longer than 50 lines remain, as everywhere in the frontend (GardenCanvas is the precedent); the callbacks inside them stay under 50."
  - "The Browser pane sends Enter with an empty key, so a native Enter on a rail tool was not exercised there; a real ArrowDown, click and Escape were (preview, V0.20.155)."
  - "On a 375×812 phone the preview band and the header take 336 px above the rail — feature 5's to fix."
  - "Rule 10 first relied on the dock body's 40vh alone, and forgot the header, the preview band and the dock's own bar. With one species planted the bloom year filled the body, and the plan's stage measured 260 px of 720 (36 %), 286 of 800 and 346 of 900 on the preview (V0.20.159); at 600 px the plan's row, held up by the tool rail, ran 94 px under the dock. Released that way in V0.20.161, and fixed by the row's own floor right after."
  - "The panels that scroll were not positioned, so absolutely positioned hidden text inside them had the page as its containing block: at 1280×600 with a planted garden the bloom year's hidden table caption made the page 628 px tall (preview, V0.20.167). Positioned since Wave 23 feature 3, with a guard."
  - "Since doc 90 (Wave 23, 2026-09-14) the details are a size container, so the suggestion list is never taller than they are; nothing inside them may be fixed-positioned, which the containment would pin to them."
---

# 87 — A Workspace, Not a Page

Feature 1 of Wave 23, and the first half of stage 1. The garden stops being a
page that scrolls past two columns and becomes a workspace that fills the
window: a header, a tool rail, the plan, a details panel and a time dock. It
ships to production together with feature 2 (doc 88), which decides what the
details panel shows — on its own the panel would hold everything at once.

## Purpose

Measured on 2026-09-07 (plan 05): the garden page was 2.5 screens tall on a
desktop and 10.8 on a phone with a bed selected, and the core loop — select a
bed, choose a species, see it on the plan — crossed both tabs and both columns.
Stage 0 (doc 86) kept the plan in view. This feature removes the reason to
scroll at all: the plan fills the window, and everything else docks to it and
scrolls inside itself. It is also where `App.tsx` stops being one 1,459-line
function.

## Architecture

### The shell

```
.app.app--workspace                ≥ 66rem: the window's height, and only panels scroll
├─ PreviewBand                     as before: pushes the rest down, never floats
├─ header.site-header    banner    brand · version · h1 · ID ▾ · ↶ · Sonne & Schatten · Rückmeldung · account
├─ main#main.workspace   main      grid: 3.5rem | minmax(0, 1fr) | 22rem (30rem when wide)
│  ├─ tool-rail          toolbar "Werkzeuge": Auswählen · Rechteck · Kreis · Dreieck · Vieleck · Freihand
│  ├─ workspace__plan    GardenCanvas (the stage fills the cell) · zoom and scale over its corner · tool hint · element menu
│  └─ aside.inspector    complementary "Details" — scrolls in itself
├─ footer.timeline-dock  contentinfo: the bloom year — player, and the timeline in a body that folds away
└─ StatusToast
```

Below 66rem the same markup stacks in one column and the page scrolls, as it
does today — except that the plan now comes before the details instead of after
them, and the rail lies flat above it. The phone gets its sheet in feature 5.

### Where the state lives

- **App** keeps what outlives one garden: status and busy (`useStatus`), the
  account, the drawers and "my gardens" (`useAccount`), the version, the
  environment, the open garden, and the landing's ways to open or make one.
- **GardenWorkspace is keyed by the garden's token** and owns everything about
  that garden through `useGarden`, composed of `useDerived`, `useSuggestions`,
  `useClipboard`, `useElements`, `useGeometry` and `useLight`. Opening a
  different garden remounts it, so the selection, the filters, the armed tool,
  the day being watched and the undo stack all start empty. Before, `goHome`
  reset eight of the 36 pieces of state and opening a garden reset none: a bed
  selected in one garden stayed selected in the next.
- **The client is passed in.** `App` takes a `client` prop, defaulting to the
  real one, and hands it down. A module-level client forced every test of it
  through a stubbed global `fetch`, which is why no test rendered `App`.

### Rehung, not rewritten

The domain components keep their markup and their tests: `GardenCanvas`,
`ElementMenu`, `BedPanel`, `ElementList`, `BedPlantings`, `ExistingPlanting`,
`FilterControls`, `FilterBar`, `SpeciesInfo`, `SuggestionList`, `CanopyBox`,
`GardenSoil`, `Sightlines`, `InsectScore`, `BloomPlayer`, `BloomTimeline`,
`AccountBar`, `PreviewBand`, `FeedbackBox`, `AccountPanel`, `Landing`. Two get a
small change that leaves their tests as they are:

- `GardenId` wraps everything below its summary in one element, so the header
  can open it as a dropdown.
- `ShadeSwitch` takes `showToggle` (default `true`). The workspace passes
  `false`: the header's *Sonne & Schatten* button is the switch now, and two
  controls for one state disagree the moment one of them is disabled.

The shell's own files: `GardenWorkspace` wires it together, `SiteHeader` is the
header on both sides of the front door, `ToolRail`, `PlanArea` (the canvas, its
menu and the tool hint), `Inspector` (the aside and its width) with
`InspectorPanels` (everything it holds until feature 2 routes it), and
`TimelineDock`. `useRemembered` keeps the two layout choices.

Removed: `Tabs` and its test, and `ShapeTools`, whose tools and hints move into
`ToolRail`.

## Data Model

None.

## API Endpoints

None. The same client calls, from new places.

## Business Rules

1. **Nothing but a panel scrolls** at 66rem and wider. The app is the window's
   height (`100vh`, then `100dvh`), the body's padding is dropped while the
   workspace is open, the plan's column is `minmax(0, 1fr)`, and the inspector
   and the dock's body scroll in themselves with `overscroll-behavior: contain`.
2. **The workspace only opens when the plan keeps 40rem.** Rail 3.5rem +
   inspector 22rem + plan 40rem: the three columns start at 66rem, and the wide
   inspector (30rem) only at 74rem. Widening the window must never narrow the
   plan — the lesson `tests/test_stylesheet.py` recorded for the two columns.
3. **The plan's height still never depends on its own measurement** (doc 86).
   In the workspace the stage fills the plan's grid cell (`height: 100%`);
   below the breakpoint it keeps doc 86's `clamp(16rem, 75vh, 75cqi)`.
4. **Landmarks:** one `banner`, one `main`, one `complementary` named
   "Details", one `contentinfo`, and the skip link still lands on `main`. The
   garden's name is the page's `h1` — visually hidden, because the header already
   shows it on the ID fold.
5. **The tool rail is one keyboard stop.** `role="toolbar"` named "Werkzeuge",
   with `aria-orientation` following the layout. Arrow keys move between tools
   (Up and Left back, Down and Right on, Home and End to the ends); Enter or Space
   arms the focused tool; the armed tool is `aria-pressed`. *Auswählen* puts the
   tool down, as pressing the armed tool again does. While busy the tools are
   `aria-disabled` and ignore presses instead of being `disabled`, because a
   disabled button cannot hold focus and would throw it out of the toolbar. Each
   tool is named by an `aria-label` carrying the words its tooltip shows on hover
   and on focus. Chrome's own accessibility tree, read over CDP, names the
   buttons from the visually hidden text as well; the Browser pane's tree, which
   leaves clipped text out, listed them without names, and the label makes the
   two agree.
6. **Escape still puts the tool down and drops the selection** (doc 49). The
   canvas's listener is untouched; the rail only shows the tool it is given.
7. **The armed tool says what to do,** in a polite live region over the plan's
   corner — the hints `ShapeTools` carried.
8. **One undo.** The header's ↶ — named *Letzte Änderung rückgängig*, so it is not
   mistaken for the polygon draft's own *Rückgängig* — runs the same undo as
   Ctrl/Cmd+Z and is disabled when there is nothing to take back. There is no redo stack; the polygon
   draft's own undo and redo stay in the plan's controls.
9. **The inspector is 22rem or, on request, 30rem** — a toggle (*Breite Ansicht*,
   `aria-pressed`, one name in both states), not a drag handle. The wave left this to feature 1:
   the range plan 05 named (360–420 px) is too narrow to be worth a drag gesture,
   a toggle is one keyboard stop with a state a screen reader can name, and
   feature 4's compact list gets two known widths to fit. The choice is kept in
   `localStorage`, read defensively; below 74rem the toggle is not shown.
10. **The dock holds the bloom year.** `BloomPlayer` is always there;
    `BloomTimeline` sits in a body that folds away under its heading, whose
    button *Jahreslauf* carries `aria-expanded` and `aria-controls` — not
    *Blühjahr*, which is already the heading of the table inside it. The body is
    at most 40vh and scrolls itself. What keeps the plan at least 40 % of the
    window is its own row, not the dock: the row grows from nothing and keeps
    `max(40vh + 1rem, 18rem)` — 40vh and its padding, or the whole tool rail —
    and the dock gives way beneath it. Open by default, and the choice is
    remembered.
11. **The front door does not change:** no workspace, the landing in its own
    `main`, the film behind it.
12. **No new file is over 300 lines,** and `App.tsx` drops from 1,459 lines to
    under 300.

## Data Flow

- **The garden:** `App.load(token)` → `client.getGarden` → `garden` in App →
  `<GardenWorkspace key={token} garden setGarden …>`. Every edit's answer is
  written back through `setGarden`. Opening one from the front door goes through
  `run`, so a failure there is said too.
- **Derived answers:** `useDerived` fetches the six (`fetchDerived`) and the
  canopy suggestions when the workspace mounts, then says what `App` hands it:
  "<name> geladen.", or — for a garden just made from the map — what the map
  could and could not measure, which the plainer message must not overwrite. A
  failure says "Laden fehlgeschlagen" instead of reaching only the console.
  `refresh` re-reads them after an edit, as before.
- **Status:** `useStatus` lives in App; `run` and `setStatus` are handed to the
  workspace, and `StatusToast` renders the one status.
- **The header:** App renders `SiteHeader` on the front door; the workspace
  renders the same header with its own controls (undo depth, the shade switch,
  the ID fold).

Full trace: `.mdd/audits/flow-a-workspace-not-a-page-2026-09-14.md` (local).

## Dependencies

- **86-the-plan-that-stayed-a-strip** — the stage that owns its height. Its
  sticky column was the stopgap this replaces.
- **11-garden-canvas**, **49-drawing-focus** (Escape), **52-element-list** (one
  selection), **47-panel-order** (the order this replaces).
- Related: **51-element-context-menu** (the fixed, anchored menu),
  **53-account-in-header**, **65-the-shade-switch**, **29-bloom-playback**,
  **30-landing-and-garden-id**.

## Security

Nothing new. No input, storage or network beyond what the rehung components
already do; `localStorage` holds two layout preferences and nothing about a
garden.

## Known Issues

See the frontmatter: the month strip, the phone, and function length in
components.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
