---
id: 88-what-the-selection-shows
title: What the Selection Shows
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-23
wave_status: active
depends_on: [87-a-workspace-not-a-page, 49-drawing-focus, 51-element-context-menu, 52-element-list]
relates: [48-garden-soil, 47-panel-order, 11-garden-canvas, 90-a-list-that-fits-a-window, 91-a-sheet-from-below]
source_files:
  - frontend/src/garden/selection.ts
  - frontend/src/garden/useSelection.ts
  - frontend/src/garden/useGarden.ts
  - frontend/src/garden/useElements.ts
  - frontend/src/garden/useSuggestions.ts
  - frontend/src/garden/useClipboard.ts
  - frontend/src/canvas/useEscapeKey.ts
  - frontend/src/components/InspectorPanels.tsx
  - frontend/src/components/InspectorSubject.tsx
  - frontend/src/components/GardenDetails.tsx
  - frontend/src/components/BedDetails.tsx
  - frontend/src/components/ElementDetails.tsx
  - frontend/src/components/PlantingDetails.tsx
  - frontend/src/components/ElementForm.tsx
  - frontend/src/components/SoilLine.tsx
  - frontend/src/components/PlanArea.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/components/ClusterLayer.tsx
  - frontend/src/components/BedPanel.tsx
  - frontend/src/components/SpeciesInfo.tsx
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/garden/selection.test.ts
  - frontend/src/App.selection.test.tsx
  - frontend/src/App.details.test.tsx
  - frontend/src/App.test.tsx
  - frontend/src/components/ElementForm.test.tsx
  - frontend/src/components/SoilLine.test.tsx
  - frontend/src/canvas/useEscapeKey.test.ts
  - frontend/src/components/ClusterLayer.test.tsx
  - frontend/src/components/SpeciesInfo.test.tsx
  - frontend/src/components/GardenCanvas.focus.test.tsx
  - tests/test_workspace_layout.py
  - frontend/src/testing/gardens.ts
  - frontend/src/testing/appFixtures.tsx
data_flow: mixed
last_synced: 2026-09-14
status: complete
phase: all
mdd_version: 11
tags: [inspector, selection, router, focus, keyboard, accessibility, refactor]
path: Workspace/Inspector
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Pflanzen, Entfernen and Eintragen in the rehung panels still use `disabled` while a request runs, so pressing one from the keyboard drops the focus to the page — measured after Pflanzen on the preview (V0.20.158). The element form does not; feature 4 rebuilds the suggestion rows the same way."
  - "The dock grows when the bloom year gains its first plant: at 1280×720 the details lost 103 px of height when the first plant arrived. Within doc 87's 40vh; feature 6's month strip is meant to give the dock one height."
  - "Below 66rem the details are part of the page, so choosing on the plan does not bring them into view — feature 5's sheet."
  - "GardenCanvas (380 lines) and CanvasScene (383 lines) were over the 300-line rule before this feature; it added a prop to each and an attribute to the scene."
  - "Since doc 90 (Wave 23, 2026-09-14) the suggestion rows' + and the filter fields stay focusable and aria-disabled while a request runs. Entfernen (BedPlantings) and Eintragen (ExistingPlanting) still use disabled."
  - "Since doc 91 (Wave 23, 2026-09-14) below 66rem the details are a sheet from below that rests at a quarter, where the name of whatever is chosen on the plan shows at once."
---

# 88 — What the Selection Shows

Feature 2 of Wave 23, and the second half of stage 1. The details panel stops
holding everything at once. It shows what is selected — the garden when nothing
is, a bed, an element, or a patch of plants — and the selection it follows is
one value that the plan, the element list and the details all read.

## Purpose

After feature 1 the details held every panel in one column, because doc 87 left
the routing to this feature: 1,962 px of them before a bed was chosen and
8,754 px after (preview, V0.20.155). The selection itself was five pieces of
state that could disagree, and did. A bed chosen in the list lost its handles.
An element clicked after a bed left the bed marked as selected. Escape left the
bed selected for planting. This feature makes the selection one value and lets
it decide what the details show, so choosing something puts that thing, and
nothing else, beside the plan.

