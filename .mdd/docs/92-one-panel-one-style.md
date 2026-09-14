---
id: 92-one-panel-one-style
title: One Panel, One Style
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-23
wave_status: active
depends_on: [87-a-workspace-not-a-page, 91-a-sheet-from-below]
relates: [88-what-the-selection-shows, 89-three-steps-in, 90-a-list-that-fits-a-window]
source_files:
  - frontend/src/styles.css
  - frontend/src/workspace/shortcuts.ts
  - frontend/src/workspace/useShortcutHelp.ts
  - frontend/src/components/ShortcutHelp.tsx
  - frontend/src/components/GardenWorkspace.tsx
  - frontend/src/components/BedPanel.tsx
  - frontend/src/components/BloomTimeline.tsx
routes: []
models: []
test_files:
  - tests/test_one_style.py
  - tests/test_stylesheet.py
  - frontend/src/workspace/shortcuts.test.ts
  - frontend/src/workspace/useShortcutHelp.test.ts
  - frontend/src/components/ShortcutHelp.test.tsx
  - frontend/src/App.help.test.tsx
  - frontend/src/components/BedPanel.test.tsx
  - frontend/src/components/BloomTimeline.test.tsx
data_flow: reads-existing
last_synced: 2026-09-14
status: complete
phase: all
mdd_version: 11
tags: [design-tokens, panels, typography, keyboard, accessibility, empty-states]
path: Workspace/Style
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Measured in Chromium only. There a click on the help's words keeps the focus in the dialog (V0.20.179); where a browser leaves it on the page's body, the window's guard keeps the keys from the page, and vitest covers that (ShortcutHelp)."
  - "Counted by radius, padding, border and background, the details still draw three kinds of box for the garden and two for a bed (V0.20.179): each panel keeps its own padding, and the list of what is drawn and the suggestion window are rows."
  - "The help's list is written by hand: a key the code starts to answer shows in it only once workspace/shortcuts.ts names it too."
---

# 92 — One Panel, One Style

Feature 6 of Wave 23, the last one. Nothing here changes what the workspace
does, apart from one addition: help for its keyboard shortcuts. The rest is
what makes the shell read as one thing rather than nine panels rehung.

## Purpose

Five features rehung the garden's panels into a workspace, a sheet and a list,
and each brought its own box. Measured on the preview (V0.20.177) from computed
styles:

- The garden in the details drew three kinds of boxed panel, with text in seven
  sizes.
- A bed in the details drew two kinds, with text in eight sizes.

Counted with the guard's own parser, the stylesheet declares the panel's box
again, whole, in nine other rules. One of them styles stamps that nothing
renders any more. A line with an 8px radius is declared in seven rules. The
sheet has 57 distinct paddings and 23 font sizes, and no custom property names a
space or a size.

- `?` did nothing, and no page named a shortcut except the polygon hint.
- Two empty panels named no next step.
- On a phone, the plan's controls ran 9 px past their row (doc 91).

## Architecture

- **`styles.css` gains two scales and two radii** as custom properties on
  `:root`, one rule for the panel look, and one for the row look.
  - Every font size inside the scale's range becomes one of its steps.
  - The literal values that guards compute from are left alone.
  - The preview band's rule stood nested inside `:root`; it moves out.
  - The rules for stamps and for `.empty`, which nothing renders, go.
- **`workspace/shortcuts.ts`** lists what the code answers, grouped by where it
  applies, in German. It is pure.
- **`workspace/useShortcutHelp.ts`** opens the help on `?`, remembers where the
  focus was, and gives it back.
- **`ShortcutHelp`** is a native `<dialog>`, opened modal. jsdom has no
  `showModal`, so the component falls back to `open`. No key pressed while it
  is open reaches the page.
- **`GardenWorkspace`** puts *Tastenkürzel* in the header's `more` slot and
  renders the dialog.
- **`BedPanel` and `BloomTimeline`** each name a next step in their empty
  state, as `.next-step`.

## Data Model

None.

## API Endpoints

None.

## Business Rules

1. **Two scales and two radii, as custom properties.**
   - Space: `--space-1` to `--space-6`, which are 0.25, 0.5, 0.75, 1, 1.25 and
     1.5rem.
   - Type: `--text-xs` 0.78rem, `--text-sm` 0.85rem, `--text-md` 0.95rem,
     `--text-base` 1rem and `--text-lg` 1.15rem.
   - Radii: `--radius` 12px for panels and `--radius-sm` 8px for rows and
     controls.

   None of these are colours, so none needs a dark value.
