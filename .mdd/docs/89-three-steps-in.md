---
id: 89-three-steps-in
title: Three Steps In
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-23
wave_status: active
depends_on: [88-what-the-selection-shows, 87-a-workspace-not-a-page, 48-garden-soil, 34-sightlines, 84-what-else-is-standing-there]
relates: [53-account-in-header, 30-landing-and-garden-id, 65-the-shade-switch]
source_files:
  - frontend/src/components/FirstSteps.tsx
  - frontend/src/components/GardenDetails.tsx
  - frontend/src/components/InspectorPanels.tsx
  - frontend/src/components/GardenWorkspace.tsx
  - frontend/src/components/InsectScore.tsx
  - frontend/src/components/BloomTimeline.tsx
  - frontend/src/components/BedPlantings.tsx
  - frontend/src/components/ElementList.tsx
  - frontend/src/canvas/shapes.ts
  - frontend/src/components/ToolRail.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/CanvasControls.tsx
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/components/CanopyMarks.tsx
  - frontend/src/components/CanopyBox.tsx
  - frontend/src/components/PlanArea.tsx
  - frontend/src/components/GardenId.tsx
  - frontend/src/garden/useGarden.ts
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/components/FirstSteps.test.tsx
  - frontend/src/App.start.test.tsx
  - frontend/src/components/GardenCanvas.viewpoint.test.tsx
  - frontend/src/components/CanvasControls.test.tsx
  - frontend/src/components/CanopyMarks.test.tsx
  - frontend/src/components/CanopyBox.test.tsx
  - frontend/src/components/ToolRail.test.tsx
  - frontend/src/components/GardenId.test.tsx
  - frontend/src/components/InsectScore.test.tsx
  - frontend/src/components/BloomTimeline.test.tsx
  - tests/test_workspace_layout.py
data_flow: mixed
last_synced: 2026-09-14
status: in_progress
phase: 6
mdd_version: 11
tags: [onboarding, empty-states, sightlines, canopy, account, workspace]
path: Workspace/Inspector
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Six of the new tests pass before the change, on purpose: each is the negative or the guard beside a positive test that fails — no claim offered while nobody is signed in; an armed Standpunkt takes the click from the shapes, and nothing is placed while no tool is armed (doc 49, kept); the plan's controls carry no viewpoint button, and no trees when none were found; and a garden that is set up shows no steps."
---

# 89 — Three Steps In

Feature 3 of Wave 23, the first half of stage 2. The garden's view loses the
panels that stood there for good: a question asked once, two boxes saying that
nothing is planted, a plan mode hidden in the plan's controls, trees that exist
only as a list, and an action on the whole garden in the middle of its details.

## Purpose

After feature 2 the garden's view is still 1,486 px (preview, V0.20.159), and
most of it is waiting: *Boden im Garten* asks a question that is answered once
per garden (doc 48); *Insektenwert* and — in the dock — *Blühjahr* each spend a
panel on "Noch nichts gepflanzt"; *Standpunkt setzen* is a button among the
zoom controls, though it is a way of using the plan; the trees the surface model
found (doc 84) are rows of numbers rather than places on the plan; and claiming
the garden for an account sits among the garden's details rather than beside its
ID. This feature makes the first visit three steps, turns each empty panel into
one line that names the next step, and puts the rest where it acts.

## Architecture

### The first steps, in the garden's view

```
GardenDetails (nothing selected)
├─ BedPanel                       the garden's name, where it is, its beds
├─ FirstSteps                     while a step is open
│  1 Boden                        SoilLine: the question, or one line once said
│  2 Schatten berechnen           the same rebuild as the sun panel's button
│  3 Erstes Beet                  arms Vieleck on the rail
├─ SoilLine                       once every step is done (feature 2's line)
├─ ShadeSwitch                    once a map exists
├─ InsectScore                    one line while nothing is planted
├─ CanopyBox                      the found trees' card
└─ ElementList
```

The steps are read from the garden, not from a flag: soil set, a light map, at
least one bed. A garden made from the map import that already has a bed shows
that step done; a garden that has everything shows no steps at all. The start is
an empty details panel with prompts, as the owner decided on 2026-09-14 — no
overlay before the first look.

### Each empty panel, one line