## Architecture

### One selection

```
useSelection — composed first in useGarden
  picked     { what: 'element' | 'planting', id } | null    the only state
  selection  resolveSelection(garden, picked)                read from the garden on every render
             none | bed {bed} | element {element} | planting {planting, bed}
  ids        selectedIds(selection)                          what the plan draws with
             bedId       the bed, when a bed is selected
             elementId   the bed or element wearing handles
             plantingId  the patch
```

- **Picked by id, resolved against the garden.** An element whose kind becomes
  *Blumenbeet* moves from `obstacles` to `beds` in the server's answer. The pick
  is the same element id, so it becomes a bed selection without being picked
  again. Something deleted or undone resolves to nothing.
- `useSuggestions`, `useClipboard` and `useElements` are handed the selection
  instead of each holding a piece of it.

### The details as a router

```
aside.inspector "Details"
└─ div.inspector__view
   ├─ Sightlines          while a viewpoint has an answer — above any view
   └─ one of
      ├─ GardenDetails    nothing selected
      ├─ BedDetails       a bed
      ├─ ElementDetails   an element that is not a bed
      └─ PlantingDetails  a patch of plants
```

| Selection | The details show |
|---|---|
| nothing | BedPanel (the garden's name, where it is, its beds) · the soil in one line, the question behind *ändern* · the claim button · the sun map's settings · the insect score · trees found nearby · the element list |
| a bed | its subject line · *Beet bearbeiten*, the element form folded away · what is planted in it · species info when asked for · the filters · the suggestions · the existing-planting form |
| an element | its subject line · the element form |
| a patch | its subject line · species info with the colour note, or a line saying the catalogue does not know the plant |

Every view but the garden's starts with `InspectorSubject`: an `h2` naming the
thing, one line saying what it is and what it covers, and the way back —
*Zurück zum Garten* from a bed or an element, *Zurück zu <bed>* from a patch.

### Rehung, and what changes

- **`ElementMenu` becomes `ElementForm`.** The same fields, the same saving and
  the same two-step delete, as a section of the details instead of a popover
  over the plan. It no longer anchors to the shape or closes on an outside
  click or Escape, so `useAnchoredMenu` and its test lose their only caller and
  go. The subject line it opened with moves to `InspectorSubject`.
- **`SoilLine`** shows the garden's soil as one line once it has been said, with
  `GardenSoil` behind *ändern* (`aria-expanded`). While the garden has no soil it
  is `GardenSoil` itself, as doc 48 asks. `GardenSoil` is untouched.
- **`SpeciesInfo`** takes `takeFocus` (default `true`). As the details of a
  selected patch it is already where the reader is, so there it neither scrolls
  nor takes the focus from the plan. It is handed the workspace's client instead
  of reaching for its module-level one.
- **`BedPanel`'s heading** is the garden view's heading when focus moves to it.
- **`CanvasScene`** marks the selected element `aria-pressed`, as it already
  marked the selected bed.
- **`ClusterLayer`** marks a patch that was just planted with `cluster--fresh`.
  The plan no longer offers the tag's "i": a selected patch's species is already
  in the details.
- **`GardenCanvas`'s Escape listener** moves to `useEscapeKey`, which leaves
  Escape typed into a text field to that field.
- **`testing/gardens.ts` and `testing/appFixtures.tsx`** hold the gardens and
  the fake client the App flow tests share; `App.test.tsx` imports them instead
  of defining its own.

## Data Model

None.

## API Endpoints

None. The same client calls, from new places.

## Business Rules

1. **One selection.** Nothing, a bed, an element or a patch — exactly one of
   them is selected. The plan, the element list and the details read that one
   value, and nothing else holds a piece of it.
2. **The same thing is the same selection, wherever it was chosen.** A bed chosen
   on the plan, in BedPanel or in the element list is selected for planting and
   wears its handles.
3. **Choosing one thing unchooses the rest.** An element chosen after a bed
   leaves the bed unmarked on the plan and its suggestions gone from the
   details; a patch chosen leaves its bed unmarked.
4. **The details follow the selection,** as the table above says.
5. **The suggestions follow the selected bed.** They are requested when the
   selected bed's id changes: one effect keyed on that id, with the filters read
   from a ref. A bed selected by any route therefore gets them — including an
   element just given the kind *Blumenbeet*. It is not an effect keyed on the
   filters, the loop this project has already paid for once; changing a filter
   still refetches explicitly. While they load the view says so, and if they
   fail it says that too, beside the toast. A species panel opened for one bed
   closes when another bed is selected.
6. **What was just drawn is selected:** an element, as before, and now also a
   bed drawn with *Vieleck*, so the next thing the details show is the bed to
   plant in.
7. **Escape drops the selection** and puts the tool down (doc 49) — from
   anywhere except a text field. Escape typed into a text or number input, a
   textarea or an editable element belongs to that field. A select, a checkbox
   or a button is not a text field.
8. **Right-click, Shift+F10 and the context-menu key ask about an element**
   (doc 51). The element is selected and the focus moves into its form's first
   field; a bed's form unfolds first. An armed tool still suppresses all of it:
   while one is armed the shapes carry no handler (docs 49, 51).
9. **Focus follows a change of view only from inside the details.** If the focus
   was in the details, or was lost because the control holding it went with the
   old view, it moves to the new view's heading. Anywhere else — on the plan,
   above all — it stays: choosing on the plan never pulls the keyboard away.
   Either way the new view opens at its top. The details scroll in themselves,
   and keeping the last view's offset opened a patch's view 190 px down after
   planting from the suggestions, its heading out of sight (preview, V0.20.158).
10. **Saving says so, and stays.** After *Übernehmen* the form stays and the
    toast says "<Art> gespeichert." *Abbrechen* leaves an element, back to the
    garden, and folds a bed's form away.
11. **The element form stays in reach while a request runs.** Its fields are
    never disabled, and its buttons stay focusable, `aria-disabled`, and ignore
    presses — doc 87's rule for the rail. A disabled control cannot hold the
    focus: every request would throw the keyboard out of the form, and
    Shift+F10 could not put it there while a bed's suggestions load.
12. ***Pflanzen* marks the patch on the plan.** After planting from the
    suggestions or from the insect score's advice, the patch that received the
    plant is `cluster--fresh` for 2.4 seconds — a pulse, or under
    `prefers-reduced-motion` a still ring. The details stay on the bed, and
    nothing scrolls.
13. **The bloom year is not repeated.** The wave's table asked for a miniature
    of it in the garden's view. The dock under the plan already shows it,
    whatever is selected, so the garden's view does not.
14. **The list belongs to the garden.** The element list stands in the garden's
    view, and every other view has one button back to it. Under a bed's
    suggestions it would sit thousands of pixels down until feature 4.
15. **No new file is over 300 lines.**

## Data Flow

Traced in `.mdd/audits/flow-what-the-selection-shows-2026-09-14.md` (local):
the five pieces of state before, the four disagreements read off the code, and
every value the views show. None of them is transformed differently from the
panel it came from — the subject lines use ElementList's area and words and
BedPanel's light text.

## Dependencies

- **87-a-workspace-not-a-page** — the details panel this routes, and `useGarden`.
- **49-drawing-focus** — Escape, and an armed tool taking the click.
- **51-element-context-menu** — the keyboard's way to ask about an element. The
  menu itself becomes the form.
- **52-element-list** — one selection, whichever way it was reached.
- Related: **48-garden-soil** (asked once, one line afterwards),
  **47-panel-order**, **11-garden-canvas**.

## Security

Nothing new: no input, storage or network beyond what the rehung components
already do. The species lookup goes through the injected client.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
