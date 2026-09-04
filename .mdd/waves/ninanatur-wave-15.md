---
id: ninanatur-wave-15
title: "Wave 15: What is in the bed, and getting it out again"
initiative: ninanatur
initiative_version: 20
status: planned
depends_on: ninanatur-wave-14
demo_state: "Ein Beet anklicken zeigt, was darin steht — jede Art einzeln wieder entfernbar. Das Gesäte steht als graue Punktcluster im Beet, so dass man sieht wie voll es ist; ein Cluster lässt sich anklicken, benennen, innerhalb der Beetgrenzen verschieben und zwischen Beeten kopieren. Das Rechtsklick-Menü bleibt am Objekt und im Bild, Beete lassen sich weiter umformen, die Gartenfläche ist kein Beet mehr, und Ctrl+Z nimmt die letzte Zeichenaktion zurück."
created: 2026-09-04
hash: b11b7e61
---

# Wave 15: What is in the bed, and getting it out again

## Demo-State

Ein Beet anklicken zeigt, was darin steht — jede Art einzeln wieder entfernbar.
Das Gesäte steht als graue Punktcluster im Beet, so dass man sieht wie voll es
ist; ein Cluster lässt sich anklicken, benennen, innerhalb der Beetgrenzen
verschieben und zwischen Beeten kopieren. Das Rechtsklick-Menü bleibt am Objekt
und im Bild, Beete lassen sich weiter umformen, die Gartenfläche ist kein Beet
mehr, und Ctrl+Z nimmt die letzte Zeichenaktion zurück.

*(This wave is not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | menu-that-stays-put | — | planned | — |
| 2 | a-bed-is-still-a-shape | — | planned | — |
| 3 | garden-is-not-a-bed | — | planned | — |
| 4 | undo-with-ctrl-z | — | planned | — |
| 5 | what-is-planted-here | — | planned | — |
| 6 | planting-clusters | — | planned | 5 |

Six rather than the seven reported: the colour bands are the same change as the
grey dots, and both are feature 6. Delivery is in two merges — 1 to 4 first,
because they are small and immediately felt, then 5 and 6.

## What each one is

### 1. menu-that-stays-put

**Reported:** the right-click window is not fixed to the bed; when it hangs off
the bottom of the screen you cannot see it, and scrolling does not bring it
back.

**Found:** `.element-menu` is `position: fixed` at the click's `clientX/clientY`
(`ElementMenu.tsx:102`, `CanvasScene.tsx:259`). Nothing clamps it to the
viewport, so a right-click near the bottom puts half the menu below the fold —
and because `fixed` ignores scrolling, scrolling cannot reveal it. Meanwhile the
bed *does* move, so the menu drifts away from the thing it is about.

**To do:** anchor to the element's own box, flip above/left when it would
overflow, clamp to the viewport as the last resort, and follow the element when
the page scrolls or the plan pans. Never off-screen, never detached.

### 2. a-bed-is-still-a-shape

**Reported:** once an object is labelled *Blumenbeet*, its shape can no longer
be changed the way other shapes can.

**Found:** `GardenOut` keeps beds and obstacles in two arrays. `CanvasScene`
merges them for drawing (`asElement`), but `GardenCanvas` looks up the selected
element in `garden.obstacles` only — so a bed never gets resize handles or
vertex handles. Labelling something `bed` moves it between the arrays and it
silently loses the ability to be reshaped.

**To do:** one lookup across both. The plan already treats them as one thing
when it draws them; selection has to agree.

### 3. garden-is-not-a-bed

**Reported:** the outline imported from the map is created as a flower bed.

**To do:** a new kind `garden` in `objects.py::TRAITS` and `kinds.ts`, used by
the map import for the boundary. A surface, not standing, not planting — the
ground everything else sits on. Existing gardens keep their outline: the kind
changes for new imports, and the old ones can be relabelled by right-click.

### 4. undo-with-ctrl-z

**Reported:** Ctrl+Z should undo the last drawing action.

**Found:** undo exists, but only for polygon draft points, and only through the
buttons in `CanvasControls`.

**To do:** the keyboard shortcut, and a stack that covers the operations the
plan actually performs — draw, move, resize, reshape, delete. Not typing: the
shortcut must not fire while a text field has focus.

### 5. what-is-planted-here

**Reported:** clicking a bed should list what is planted in it, removable one by
one.

**To do:** the list per bed, with the count, and a per-row remove. The delete
path exists server-side (`drop_plantings`); this is the view that was missing.
Removal is per species, and asks first, because a planting is somebody's
decision and not a keystroke.

### 6. planting-clusters

**Reported:** show what is sown as greyed dots so the bed's fullness is
readable; always clustered; cluster size from the species' space requirement
where known; left-click a cluster for its name and an info button, drag it
within the bed's bounds, copy and paste it, including between beds. Plus: the
painted flowers are sometimes still colour bands.

**Found for the bands:** `bloomFill` still returns `url(#bloom-unknown)` — a
hatch pattern over the whole bed — whenever a bed's palette has no known colour
but some unknown ones. That is the striping still being seen, and it is the same
question this feature answers: unknown-colour plantings become grey dots like
everything else, and the pattern goes.

**To do:** positions that persist rather than being generated per render — a
cluster the user has moved has to stay where it was put, so this needs storage
on the volume. Cluster radius from `space_m2` where the catalogue has it, from a
default where it does not, and visibly uncertain in neither case. Dragging is
clamped to the bed's polygon, not its bounding box.

## Open Research

- Where a moved cluster's position lives. `planting` is per bed and species; a
  position is per *cluster*, and pasting the same species twice into one bed
  means two clusters of one species. This may need a row per cluster rather than
  a column on `planting`.
- ~~Whether `space_m2` is populated widely enough for cluster size to mean
  anything.~~ **Answered before building.** The catalogue records no spread at
  all — GIFT gives `height_max_m` and nothing about width — and `space_m2` is
  derived from that height by `canopy.py`, for the 3 952 of 8 939 species that
  have one. So cluster size can use it for 44 %, and the rest fall back to a
  default.

  The consequence is a design constraint, not a blocker: the cluster may not
  look measured. `canopy.py` already states the rule this project works to —
  "a derived number that looks measured is worse than no number" — so a cluster
  gets no area figure and no crisp edge, and the info panel says the room it
  claims is estimated from height.
