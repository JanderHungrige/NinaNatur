---
id: ninanatur-wave-23
title: "Wave 23: The plan is the page"
initiative: ninanatur
initiative_version: 23
status: in_progress
depends_on: ninanatur-wave-20
demo_state: "Der Plan füllt den Bildschirm — Werkzeuge links, Details zur Auswahl rechts, die Zeit unten. Beet wählen, Art wählen, die Pflanze im Plan sehen: ohne dass die Seite scrollt, am Schreibtisch wie auf dem Telefon, wo die Details als Blatt von unten kommen. Und der Plan schrumpft nie mehr zu einem Strich."
created: 2026-09-07
hash: 3ab57e86
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

## Progress

- **2026-09-14 — feature 0, the plan that stayed a strip** (doc 86). The loop
  is broken where it closed: `useViewport` measures the stage the drawing sits
  in, the stage takes its height from the page — `clamp(16rem, 75vh, 75cqi)` —
  and the drawing fills it, so nothing drawn can change what is measured. A zero
  or non-finite measurement is ignored and a real one is taken exactly: a floor
  under a real box would letterbox the drawing and move every click, so the
  floor is the stage's 16rem instead. Above the two-column breakpoint the plan's
  column is sticky and scrolls itself. The status line is a toast whose live
  region is always in the page, and a failure stays until it is closed.
  Measured on the preview (V0.20.151) by DOM, since the Browser pane cannot
  capture the plan: at 1280×720 the drawing and its stage are one 840×540 box
  and the viewBox has their shape (0.6429); scrolled 700 px, the plan column
  holds at 16 px with the plan wholly in view; opened in a 1280×300 window the
  plan stops at 256 px instead of collapsing, and grown to 1280×900 without a
  reload it follows to 630 px with the viewBox at 0.75; on a 375×812 phone,
  one column, nothing sticky, a 343×257 plan and no sideways scroll. The pane
  was hidden, which holds a resize and a transition back until the page gets a
  frame; waiting for one showed both arrive. In production as V0.20.152, the
  live bundle carrying the stage, the plan column and the toast. The Playwright
  smoke test the acceptance names is not written yet: the workspace it measures
  is feature 1's. Thirteen new tests: `canvas/viewportSize.test.ts`,
  `GardenCanvas.stage.test.tsx`, `StatusToast.test.tsx` and
  `tests/test_plan_stage.py`.

- **2026-09-14 — feature 1, a workspace, not a page** (doc 87). `App.tsx` went
  from 1,459 lines to 256: everything about one garden now lives in `useGarden`
  — `useDerived`, `useSuggestions`, `useClipboard`, `useElements`, `useGeometry`,
  `useLight` — inside a workspace keyed by the garden's token, so nothing of one
  garden carries into the next, and `App` takes its client as a prop and has
  flow tests at last. At 66rem and wider the garden is the window: header, tool
  rail, plan, details and a dock for the bloom year, and only the details and
  the dock scroll. Measured on the preview (V0.20.155) by DOM at 1280×720: the
  page is exactly 720 px tall with nothing sideways; one banner, main,
  complementary and contentinfo; columns 56 / 872 / 352 px, the plan 50.4 % of
  the window. With a bed chosen the details hold 28 suggestions in 8,754 px and
  the page stays 720 px; scrolled to their end, the window stays at the top.
  At 1440×900 the wide view widened the details from 352 to 480 px without the
  page scrolling, and was remembered; on a 375×812 phone the workspace stacks
  rail, plan, details and dock with nothing sideways. Found on the way: the
  rail's hidden tool names had no offsets and sat over the next tool, so a
  click aimed at one name armed its neighbour — they are pinned inside their
  own buttons now; and a garden made from the map had what the map measured
  overwritten by the plainer "geladen", so the workspace is told what to say.
  The Browser pane listed the rail's six buttons without names. Chrome's own
  tree, read over CDP, named them from the hidden text all along — the commit
  that added `aria-label` blames Chrome and is wrong — and the label now makes
  both trees agree (V0.20.156). The Browser pane's Enter arrives with an empty
  key, so a native Enter on a tool was not exercised; a real ArrowDown, click
  and Escape were. Not released on its own: features 1 and 2 go to production
  together. Thirty-six new tests: `App.test.tsx`, `ToolRail.test.tsx`,
  `TimelineDock.test.tsx`, `Inspector.test.tsx`, `useRemembered.test.ts` and
  `tests/test_workspace_layout.py`.

