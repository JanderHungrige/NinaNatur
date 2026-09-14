---
id: 90-a-list-that-fits-a-window
title: A List That Fits a Window
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-23
wave_status: active
depends_on: [88-what-the-selection-shows, 23-catalogue-filters, 25-woody-and-birds, 15-timeline-ui]
relates: [24-month-suggestions, 22-species-info, 87-a-workspace-not-a-page]
source_files:
  - frontend/src/suggestions/window.ts
  - frontend/src/suggestions/months.ts
  - frontend/src/suggestions/focus.ts
  - frontend/src/components/SuggestionList.tsx
  - frontend/src/components/SuggestionWindow.tsx
  - frontend/src/components/SuggestionRow.tsx
  - frontend/src/components/MonthStrip.tsx
  - frontend/src/components/FilterControls.tsx
  - frontend/src/components/BedDetails.tsx
  - frontend/src/api/client.ts
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/suggestions/window.test.ts
  - frontend/src/suggestions/months.test.ts
  - frontend/src/components/SuggestionWindow.test.tsx
  - frontend/src/components/SuggestionRow.test.tsx
  - frontend/src/components/MonthStrip.test.tsx
  - frontend/src/components/SuggestionList.test.tsx
  - frontend/src/components/FilterControls.test.tsx
  - frontend/src/App.list.test.tsx
  - frontend/src/App.test.tsx
  - frontend/src/App.details.test.tsx
  - frontend/src/api/client.test.ts
  - tests/test_workspace_layout.py
data_flow: mixed
last_synced: 2026-09-14
status: in_progress
phase: 6
mdd_version: 11
tags: [suggestions, virtual-list, keyboard, filters, accessibility, workspace]
path: Workspace/Inspector
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "frontend/src/api/client.ts was 591 lines before this feature, over the 300-line limit. The one change here, the default limit, leaves it at 591; splitting it by concern is a task of its own."
---

# 90 — A List That Fits a Window

Feature 4 of Wave 23, the second half of stage 2. The suggestions stop being a
page and become a window: compact rows, only the visible ones in the document,
the filters in the list's own header, and a keyboard that reaches every row
without the page moving.

## Purpose

The suggestions are what a bed is chosen for, and they were the longest thing
in the app: 28 rows of about 240 px each, 7,480 px of details with a bed chosen
at 1280×720 (preview, V0.20.159) and 6,725 px for the panel alone on a phone
(plan 05). Every row was a small panel repeating the same labels. Nothing about
what is ranked changes here — `rank_plants` is untouched — only how the ranking
is shown, and how far down it can be read.

## Architecture

```
BedDetails (a bed selected)
└─ SuggestionList            section "Vorschläge für <bed>"
   ├─ header                 what is listed, of how many · the active filters as chips (FilterBar)
   │                         · Filter (FilterControls, in a disclosure) · the birds note, once
   ├─ SuggestionWindow       role=list, scrolls in itself, only the rows in view in the DOM
   │  └─ SuggestionRow       name (opens Info) · + · colour dot and word · months strip
   │                         · fit badge · room and birds on a third line
   └─ Gehölze für diesen Standort   its own heading and its own window (at most eight)
```

- `suggestions/window.ts` is the arithmetic: which rows a scroll position shows,
  where to scroll so a row is shown, and how many rows a page is. Pure, and
  tested without layout.
- `suggestions/months.ts` turns a flowering start and end into months, wrapping
  across the new year as `bloom/timeline.py::flowering_months` does.
- `suggestions/focus.ts` says where the focus is. It is read while rendering,
  before the commit that may remove the row holding the focus; once that row is
  gone, nothing says where the focus had been.
- `MonthStrip` draws twelve cells with the flowering months filled, and names
  the months in words for a screen reader.
- `SuggestionWindow` measures its own height and one row's, renders the rows in
  view, five above and below, and the row holding the tab stop, places each at
  its index times the row height, and moves one tab stop across all rows.
- `FilterBar` is rehung into the list's header unchanged; `FilterControls` goes
  behind a *Filter* disclosure.

## Data Model

None.

## API Endpoints

