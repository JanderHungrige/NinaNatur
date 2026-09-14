---
id: 91-a-sheet-from-below
title: A Sheet From Below
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-23
wave_status: active
depends_on: [87-a-workspace-not-a-page, 88-what-the-selection-shows, 90-a-list-that-fits-a-window]
relates: [53-account-in-header, 30-landing-and-garden-id, 29-bloom-playback, 86-the-plan-that-stayed-a-strip]
source_files:
  - frontend/src/workspace/sheet.ts
  - frontend/src/workspace/useInertOutside.ts
  - frontend/src/components/SheetHandle.tsx
  - frontend/src/components/Inspector.tsx
  - frontend/src/components/SiteHeader.tsx
  - frontend/src/components/GardenWorkspace.tsx
  - frontend/src/testing/appFixtures.tsx
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/workspace/sheet.test.ts
  - frontend/src/components/SheetHandle.test.tsx
  - frontend/src/components/Inspector.test.tsx
  - frontend/src/components/SiteHeader.test.tsx
  - frontend/src/App.sheet.test.tsx
  - tests/test_narrow_workspace.py
data_flow: reads-existing
last_synced: 2026-09-14
status: in_progress
phase: 6
mdd_version: 11
tags: [workspace, mobile, bottom-sheet, accessibility, focus, layout]
path: Workspace/Sheet
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# 91 — A Sheet From Below

Feature 5 of Wave 23. Below 66rem the workspace stops being a page: the plan
fills the window, the tools are a bar at its foot, and the details come up
from below as a sheet with three heights.

## Purpose

On a phone the garden was a page. Measured on the preview (V0.20.171) in
Chromium with the iPhone 11 Pro's metrics — 375 px wide, 635 px of window,
touch — the stage 1 garden was 3,069 px tall: a header of 199 px in four rows,
the tools, the plan's controls, 126 px of plan on the first screen under the
toast, and the details below it all. Tapping a bed filled the details 832 px
down, out of sight; the first *+* was 1,504 px down, and scrolling to it took
the plan out of view, so the patch the planting drew was drawn where nobody
could see it. The wave's acceptance names this: no page scroll at 375×812, and
three species planted on a phone without losing sight of the plan.

## Architecture

```
.app--workspace          the window's height; nothing scrolls but a panel
├─ PreviewBand           (the preview only)
├─ SiteHeader            one row: mark · the garden's fold · undo · Menü
│  └─ .site-header__more  version · Sonne & Schatten · Rückmeldung · account
├─ main.workspace        data-sheet = peek | half | full
│  ├─ PlanArea           fills what the sheet leaves at rest
│  ├─ aside.inspector    the sheet: SheetHandle, then the details as before
│  └─ ToolRail           a bar fixed at the window's foot
└─ footer.timeline-dock  the year, a strip above the bar
```

- `workspace/sheet.ts` holds the heights and the arithmetic of a drag: where
  a finger has taken the sheet, and where a released drag comes to rest. Pure.
- `SheetHandle` is the handle: a window splitter for the keyboard and a screen
  reader, a drag and a flick for a finger.
- `useInertOutside` makes everything but one element `inert`, and gives it
  back.
- `Inspector` takes an optional `sheet`: with it, the aside carries its height
  as `data-snap`, renders the handle, traps the page at 90 % and lowers itself
  on Escape. Without it, it is doc 87's column, unchanged.
- `GardenWorkspace` owns the height (per mount, never stored), sets it on
  `main` for the stylesheet, and passes a sheet to the details only on a narrow
  window. It writes a drag in progress straight to `main`'s style, so a moving
  finger re-renders nothing.
- `SiteHeader` gains a `more` slot and a *Menü* disclosure. On a wide window,
  and on the front door, the disclosure's contents stand in the header as
  before and its button is not shown.

## Data Model

None. The only new remembered value is per browser: whether the year is folded
on a narrow window (`ninanatur.dock.open.narrow`, folded by default).

## API Endpoints

None.

