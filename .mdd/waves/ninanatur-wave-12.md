---
id: ninanatur-wave-12
title: "Wave 12: The plan gets out of its own way"
initiative: ninanatur
initiative_version: 13
status: in_progress
depends_on: ninanatur-wave-11
demo_state: "A user opens a garden, finds the drawing tools at the top, drags out a shape without anything else being selected, closes a polygon by coming back to where they started, names it with a right-click, and finds every element again in a list"
created: 2026-08-31
hash: 766fc32c
---

# Wave 12 — The plan gets out of its own way

## Demo-State

A user opens a garden, finds the drawing tools at the top, drags out a shape
without anything else being selected, closes a polygon by coming back to where
they started, names it with a right-click, and finds every element again in a
list.

*(This wave is not complete until this can be manually demonstrated.)*

## Why this wave exists

Wave 11 made the drawing model right and left the interface around it wrong.
Every item below came from using the plan, not from reading it:

- The tools are in the right-hand column, below the plan they operate.
- Two forms survive from before drawing existed: *Beet hinzufügen* and
  *Hindernis hinzufügen*.
- **Clicking the canvas to draw first selects the garden-wide bed**, which
  scrolls the page to the plant suggestions. The user then clicks again and it
  works — so the tool appears to need two attempts.
- The polygon panel never goes away, and Escape does not close it or clear a
  selection.
- **A polygon refuses to close when the last corner overlaps the first.** Three
  corners close; four corners that go slightly past the start are rejected as
  self-intersecting.

## What was reproduced before planning

| Outline | self-intersects | result |
|---|---|---|
| 3 corners, nearly closed | no | closes |
| 4 corners, nearly closed | no | closes |
| 4 corners, **slightly past the start** | **yes** | *"Der Umriss überschneidet sich selbst"* |

The complaint is exact: it is the overlap, not the corner count. Freehand
already has the rule this needs — `closeIfNear` drops a trailing point that came
back to the start — and the two drawing paths should close the same way.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | panel-order | .mdd/docs/47-panel-order.md | complete | — |
| 2 | garden-soil | .mdd/docs/48-garden-soil.md | complete | — |
| 3 | drawing-focus | .mdd/docs/49-drawing-focus.md | complete | — |
| 4 | polygon-closing | .mdd/docs/50-polygon-closing.md | complete | — |
| 5 | element-context-menu | .mdd/docs/51-element-context-menu.md | complete | — |
| 6 | element-list | .mdd/docs/52-element-list.md | complete | 5 |

### 1 — panel-order

The drawing tools move to the top of the left column, directly under the garden
ID. *Beet hinzufügen* and *Hindernis hinzufügen* go: both predate drawing, and
two ways to put a thing on a plan is one more than anybody wants.

Soil and moisture are not part of this feature: they move out of the removed
form and into feature 2, which is about where they come from rather than where
the box sits.

### 2 — garden-soil

**One question per garden, not one per bed.** After a garden is created the user
is asked once what the soil and the moisture are, and every bed drawn afterwards
starts from that. Individual beds can be changed later — a raised bed with
bought soil, or a corner that gets watered — in the element editor beside the
kind and the label.

This is the shape Wave 8 already settled on for building heights, and for the
same reason: the alternative asks the same question of every bed and puts a wall
in front of somebody who has just arrived.

**They keep their fields rather than becoming free text**, decided with the
user. Soil and moisture are not decoration — they produce three of the four
Ellenberg axes the suggestions rank on, and a free label would take that away
without saying so. What changed is where they are asked, and how often.

**A link out, not a guess.** Most people do not know their soil type, so the
question carries a button to a page where it can be looked up. Linking is all
this feature does with an outside source; reading one is research, below.

### 3 — drawing-focus

An armed tool suppresses selection until the shape is placed. Today the first
click lands on the garden-wide bed, the page jumps to the suggestions, and the
tool looks broken until the second attempt.

Escape becomes the one way out of everything: it puts the tool down, closes the
drawing panel, and clears the selected element. Only the polygon tool keeps its
panel, and only while it is armed.

### 4 — polygon-closing

A last corner within snapping distance of the first closes the ring instead of
being refused. The check order stays as it is — the specific complaint first —
but closing happens before the self-intersection test, because an overlap at the
start is a closure, not a tangle.

### 5 — element-context-menu

Right-click an element for its kind and label, at the element rather than across
the page. The editor panel stays: the menu is the short way, not the only way.

Keyboard equivalent required — a context menu that only a right-click reaches
leaves out everyone using the plan from the keyboard, and every element is
already focusable and named.

### 6 — element-list

Every drawn element in a list beside the plan: select one, name one, find the
one buried under three others. This is the real answer to overlapping shapes —
draw order helps two, and nothing helps three.

## Risks

- **Removing the two forms removes the only numeric entry path.** A bed drawn by
  hand can no longer be given exact coordinates. Nobody has asked for that, and
  it is written here so its absence is a decision rather than an oversight.
- The context menu and the list both edit the same element. Two panels
  disagreeing about what is selected is the obvious way for this to go wrong.

## Open Research

- [x] Does the element list need to scroll independently of the plan, or is a
      garden small enough that it never gets long? A hundred elements is not
      unreasonable for a real garden.
- [ ] **Can the soil be read rather than asked?** The map already fixes the
      location, so a soil map could answer it. Explicitly queued behind this
      wave — the button that links out is the first pass.

      Candidates to check, and the check is the same one that kept this project
      off NaturaDB: licence first, then `robots.txt`, then whether the terms
      permit derived work in a hosted product.

      - **SoilGrids (ISRIC)** — global, ~250 m, a REST API, and the most likely
        to clear on licence. Gives sand/silt/clay fractions and pH, which is
        most of what `site_axes_from_soil` needs.
      - **BGR BÜK200** — German, far better resolution, licence to establish.
      - State soil services, per Bundesland, as the orthophotos already are.

      **Moisture will not come from any of them.** A soil map describes what the
      ground is made of, not whether this corner is watered or drains into a
      ditch. That half stays a question, and a feature that quietly filled it in
      from a map would be inventing the number the light model then uses.

## Definition of done

Drawing works on the first click, Escape always gets out, a polygon closes when
the hand comes back to the start, and every element can be found and named both
on the plan and in the list.