2. **One panel look, declared once.** Its border, radius and background are
   declared in a single rule, shared by every box drawn that way:
   - `.panel`
   - the panels under another name: the soil line, a first step, the garden's
     fold, the account drawer and the header's menu
   - the toast, the plan's paper, the sun's readout and the help itself

   Each keeps only its own padding. A panel's padding comes from the space
   scale.
3. **One row look, declared once.** A line and the small radius, in a single
   rule. It is shared by what sits inside a panel with a line round it:
   - a suggested change, a bed's planting and the suggestion window
   - a bed's button, a field, the garden's id and a tool's shown name

   The list of drawn elements takes the small radius too. No rule writes an 8px
   or 12px radius as a number any more.
4. **Every font size in the scale's range is one of its five.** That range is
   0.7 to 1.25rem.
   - 0.72–0.8rem becomes xs.
   - 0.82–0.88rem becomes sm.
   - 0.9–0.97rem becomes md.
   - About 1rem becomes base.
   - 1.05–1.25rem becomes lg.

   Sizes outside the range keep their own value: the details' title, the
   landing's figures and headings, the score's large number, the compass, and a
   phone's 16 px floor for fields (doc 91).
5. **The panels' spacing comes from the scale.** This covers their padding (a
   phone's included), the gap between panels in the details, and the margins of
   a panel's heading and of a hint.
6. **`?` shows the keyboard's shortcuts.**
   - **How it opens.** `?` opens it, unless someone is typing into a field or
     holds Ctrl, Cmd or Alt. *Tastenkürzel* in the header also opens it; on a
     narrow window that button is behind *Menü*, and it names `?` in
     `aria-keyshortcuts`.
   - **How it behaves.** The help is a modal dialog named *Tastenkürzel*. It
     takes the focus, and Escape or *Schließen* closes it.
   - **Where the focus goes.** When the help closes, the focus returns to where
     it was. If that can no longer take it, because the menu it was in has
     closed, the focus goes to that menu's button.
   - **Keys while it is open.** No key reaches the page, wherever the focus has
     gone. There, Escape would clear the selection and Ctrl+Z would undo a
     change hidden behind the help.
   - **What it lists.** Only what the code answers, grouped by where it applies.
     It says that ⌘ stands for Strg on a Mac, and that keys typed into a field
     belong to the field.
7. **An empty panel names its next step.**
   - A garden with no beds says to choose a shape from the tools and draw the
     first bed.
   - An empty bloom year says to choose a bed and plant a species.

   Notes about missing data stay notes. A missing Wikipedia article or an
   unrecorded height leaves nothing to do.
8. **A phone's plan controls fit their row.** At 375 px their text takes the
   scale's smallest size and their gaps its smallest space.
9. **What the guards compute from stays literal.** The rail's tools and gap, the
   bar, the sheet's rows and the suggestion window's height keep their rem
   values.
10. **No behaviour changes but the help, and no new file is over 300 lines.**

## Data Flow

Traced in `.mdd/audits/flow-one-panel-one-style-2026-09-14.md` (local).
Nothing is requested, returned or stored differently. The help reads a static
list.

## Dependencies

- **87-a-workspace-not-a-page**: the workspace, its header and its panels.
- **91-a-sheet-from-below**: the narrow window, the menu and the plan's controls.
- Related: **88-what-the-selection-shows** (Escape and the views),
  **89-three-steps-in** (the empty states), and
  **90-a-list-that-fits-a-window** (the rows and the window).

## Security

Nothing new. The help is static text.

## Known Issues

- Measured in Chromium only. There a click on the help's words keeps the focus in the dialog (V0.20.179); where a browser leaves it on the page's body, the window's guard keeps the keys from the page, and vitest covers that (ShortcutHelp).
- Counted by radius, padding, border and background, the details still draw three kinds of box for the garden and two for a bed (V0.20.179): each panel keeps its own padding, and the list of what is drawn and the suggestion window are rows.
- The help's list is written by hand: a key the code starts to answer shows in it only once workspace/shortcuts.ts names it too.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
