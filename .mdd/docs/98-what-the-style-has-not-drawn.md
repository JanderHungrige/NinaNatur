---
id: 98-what-the-style-has-not-drawn
title: What the Style Has Not Drawn
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-24
wave_status: active
depends_on: [97-draft-sketch-in-svg, 94-which-way-the-ridge-runs]
relates: [97-draft-sketch-in-svg, 96-a-theme-is-a-thing]
source_files:
  - ninanatur/garden/roofshape.py
  - ninanatur/garden/roof_lines.py
  - frontend/src/kinds.ts
  - ninanatur/api/schemas.py
  - ninanatur/api/gardens.py
  - frontend/src/api/types.ts
  - scripts/stylx_to_theme.py
  - scripts/draft_sketch/cim.py
  - scripts/draft_sketch/layers.py
  - scripts/draft_sketch/outline.py
  - scripts/draft_sketch/lines.py
  - scripts/draft_sketch/emit.py
  - frontend/src/themes/types.ts
  - frontend/src/themes/index.ts
  - frontend/src/components/PlanDecorations.tsx
  - frontend/src/components/PlanObjects.tsx
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/components/PlanFurniture.tsx
  - frontend/src/components/PlanCredit.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/canvas/sketch.ts
  - frontend/src/canvas/along.ts
  - frontend/src/canvas/scaleBar.ts
  - frontend/src/themes/draft-sketch/index.ts
  - frontend/src/themes/draft-sketch/draw.tsx
  - frontend/src/themes/draft-sketch/drawAlong.tsx
  - frontend/src/themes/draft-sketch/paths.ts
  - frontend/src/themes/draft-sketch/overlays.ts
  - frontend/src/themes/draft-sketch/ours/rules.ts
  - frontend/src/themes/draft-sketch/ours/Furniture.tsx
  - frontend/src/themes/draft-sketch/ours/Roads.tsx
  - frontend/src/themes/draft-sketch/theme.css
  - frontend/src/themes/draft-sketch/generated/rules.ts
  - frontend/src/themes/draft-sketch/generated/symbols.ts
  - frontend/src/sheet/build.ts
  - frontend/src/sheet/vocabulary.ts
  - frontend/src/sheet/gardens.ts
  - frontend/src/sheet/SheetCell.tsx
  - frontend/src/sheet/main.tsx
  - frontend/scripts/plan-sheet.mjs
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - tests/test_roof_lines.py
  - tests/test_draft_sketch_converter.py
  - frontend/src/canvas/sketch.test.ts
  - frontend/src/canvas/along.test.ts
  - frontend/src/canvas/scaleBar.test.ts
  - frontend/src/themes/draftSketchVocabulary.test.tsx
  - frontend/src/themes/draftSketch.test.tsx
  - frontend/src/components/PlanFurniture.test.tsx