## Business Rules

1. **The narrow workspace is the window.** Below 66rem the app is the window's
   height (`100vh`, then `100dvh`), the body has no padding, and nothing
   scrolls but a panel: the sheet, the year's table, the suggestion window.
2. **The header is one row**: the mark, the garden's fold, undo and *Menü*. The
   version, *Sonne & Schatten*, *Rückmeldung* and the account are behind *Menü*,
   a disclosure (`aria-expanded`, `aria-controls`). Escape closes it and gives
   the focus back to its button without reaching the plan's Escape; pressing
   anything in it closes it after doing that thing; a pointer going down
   outside closes it. The front door's header is untouched.
3. **The plan fills what the sheet leaves at rest**, its controls and hint
   floating over it. It follows the sheet's resting height and not a drag in
   progress: one refit per height, not one per frame. A shorter stage keeps the
   view's centre and horizontal span (`measuredView`), as a resized window does.
4. **The tools are a bar at the window's foot**, seven across. Their names open
   upward, and at the two ends inward, so no name leaves the window.
5. **The year is a strip above the bar**, not on the sheet as the wave sketched:
   the dock is the page's `contentinfo` (doc 87) and stays outside `main`, and
   below the sheet it holds still while the sheet moves. Its table opens upward
   over the sheet and scrolls in itself. On a narrow window the year starts
   folded, remembered apart from the wide window's choice.
6. **The details are a sheet from below with three heights** — a quarter, 60 %
   and 90 % of the space between the header and the year's strip — and rest at
   a quarter, where the view's heading shows. A bed tapped on the plan says its
   name there at once (doc 88's handoff); nothing raises the sheet but the
   gardener.
7. **The handle is a window splitter**: `role="separator"`, horizontal, named
   *Höhe der Details*, `aria-valuenow` 25, 60 or 90 with the height in words,
   `aria-controls` the details. Arrow Up and Page Up raise it one height, Arrow
   Down and Page Down lower it, Home and End go to the ends, and Enter toggles a
   quarter and 60 % (from 90 % it comes down to 60 %). Dragged, the sheet
   follows the finger and comes to rest at the nearest height, or at the next
   one the way it was flicked; a touch that does not travel is Enter.
8. **At 90 % the sheet is the page.** Everything outside it is `inert` — a focus
   trap that also hides the rest from a screen reader — and dimmed, and the
   focus moves in if it was outside. Escape, unless typed into a text field,
   lowers it to 60 % and leaves the selection alone. Below 90 % the plan stays
   usable and Escape keeps doc 88's meaning.
9. **The toast drops from the top** on a narrow window, where neither the sheet
   nor the bar can cover it.
10. **Text fields are 16 px** on a narrow window, so iOS does not zoom into them
    (doc 87 deferred it here).
11. **The wide workspace is unchanged.** From 66rem everything is as doc 87
    built it, and no sheet, handle or menu button is shown.
12. **The plan's 40 % holds at rest.** At a quarter the plan keeps at least
    40 % of the window at 375×812 and in the 375×635 window of an iPhone 11
    Pro. Raising the sheet is the gardener's choice to trade plan for details;
    60 % and 90 % do not promise the floor.
13. **No new file is over 300 lines.**

## Data Flow

Traced in `.mdd/audits/flow-a-sheet-from-below-2026-09-14.md` (local): nothing
is requested, returned or stored that was not before, apart from the one
remembered fold. The selection, the views and their focus rules (doc 88) are
the same component in a different box.

## Dependencies

- **87-a-workspace-not-a-page** — the wide workspace, the landmarks, the dock.
- **88-what-the-selection-shows** — the views, Escape, and the focus rules.
- **90-a-list-that-fits-a-window** — the suggestion window, bounded by the
  sheet it stands in.
- Related: **53-account-in-header**, **30-landing-and-garden-id**,
  **29-bloom-playback**, **86-the-plan-that-stayed-a-strip**.

## Security

Nothing new. `inert` removes interaction; it grants none.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