- **2026-09-14 — feature 2, what the selection shows** (doc 88). The details
  show one thing at a time — the garden while nothing is selected, or the bed,
  the element or the patch that is — and what is selected is one picked id, read
  against the garden on every render, so the plan, the element list and the
  details can no longer disagree. Five pieces of state did: a bed chosen in the
  list lost its handles, an element chosen after a bed left the bed marked, and
  Escape left the bed selected for planting. The element menu became the element
  form in the details. Measured on the preview in Chromium with real keys at
  1280×720 (V0.20.159): with nothing selected the details hold 1,486 px, where
  every panel at once had been 1,962 px. Enter on the bed on the plan shows the
  bed with its handles and 28 suggestions in 7,480 px, Chrome's own tree calls
  the bed pressed, and the focus stays on the plan. The same bed chosen in the
  element list gets the same selection, handles included, and the focus moves to
  the bed's heading. Escape goes back to the garden from the plan and from the
  details; an element chosen after the bed leaves only the element pressed;
  Shift+F10 and a right-click put the focus in the form's *Art*, and on the bed
  the form unfolds for it while the suggestions load; Escape typed into a text
  field leaves the selection alone. *Pflanzen* marked the new patch on the plan,
  the mark was gone three seconds later, the details moved by 7 px and the page
  not at all. Found on the way: a patch chosen after planting opened its view
  190 px down with its heading out of sight, because the details kept the last
  view's offset — a new view now opens at its top; *Pflanzen* is `disabled`
  while its request runs and drops the keyboard's focus to the page, handed to
  feature 4; and the dock grows by 103 px when the bloom year gains its first
  plant. On a 375×812 phone nothing goes sideways. The console holds only the
  account check's expected 401. Stage 1 — features 1 and 2 — goes to production
  together. Fifty new tests in vitest and one in pytest; the popover's eight
  tests and the anchoring's six went with them, and eleven moved into
  `ElementForm.test.tsx`.

- **2026-09-14 — stage 1 in production.** Features 1 and 2 went to production
  together as V0.20.161, its bundle carrying the workspace, the view headings,
  *Zurück zum Garten*, *Beet bearbeiten* and the fresh-patch mark. Measuring the
  planted state before recording it found the plan short of its share: with one
  species planted the bloom year filled the dock's 40vh, and the plan's stage
  measured 260 px of 720 (36 %), 286 of 800 and 346 of 900 on the preview
  (V0.20.159); at 600 px the plan's row, held up by the tool rail, ran 94 px
  under the dock. Doc 87 had counted the dock and forgotten the header, the
  preview band and the dock's own bar. The plan's row now keeps `max(40vh +
  1rem, 18rem)` and the dock gives way: on the preview (V0.20.162) the stage
  measured 288 px of 720, 320 of 800 and 360 of 900 — 40 % each — and 272 of
  600, the plan inside its row every time and the page never scrolling. A guard
  computes the rail's height from the stylesheet and the tool count, so feature
  3's new rail tool cannot outgrow the floor unnoticed. In production as
  V0.20.164, its stylesheet carrying the row's floor.

- **2026-09-14 — feature 3, three steps in** (doc 89). A garden that is not set
  up opens on three steps in its details — soil, shade, a first bed — read from
  the garden and gone once all three are done; the owner chose prompts in the
  details over an overlay. The empty insect score and the empty bloom year are
  one line each that names the next step, *Standpunkt* is the rail's seventh
  tool, found trees are dashed crowns on the plan with *N gefundene Bäume* among
  its controls, and claiming a garden for an account sits in the header's ID
  fold. Measured on the preview in Chromium (V0.20.167). On a garden made for
  the check: all three steps open and no sun panel; *Beet zeichnen* armed
  *Vieleck*, four clicks and *Fertig* drew a bed, which the details then showed;
  back in the garden the bed's step was done; *Schatten berechnen* computed the
  map, ticked its step and brought the sun panel; answering the soil made the
  steps disappear and left *Boden: lehmig, frisch* as one line. On the stage 1
  garden: the empty bloom year is one line in a 26 px body where it was 163;
  *Standpunkt* armed from the rail and a click on the plan placed the viewpoint,
  put the tool down and put the answer above the details; the plan drew 6 found
  trees as crowns, and *6 gefundene Bäume*, with a bed selected, brought back
  the garden's details with the card's heading focused. With seven tools the
  rail's floor is 20rem, and with one species planted the plan's stage measured
  304 px of 720 (42.2 %). Found on the way: at 1280×600 the page was 628 px
  tall, because the bloom year's visually hidden table caption, absolutely
  positioned far down the dock's scrolled body, had the page as its containing
  block and escaped the panel. The details and the dock's body are positioned
  now, and on V0.20.168 the page is exactly the window's height at 600, 720, 800
  and 900. The console holds only the account check's 401; the claim needs a
  signed-in account and was checked in vitest only. Thirty-one new tests and a
  stylesheet guard: `FirstSteps`, `CanopyMarks`, `CanvasControls`,
  `GardenCanvas.viewpoint`, `App.start`, additions to `GardenId`, `CanopyBox`,
  `InsectScore` and `BloomTimeline`, and `tests/test_workspace_layout.py`.

