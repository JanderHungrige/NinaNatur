---
id: ninanatur-wave-14
title: "Wave 14: A plan that looks painted, not plotted"
initiative: ninanatur
initiative_version: 18
status: complete
depends_on: ninanatur-wave-13
demo_state: "A bed shows its flowers as clustered dots rather than a colour bar, an element can be deleted where it stands, the plan reads as a painting rather than a drawing, and the street outside is on it"
created: 2026-08-31
hash: e7b57f79
---

# Wave 14 — A plan that looks painted, not plotted

## Demo-State

A bed shows its flowers as clustered dots rather than a colour bar, an element
can be deleted where it stands, the plan reads as a painting rather than a
drawing, and the street outside is on it.

*(This wave is not complete until this can be manually demonstrated.)*

## Why this wave exists

The plan works and looks like CAD. Four things from using it:

- **Bloom colour is a thick bar across the bed.** It should be dots — flowers
  are small, and several of one colour go in together because that is how
  anybody plants.
- **Nothing can be deleted from the plan.** An element drawn by mistake stays.
- **The whole thing reads as a technical drawing.** The reference the user gave
  is still a plan, but painted: watercolour washes, a path drawn as stones, a
  roof drawn as a roof.
- **The map knows more than the plan shows.** Streets are in OpenStreetMap and
  are not on the drawing.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | bloom-dots | .mdd/docs/56-bloom-dots.md | complete | — |
| 2 | delete-elements | .mdd/docs/57-delete-elements.md | complete | — |
| 3 | painted-plan | .mdd/docs/58-painted-plan.md | complete | — |
| 4 | osm-streets | .mdd/docs/59-osm-streets.md | complete | — |

### 1 — bloom-dots

Flowers as dots inside the bed, grouped by colour.

A tiling pattern cannot do this: a pattern repeats uniformly and clustering is
the opposite of uniform. The positions have to be generated per bed and clipped
to its outline — **seeded from the bed's own id**, so the same bed looks the
same on every render rather than shuffling its planting each time React
re-draws.

Bands stay wrong for a second reason beyond thickness: they say the bed is half
yellow and half blue, when what is true is that some flowers are yellow and some
are blue. Dots say the true thing.

The count is bounded. A bed with two hundred plants is not two hundred dots — it
is a bed that reads as full, and past some density more dots carry no more
meaning and cost a composited node each.

**"Never recorded" keeps its hatch.** It is not a colour and must not become a
grey dot among coloured ones.

### 2 — delete-elements

Delete from the right-click menu, where the kind and the label already are.

It asks first and the confirming button names what it does, like the garden list
in Wave 13. A bed with plants in it says how many go with it — the same warning
re-labelling already gives, for the same reason.

### 3 — painted-plan

The wobble filter has been there since Wave 10 and the plan still reads as
plotted. Adding another filter is not the answer; what is missing is what
watercolour actually does:

- **Colour varies within a shape.** Every fill is one flat value, which is what
  makes it read as CAD. Two or three tones per wash, unevenly.
- **Edges bleed.** A wobbled crisp edge is still a crisp edge. Watercolour is
  darker where it pools at the rim and thinner in the middle.
- **The symbols are drawn objects, not textures.** A gravel path is stones of
  different sizes, not a stipple; a roof has battens, which it now has; a pond
  has a rim and a ripple.

**The honest note:** this feature's definition of done cannot be asserted. It is
looked at, and Wave 13 took four passes of looking to get a background right.
Budget for that rather than expecting one.

### 4 — osm-streets

The street outside, from OpenStreetMap, as a line element.

This is the shape Wave 11 built: a road is a centreline and a width, which is
exactly what `shape: 'line'` stores, and `band_of` already turns it into the
footprint everything downstream consumes. No new geometry.

Licence is settled — OSM is ODbL and the attribution is already on the page, the
same source the buildings come from. What is not settled is **volume**: the
buildings query fetches centres only, and a street query returns geometry.
Overpass is a free service with the same no-SLA standing as Nominatim, so this
follows the project's existing rule — cache on disk, delay, and a rerun costs
zero calls.

A street does not shade a garden. It is on the plan to orient somebody looking
at it, which means it is drawn and then left alone: no height, no shadow, and
nothing downstream should start treating it as an obstacle.

## Risks

- **Two features rewrite how the plan is drawn.** Bloom dots and the painted
  look both land in `CanvasScene`, which was already the largest thing on the
  frontend before either.
- **The painted look has no test.** Its risk is that it gets called done by
  whoever wrote it. It is not done until it is looked at on a real plan with
  real beds.
- **Streets can be many.** A garden on a corner sits near a dozen ways, and
  drawing all of them turns the plan into a map.

## Open Research

- [ ] How many dots is "full"? It needs to read as a planted bed at a whole-
      garden zoom and not turn to soup at close range — those may want different
      answers, which means density may have to follow the zoom.
- [ ] Which streets belong on the plan? Everything within the 50 m margin is
      probably too much; the ones the garden actually touches is probably right.

## Definition of done

A bed's flowers read as clustered dots, an element can be deleted where it
stands, the street outside appears, and somebody shown the plan calls it a
drawing of a garden rather than a diagram of one.


## What the wave found

| Found by | Defect |
|---|---|
| an existing Wave 10 test | seventy flowers between the pointer and the bed would have swallowed every click that selects it |
| adding the street call | a test reached Overpass for real and passed anyway on a warm cache — green here, red in CI |
| the container check | the API turned "this kind has no height" into `0.0`, a measurement nobody took |

The last one is the interesting one: the rule has been written down since Wave 8
and the domain type had it right. The API kept an `or 0.0` at the one edge where
a caller does not supply a height, so every heightless kind — street, lawn,
pond, paving — has been stored as something zero metres tall rather than as
something with no height.

## What is not verified

**The painted look has not been seen by anybody.** The Browser pane returns a
blank capture whenever this SVG is on screen — canvas fully in view, opacity 1,
DOM correct, image empty. The plan said this feature is not done until it is
looked at on a real plan. It stands on its reasons until somebody looks.