`InsectScore` with nothing planted, and `BloomTimeline` in the dock, render one
line — what it is, that nothing is planted, and the next step — instead of a
panel. The bloom year's weighting checkbox goes with it: it weighs nothing.
`BedPlantings` and `ElementList` keep their panels and lose directions that the
workspace made wrong: the tools are no longer above the plan, and the
existing-planting form is no longer above the list.

### Where the rest acts

- **Standpunkt is the rail's seventh tool** (`viewpoint`). Armed, a click on the
  plan places the viewpoint and puts the tool down; the answer stands above the
  details as before (doc 88). `GardenCanvas` loses its own `placing` state and
  `CanvasControls` its button.
- **Found trees are marked on the plan.** `CanopyMarks` draws each suggestion's
  crown as a dashed circle where it stands. The plan's controls carry
  *N gefundene Bäume*, which shows the card: the garden's view, with the card's
  heading focused.
- **The claim is in the header's ID fold**, the menu for the whole garden, while
  an account is signed in.

## Data Model

None.

## API Endpoints

None. The same client calls, from new places.

## Business Rules

1. **Three steps while the garden is not set up:** soil, shade, first bed — done
   when `soil_type` and `moisture` are set, when a light map exists, when the
   garden has a bed. Nothing is stored about having seen them.
2. **Each step says whether it is done in words** ("erledigt", "offen"), not only
   by colour or a tick.
3. **Step 1 is doc 48's question, unchanged** — asked once per garden, a null
   until somebody answers, a link out rather than a guess — shown through
   `SoilLine`, so once answered it is already the one line it stays.
4. **Step 2 computes the same map as the sun panel.** While there is no map the
   sun panel is not shown: its only content would be the same button.
5. **Step 3 arms *Vieleck*.** The rail shows it armed and the plan's hint says what
   to do; drawing stays a pointer gesture, as it was.
6. **When every step is done the steps are gone**, and the garden's view shows
   the soil as one line (doc 88).
7. **An empty panel is one line that names the next step.** The words "Noch
   nichts gepflanzt" stay, and no table, chart or checkbox is drawn over nothing.
8. **Standpunkt is a tool like the others** (doc 87, rule 5): in the rail's
   arrow-key order, `aria-pressed` while armed, put down by Escape or by pressing
   it again — and, once the viewpoint is placed, by the placing itself. While it
   is armed the shapes carry no handlers (doc 49): a click places the viewpoint
   rather than selecting what is under it.
9. **The rail's floor grows with the rail.** Seven tools need 20rem; the
   stylesheet guard from the stage 1 fix counts them.
10. **A found tree on the plan is a mark, not an object** (doc 84): a dashed crown
    at `x`, `y` with `radius_m`, hidden from the accessibility tree and from the
    pointer, so it never takes a click from what is beneath it. Accepting or
    refusing it stays in the card, both buttons as prominent as each other.
11. ***N gefundene Bäume* shows the card**: it drops the selection and focuses the
    card's heading. One tree is *1 gefundener Baum*; with none there is no button.
12. **Claiming acts on the whole garden, so it sits with the garden's ID** in the
    header's fold, for a signed-in account, and no longer in the details.
13. **No new file is over 300 lines.**

## Data Flow

Traced in `.mdd/audits/flow-three-steps-in-2026-09-14.md` (local): soil from
`garden.soil_type` and `garden.moisture`, the map from `derived.lightMap`
(`client.lightMap`, `client.rebuildLightMap`), beds from `garden.beds`, found
trees from `derived.canopies` (`client.canopies`), the claim through
`client.claimGarden`, and the viewpoint through `client.sightlines` — every one
read as the panels already read it.

## Dependencies

- **88-what-the-selection-shows** — the garden's view, the details' focus, the
  sightlines above every view.
- **87-a-workspace-not-a-page** — the rail, the plan's controls, the header's fold.
- **48-garden-soil** — the question step 1 asks.
- **34-sightlines** — what the viewpoint tool asks for.
- **84-what-else-is-standing-there** — the found trees the plan marks.
- Related: **53-account-in-header**, **30-landing-and-garden-id**,
  **65-the-shade-switch**.

## Security

Nothing new. The claim moves, and still needs a signed-in account and the
garden's token, as before.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)