- **2026-09-14 — feature 4, a list that fits a window** (doc 90). A bed's
  suggestions are a window in its details: fifty compact rows — the name, which
  opens what is known about the species, *+*, the colour, the flowering months
  as a strip, a fit badge naming the weakest axis, room and birds — with only
  the rows in view in the document, one tab stop across all of them, the filters
  in the list's own header and the woody plants in a window of their own. The
  client asks for fifty suggestions instead of twenty; the ranking is untouched.
  Measured on the preview in Chromium (V0.20.171) on the stage 1 garden at
  1280×720: *Die 50 passendsten von 2.549 Arten*; the arrow keys walked all
  fifty in order with at most 16 rows in the document, and the page never
  scrolled; row forty's *+* was reached with seven Page Downs, four arrows and
  two Tabs, inside the window and the viewport. Pressing it kept the focus on it
  while the request ran; *Matricaria chamomilla* left the list (2,549 matches,
  then 2,548), and the focus went to *Saxifraga adscendens*, which took its
  place. The bloom year the planting gave the dock shrank the details from 516
  to 320 px and the window from 414 to 294, and the focused row stayed in view.
  Choosing *blüht im Juni* in the header kept the focus on the field (1,160
  matches), and taking the chip off handed it to the list's heading. Chrome
  names the lists *Vorschläge* and *Gehölze*, a row's button *Saxifraga
  adscendens pflanzen* and its strip *Blüte Juni bis August*. With a bed chosen
  the details hold 2,261 px, where they held 7,480 (V0.20.159). Found on the
  way, on V0.20.170: with one species planted the details were 320 px and the
  window 394, and its contained scrolling kept the wheel from the rest of the
  details; and in the details' 22rem 11 of 58 fit badges were cut, every one
  beside *Farbe unbekannt*, which 47 of the 58 rows say. The details are a size
  container now, the window is at most their height and lets the wheel go on to
  them, and the colour's word gives way before the badge does: on V0.20.171,
  with the dock full, the window is 294 px in 320 px of details, the wheel over
  it moved the details from 716 to 1694 px once the list had ended, no badge is
  cut, and eleven colour words are. Fifty-eight new tests and two stylesheet
  guards: `window`, `months`, `MonthStrip`, `SuggestionRow`, `SuggestionWindow`,
  `App.list`, additions to `SuggestionList`, `FilterControls` and the client,
  and `tests/test_workspace_layout.py`.

- **2026-09-14 — stage 2 in production.** Features 3 and 4 went to production
  together as V0.20.173 (merge 1d1f1c2), with the fixes their measurements found
  on the preview: the hidden caption that stretched the page, and a suggestion
  list taller than its details whose fit badges were cut. CI on main passed, and
  production serves the stylesheet measured on the preview as V0.20.171
  (`index-1BDQlzqN.css`).