None changed. `client.bedSuggestions` asks for `limit=50` by default instead of
20 (the route's range is 1–100).

## Business Rules

1. **Fifty, not twenty.** The client asks for fifty herbaceous suggestions; the
   woody shortlist stays at eight and the ranking is untouched. The window is
   what makes a longer list affordable, and the wave's acceptance names a garden
   with fifty suggestions.
2. **Only the rows in view are in the document**, plus an overscan of five above
   and below, and the row holding the tab stop wherever the list is scrolled.
   With fifty suggestions fewer than thirty rows exist at once. Every row of a
   window has one height, set in the stylesheet and measured once from a
   rendered row, so the arithmetic is exact.
3. **The list says how long it is.** `role="list"`, and every row carries
   `aria-setsize` and `aria-posinset`, so a screen reader hears where it is in
   fifty although twenty rows are in the document.
4. **One tab stop, every row in reach.** Arrow keys move a row, Home and End to
   the ends, Page Up and Page Down by the whole rows a window holds. The row
   about to take the focus is scrolled into the window first, so it exists when
   it is focused. Tab from a row reaches its name and its *+*.
5. **A compact row says what the panel-row said**, in less room. First line: the
   name, which is the button that opens what is known about the species
   ("Informationen zu …"), and *+*, which plants it and is named "… pflanzen".
   Second line: the colour as a dot and its German word — the gardener's own
   marked "von dir", unknown a neutral dashed dot and "Farbe unbekannt"
   (doc 15); the flowering months as a strip, wrap-aware, named in words
   ("Blüte Juni bis Juli", or "Blühzeit unbekannt"); the fit as a badge naming
   its weakest axis ("Feuchte grenzwertig", or "optimal"), with every axis in
   its title and for a screen reader. Third line, in every row of a window where
   any row needs one: "braucht ~N m²" when it does not fit the bed, and the
   birds recorded eating it (doc 25). **The badge is never cut**: it names what
   does not suit the place. Beside it the colour's word and an unknown bloom
   time give way, and the colour's whole word stays in its title. Before this
   rule, on V0.20.170 in the details' 22rem, 11 of 58 badges were cut ("Licht
   p…"), every one beside "Farbe unbekannt", which 47 of the 58 rows say.
6. ***+* stays in reach while its request runs**: `aria-disabled`, presses
   ignored, the focus kept (doc 88, rule 11 — the handoff from feature 2). The
   filter fields in the header do the same: changing one runs a request, and a
   field disabled under the keyboard's focus throws the focus to the page.
7. **The filters are the list's header**: what is listed — the herbaceous
   matches, or "Die 50 passendsten von N Arten" when the window holds fewer than
   matched (`total` counts every herbaceous match before the limit); the active
   filters as chips with what each could not judge (doc 23, unchanged), always
   above the rows; the inputs behind *Filter*. Only the rows scroll, so the
   header never scrolls away from the list it describes.
8. **The woody list keeps its own heading** (doc 25), in its own window.
9. **The window scrolls in itself, and is never taller than the details it
   stands in.** `overflow-y: auto`, positioned so the rows it places and the
   hidden text in them stay inside (doc 89's lesson), and at most
   `min(26rem, 100cqh)`, the details being a size container in the workspace.
   The wheel goes on to the details when the list ends; the details keep their
   own scrolling to themselves, so the page still never moves. Before this
   rule, on V0.20.170 with one species planted at 1280×720, the details were
   320 px and the window 394, and a window that contained its own scrolling
   kept the wheel from the rest of the details.
10. **Planting keeps the list where it was.** Rows are keyed by species, so the
    refetch after *+* leaves the window's scroll where it was. The server leaves
    a planted species out of its bed's suggestions (`exclude_planted`), so the
    row that was pressed is gone: the focus goes to the row that takes its
    place. A list that goes away entirely — a bed's only woody suggestion,
    planted — hands the focus to the list's heading.
11. **No new file is over 300 lines.**

## Data Flow

Traced in `.mdd/audits/flow-a-list-that-fits-a-window-2026-09-14.md` (local):
the same `BedSuggestions` fields the rows showed before, the months now drawn
from `flowering_start_month` and `flowering_end_month` with the wrap the server
already applies, and `limit` the only value that changes. `total` is
`len(herbaceous)` in `ninanatur/api/suggestions.py::_presented`, counted before
the list is cut to the limit.

## Dependencies

- **88-what-the-selection-shows** — the bed's view the list stands in.
- **23-catalogue-filters** — the filters and what they dropped.
- **25-woody-and-birds** — the woody list, the room, the birds.
- **15-timeline-ui** — unknown stays unknown.
- Related: **24-month-suggestions**, **22-species-info**,
  **87-a-workspace-not-a-page**.

## Security

Nothing new: the same request with a larger page, well inside the route's own
bound of 100.

## Known Issues

- `frontend/src/api/client.ts` was 591 lines before this feature, over the
  300-line limit. The one change here, the default limit, leaves it at 591;
  splitting it by concern is a task of its own.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