data_flow: reads-existing
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [draft-sketch, themes, roofs, raised-beds, hedges, shrubs, fences, walls, blooms, compass, scale-bar]
path: Canvas/Style
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Paint budget: 85 ms for the city at 40 m, CPU x4, against the 72 ms limit (twice Technisch's 36) — a stage-3 finding. With production React: 66 ms against Technisch's 17."
  - "Deciduous and conifer trees are drawn alike: no tree on the plan carries its kind, and none is guessed."
  - "Sightlines are not on the plan in any theme, so there is nothing to draw in his ink."
  - "His Tree 2 and his waves are capped on small shapes (a wave at an eighth of the radius, a tick at a third): an adaptation, visible on shrubs a metre across."
  - "Images of his under 8 px are not drawn as his pictures: fence posts are outlined, mortar joints left out, a tree's centre is a vector cross."
  - "A pent roof's one line lies on its outline; the fall arrow is what shows it."
  - "The title block's date is when the garden last changed, not when the plan was looked at."
  - "Blooms are his splotch through a CSS mask on every dot, drawn at 1.8 times the dot."
  - "Lettering is today's type until feature 5."
---

# 98 — What the Style Has Not Drawn

## Purpose

Feature 3 of Wave 24, the second half of stage 2. Doc 97 draws a garden in
Warren Davison's hand wherever his style has a symbol: surfaces, buildings,
trees. A garden plan needs more than a city map: roofs that say what kind of
roof they are, raised beds, hedges, shrubs, fences and walls, blooms, a north
arrow and a scale. Each is drawn from data the plan already has, in his hand —
his own symbols where he has one, adapted or new ones in his manner where he
has not — and where the data is missing, nothing is invented.

## Where each comes from

| Need | Data | Drawing | Provenance |
|---|---|---|---|
| **roofs by type** | `roof`, `roof_fall_deg`; the server's roof model (doc 94) | ridge, a hip roof's four hips, a pent roof's upper edge, in his ink; flat and unknown roofs as planes | NinaNatur, in the style of Draft Sketch |
| **raised beds** | `height_above_ground` > 0 | an inner second outline and a shadow on the side away from his light | NinaNatur, in the style of Draft Sketch |
| **hedges** | kind `hedge` | his dark green wash, hatched along the side away from the light | NinaNatur, in the style of Draft Sketch |
| **shrubs** | kind `shrub` | his Tree 2 — the serrated crown with rings, three levels of detail | Warren Davison (Draft Sketch) |
| **fences** | kind `fence` | his Wood Fence along the element's line: ink, posts | adapted from Draft Sketch |
| **walls** | kind `wall` | his Brick Wall fitted to the wall's own faces: two lines, the wash between | adapted from Draft Sketch |
| **blooms** | the plan's clusters (doc 56) | each dot a dab of his watercolour, grey out of season | NinaNatur, in the style of Draft Sketch |
| **viewpoint** | Wave 9 | in his ink | NinaNatur, in the style of Draft Sketch |
| **streets** | kind `street`, one band per way | his paving wash per band; one ink round the network, none across a junction | NinaNatur, in the style of Draft Sketch |
| **the ground** | the garden itself | his lawn wash, thinned over the paper: a drawing is not white | NinaNatur, in the style of Draft Sketch |
| **north, scale, title** | the view, `GardenOut.name` | a north arrow, a scale bar that is true at every zoom, a title block | NinaNatur, in the style of Draft Sketch |

**Not drawn, named:**

- **Deciduous against conifer.** No tree on the plan knows what it is: a tree
  element has no species, and the leaf state the server works out for found
  canopies is not sent. A conifer crown drawn without that would be a guess
  on the map — the one thing a plan must not do. It waits for the data.
- **Sightlines.** No plan draws them, in any theme: they are a list in the
  inspector. There is nothing on the plan to draw in his ink.
- **Hand lettering** is feature 5's; the title block uses today's type.

## Roofs: the server says, the plan draws

The plan has a roof's type and, where surveyed, which way it falls — but not
where its ridge runs: that is the server's roof model (`roofshape.surface_of`),
the same one the light model uses. Working it out again in the browser would be
a second answer to "where is the ridge", which is how two drawings of one roof
come to disagree. So `ObstacleOut` gains **`roof_lines`**: the lines that draw
the roof the model knows, in garden metres.

- **gable** — the ridge, wall to wall along the model's axis.
- **hip** — the shortened ridge, and a hip from each of its ends towards the
  two corners of the roof's rectangle at that end — ending on the house's own
  corner nearest to each.
- **pent** (surveyed) — the upper edge, where the one plane is highest.
- **flat, mixed, other, unknown, an unsurveyed pent, a pitch under 5°** — no
  lines: the model treats them as a plane at one height, and so does the
  drawing.

Add-only: a computed field of the answer, no column.

**Only inside the house** (the owner, 2026-09-21: "Bei schrägen, nicht
rechteckigen Häusern zeichnet das Dach manchmal über das Haus hinaus. Vor allem
beim Walmdach"). The model works over one rectangle per house, and on a house
that is not one — a trapezoid on a street corner, an oblique end wall, an L —
the rectangle's corners lie outside the walls: the hips ran out across the
garden and a gable's ridge past the shorter wall. `garden/roof_lines.py` sends
each hip to the house's own corner nearest the rectangle's and cuts every line
to the outline, keeping what lies on a wall (a pent's upper edge does). On a
rectangle neither changes anything; the roof's light is still the model's.

## What the plan draws, and where it stands

| Mark | Drawn by | Where |
|---|---|---|
| a shape's shadow | the theme's `decorate`, `under` | right beneath its own shape, in `canvas__objects` |
| roofs, raised beds' edges, hedges' hatch, his ink | `decorate`, `over` | the ink layer over every shape |
| his line symbols | `drawAlong` | the ink layer; a wall's clipped to its outline |
| north, scale, title | the theme's `Furniture` | the plan's corner (`PlanFurniture`) |
| the street network's ink | the theme's `Plan` | first in the ink layer, under every shape's own marks |
| his credit | `PlanCredit` | a caption beneath the plan — with OpenStreetMap's on a line of its own where the plan draws OSM content (doc 106) |

**Shadows moved.** Doc 97 drew every shadow in one layer under every shape.
A tree's shadow then fell under the lawn it stands on, and a raised bed's
under the path beside it: each shape's shadow is now drawn right before the
shape itself, as his shadow is each symbol's bottom layer.

**The credit moved.** In the title block, in full, it covered a third of a
phone's plan; it is now a caption beneath the plan, word for word, whenever
the plan is drawn in his style. The tool's hint moved with it: it used to
float at the bottom of the whole plan column, which now ends below that
caption, so the two were drawn over each other. It hangs inside the drawing's
own box (`canvas-stage`) instead, and the stage takes the room the caption
leaves (`flex: 1`, doc 86's rule intact: the drawing still cannot set its own
height). Under the controls at the top edge, not at the bottom: the bottom is
the theme's, and the first try put the hint straight over the title block.

## His line symbols along our elements

Fences, walls and hedges are elements with an outline, often drawn as a line
(`shape` `line`, with `points`). His Wood Fence and Brick Wall are line
symbols (CIM class 4): strokes, marks every few points, splotches of varying
size scattered along. The converter reads them as it reads his polygons, into
overlays of their own that `draw.tsx` lays along a line:

- a fence: along its own line when it has one, else along its outline's long
  axis;
- a wall: his two lines, which at 1:250 would stand 0.7 m apart, laid on the
  wall's real faces instead; his wash and splotches between them.

## Streets meet, so they are one network

A street arrives from the map as a **way**: a centreline and a width, one
element per stretch. Two ways that meet are two bands lying over each other,
and an outline drawn per band runs straight through the road beside it — the
junction looks stitched together from edges and nodes, which is what it is.

The plan is drawn one shape at a time, so no shape can know this. The seam has
a member for it: `PlanTheme.Plan` is drawn once for the whole plan, first in
the ink layer. `ours/Roads.tsx` takes every street's outline, draws the lot as
one path at twice his ink width, and masks that path **with itself**: by
luminance, so what is painted black — the road surface — is cut away, and only
the half of the line that lies outside the network survives. Nothing crosses a
junction, and a street's own `decorate` draws no outline at all.

**A road turns on a corner it does not have.** A way is a rectangle, so two of
them meeting at an angle leave the outside of the bend open: a wedge at a
shallow angle, a notch a metre wide at a sharp one. Each way now carries a disc
of its own width at each end of its centreline — the round join the rectangles
lack — drawn beneath the band in the band's own wash, and added to the
network's outline so the ink rounds the same corner from the same numbers. In
the mask the discs are a path of their own: in one path with the bands, a disc
that winds the other way cancels against the band it sits in and opens a hole,
which lets the ink through inside the road.

A way that ends on another way's **edge** rather than in it puts the two
boundaries on top of each other, and a hairline of ink comes through the seam —
a line across a road, which is the thing this draws away. The mask is grown by
three quarters of a pixel to swallow them, and the line is drawn that much
wider so what is left outside keeps his weight.

**Nor across a house.** The outline is drawn over every shape, so a house the
map put on the road — drawn over the road's grey — still had the road's line
running through it (the owner, 2026-09-21, both screenshots). What is built
(`kinds.isBuilt`: a house, a shed, a wall) is painted into the mask too, each
outline turned the same way round so two that overlap add up rather than
cancel. What grows or lies on a road keeps the line: a crown over a street
does not end it.

The mask's box holds the discs as well. It was sized to the bands, so a road's
rounded end lay outside it and had no line.

It is worked out once per garden and per zoom step (`useMemo`, and `InkLayer`
gets the same quantised scale the decorations use), not on every drag frame:
a map import brings sixty ways, and each one's wobble is real work.

**The ground is grass, not paper.** His lawn wash under the whole garden at
half opacity — pale green over the paper, with a real lawn darker on top of
it. `--plan-ground-fill` in `theme.css`. Technisch's ground has been a flat
grass wash since 2026-09-21 (no blades, so a drawn lawn still tells apart).

## The paint budget, measured

The city (102 elements, 11 fences, a 60 m wall, 20 houses with roof lines, 9
shrubs) at 40 m, CPU ×4, median of five: **83 ms**, against the 72 ms that is
twice Technisch's recorded 36 — over, and a finding for stage 3 as doc 97's
rule has it. Measured with production React, which is what anybody using the
plan gets: **66 ms**, against Technisch's 17.

What was tried, and what it gave (dev React): his line symbols' marks through
one mask per layer rather than one per mark, no change; posts in one path and
specks of images not drawn, 98 → 88; shadows without a group each, no change;
tree centres as vector crosses when they are specks, 87 → 85. What does not
cost: the bloom dabs, roof lines. The cost is the number of elements — React's
development checks weigh on each — and the lever left is feature 4's: his
levels of detail set in metres. At 40 m the city is drawn in his richest
symbols, because his print ranges put the change at 0.40 m a pixel.

## Business Rules

1. **Nothing invented.** A roof is drawn from the server's lines or not at all;
   a tree is not given a kind it has not got.
2. **His where he has it.** Shrubs, fences and walls are derived from his file
   by the converter and pass `--check`, as doc 97's do. What is ours says
   *NinaNatur, in the style of Draft Sketch* in its provenance header.
3. **Never a target.** Everything here is decoration — each shadow beneath its
   shape, the rest in the ink layer — or the furniture's own corner, which
   takes no pointer; the shapes stay the hit targets.
4. **Technisch is untouched**: its 24 cells as recorded. The contact sheet
   gains a fourth garden for other themes only — every roof, a raised bed, a
   hedge, fences, walls, shrubs.
5. **The scale bar is true**: its length in metres is what it covers on the
   screen at the current zoom, rounded to a 1-2-5 step.
6. **The budget is measured**: the city at 40 m, CPU ×4, against twice
   Technisch's 36 ms; beyond it is a finding for stage 3, as in doc 97.

## Dependencies

- 97 — the converter, the theme, the decoration layers.
- 94 (which way the ridge runs) — the roof model: ridge direction from the survey.

## Security

No new input. `roof_lines` is computed from the element's own footprint and
roof fields. The converter reads more of the same pinned file.

## Known Issues

- **Technisch still shows the wedge at a bend.** His style now rounds the
  corner (above); ours draws the rectangles as they come. The same disc would
  work there, and it is a change to a recorded look, so it waits for the owner.

## Bugs

(none yet — populated by /mdd bug when issues are reported)