- **2026-09-14 — feature 5, a sheet from below** (doc 91). Below 66rem the
  garden is the window instead of a page: one header row with the rest behind
  *Menü*, the plan filling what the details leave, the tools as a bar at the
  window's foot, the year as a strip above it, and the details as a sheet from
  below that rests at a quarter and rises to 60 or 90 %. The dock stays the
  page's contentinfo, so its strip sits above the bar and not on the sheet as
  the wave sketched. Before, on V0.20.171 in an iPhone 11 Pro's 375×635 window,
  the garden was a page of 3,069 px with a header of 199 px; a bed tapped on the
  plan filled details 832 px down, and the first *+* was 1,199 px of scrolling
  away from the plan. Measured on the preview in Chromium (V0.20.177), same
  window, touch: the page is the window (635 of 635 px), the header one row of
  61 px, and at rest the plan's stage keeps 46.8 % (53 % at 375×812); a bed
  tapped on the plan says *Südbeet* in the resting sheet; a slow drag of the
  handle raised the sheet to 60 % (247 of 411 px), and three species planted
  from there each left a patch seen on the plan with nothing over it; dragged to
  90 %, the header, the plan, the tools and the year were inert and the focus in
  the sheet, Escape brought it back to 60 % with *Südbeet* still shown, and End
  on the handle took it up again. *Menü* opened over the plan with *Sonne &
  Schatten*, *Rückmeldung* and *Anmelden* and closed at a touch outside; the
  year's table opened upward from its strip and folded again; the seven tools
  stood in a bar at the window's foot. At 1280×720 the wide workspace keeps doc
  87's shape: no handle and no *Menü*, and with the species taken out again the
  plan's stage holds 69.5 %. Found on the way: the first deploy stopped in CI,
  where the full suite's stylesheet test found `--sheet-drag` used but never
  declared — it is set inline, and declared it would keep the sheet from falling
  back to its resting height; only the layout guards had been run locally. On
  V0.20.176, at 60 % the plan's 153 px lay under its controls in two rows and
  its hint in two lines, and a toast lay over undo and *Menü* for its five to
  fifteen seconds. The controls keep to one row now (37 px), the hint makes way
  while the sheet is raised, and the toast keeps to the left and lets a touch
  through. A flick is not measured on the preview: the protocol's round trips
  make every drag slow, and there the flick meant for 90 % rested at 60 %;
  vitest covers it. Forty-three new tests and ten stylesheet guards: `sheet`,
  `SheetHandle`, `SiteHeader`, `App.sheet`, additions to `Inspector`, and
  `tests/test_narrow_workspace.py`.

## Features
| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | the-plan-that-stayed-a-strip | docs/86-the-plan-that-stayed-a-strip.md | complete | — |
| 1 | a-workspace-not-a-page | docs/87-a-workspace-not-a-page.md | complete | 0 |
| 2 | what-the-selection-shows | docs/88-what-the-selection-shows.md | complete | 1 |
| 3 | three-steps-in | docs/89-three-steps-in.md | complete | 2 |
| 4 | a-list-that-fits-a-window | docs/90-a-list-that-fits-a-window.md | complete | 2 |
| 5 | a-sheet-from-below | docs/91-a-sheet-from-below.md | complete | 2 |
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

Decided with the owner on 2026-09-14: the start is an empty inspector with
prompts — no modal before the first look — rather than an overlay.

### 4. a-list-that-fits-a-window

The suggestion list is virtualised (only the visible ~20 rows in the DOM),
rows become compact — name · colour dot · bloom months as a strip · fit badge ·
*+* — filters become chips in a sticky header **inside** the panel, and the
woody list keeps its own heading. The 6 725 px become a window. Nothing about
what is ranked changes; `rank_plants` is untouched.

Tests: fifty suggestions render fewer than thirty rows; keyboard navigation
through the virtual list reaches every item; the *Pflanzen* button of row forty
is reachable without page scroll.

Found in feature 2 (preview, V0.20.158): *Pflanzen* is `disabled` while its
request runs, so pressing it from the keyboard drops the focus to the page. The
compact rows keep their buttons focusable and `aria-disabled` while busy, as the
element form does (doc 88, rule 11).

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

Answered by the owner on 2026-09-14, before any of it was built:

- **The tabs go entirely.** The inspector follows the selection; *Zeichnen*
  and *Säen* do not survive as inspector tabs either.
- **Tools left, details right**, as every editor does.
- **The start is an empty inspector with prompts** (feature 3), not an overlay.

Decided in feature 1 (doc 87, rule 9): two fixed widths — 22rem, and 30rem on
request from 74rem — rather than a drag handle. The range plan 05 named is too
narrow to be worth a gesture, and a toggle is one keyboard stop whose state a
screen reader can name.

## Deliberately not in this wave

- A new drawing style. That is Wave 24, and it needs this shell to be stable
  first, because the theme interface lives in the canvas this wave rehangs.
- Any change to what is ranked, scored or suggested.
- A design system beyond tokens. One consistent panel is the goal; a component
  library is not.
