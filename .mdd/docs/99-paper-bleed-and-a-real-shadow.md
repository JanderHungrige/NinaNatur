---
id: 99-paper-bleed-and-a-real-shadow
title: Paper, Bleed and a Real Shadow
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-24
wave_status: active
depends_on: [97-draft-sketch-in-svg, 98-what-the-style-has-not-drawn]
relates: [96-a-theme-is-a-thing, 07-solar-geometry, 38-polygon-shadows]
source_files:
  - ninanatur/solar/drawing.py
  - ninanatur/api/schemas.py
  - ninanatur/api/gardens.py
  - frontend/src/api/types.ts
  - frontend/src/themes/types.ts
  - frontend/src/themes/index.ts
  - frontend/src/themes/draft-sketch/index.ts
  - frontend/src/themes/draft-sketch/draw.tsx
  - frontend/src/themes/draft-sketch/Defs.tsx
  - frontend/src/themes/draft-sketch/theme.css
  - frontend/src/themes/draft-sketch/generated/symbols.ts
  - frontend/src/components/PlanDecorations.tsx
  - frontend/src/components/PlanObjects.tsx
  - scripts/draft_sketch/tiles.py
  - scripts/draft_sketch/emit.py
  - scripts/stylx_to_theme.py
routes: []
models: []
test_files:
  - tests/test_drawing_shadow.py
  - tests/test_draft_sketch_converter.py
  - frontend/src/themes/draftSketch.test.tsx
  - frontend/src/themes/draftSketchVocabulary.test.tsx
data_flow: mixed
last_synced: 2026-09-20
status: draft
phase: all
mdd_version: 11
tags: [draft-sketch, plan, theme, shadow, sun, level-of-detail, paper, filter]
path: Plan/Draft Sketch/Paper and shadow
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 99 — Paper, Bleed and a Real Shadow

## Purpose

Three things the style still owes, all measured on the contact sheet (doc 95):

1. **Paper and bleed** — the sheet under the drawing is his paper, and his
   washes bleed past their edge, both where SVG geometry cannot do it.
2. **Levels of detail set to our sizes** — his print ranges draw his richest
   symbols at every zoom anybody uses, which costs marks that are too small to
   see. This is the lever doc 98's paint budget named.
3. **A shadow the sun actually casts** — the drop shadow of a standing thing
   points where the sun puts it, at one reference moment, and is as long as the
   thing is tall. No other plan on the page knows where the sun is.

## The shadow is the model's, like the roof

Doc 98's rule — *the roof a drawing shows is the model's* — decides this one
too. The sun is arithmetic the server already owns (`ninanatur/solar`, doc 07):
`sun_position` gives altitude and azimuth, `shadow_length(height, altitude)` is
`height / tan(altitude)`, and `shading_height` (doc 32) knows that a pitched
roof shades from somewhere between its eaves and its ridge. Porting any of that
into the browser would give the plan a second sun to disagree with the first.

So the server hands each obstacle the offset its shadow has **at the drawing's
reference moment**, in metres, as it already hands over `roof_lines`:

```
ObstacleOut.shadow: [dx, dy] | null      # metres, x east, y north
```

`null` when the thing casts none: no height, a kind that does not cast
(doc 08's `casts_shadow`), or a sun too low to draw. A pitched roof shades from
`shading_height`, so a house throws the shadow of its eaves plus part of its
gable rather than of its ridge.

**The shape is swept, not moved.** Offsetting the outline by eight metres
leaves a gap between a house and its own shadow, which reads as a second
building; the shadow is the ground the thing hides all the way over. So the
mark is the hull of the outline and its offset copy (`sweep`), which is the
same hull `solar/shading.shadow_polygon` takes — the drawing and the light
model draw one outline, not two.

And it is **not wobbled**. His drop shadow was a pen mark and wobbled like one;
a cast shadow has the edge the wall has. Dropping the wobble from 51 shadows on
the city took the frame from 78 ms to 69 — the real shadows cost less than the
style's pretend ones did.

### The reference moment

**15 June, 15:00 local solar time**, at the garden's own longitude:

```python
when = datetime(YEAR, 6, 15, tzinfo=UTC) + timedelta(hours=15 - longitude / 15)
```

Local *solar* time rather than the clock, because the clock is a political
line: a garden in Vigo and one in Wuppertal share a time zone and an hour and a
half of sun. Three hours after noon in June puts the sun high and to the
west-south-west anywhere in Europe, which is what makes the shadow **short**
— about 0.8 of the thing's height at 50° north — and unmistakably afternoon.

It is one moment, not the day: the plan is a drawing, and a drawing has one
light. The moving shadows of the day playback (doc 38) are a different thing on
the same plan and stay as they are.

## Levels of detail, set to what can be seen

His three ranges are 1:1,500 and 1:2,500 at print scale — 0.40 and 0.66 metres
per pixel, beyond any zoom the plan is normally used at, so every plan anybody
opens is drawn in his richest symbols. Measured on the city (102 elements) at
40 m, the span a phone opens at, with the CPU slowed four times:

| What is drawn | Nodes | Marks | Paint | Against his richest |
|---|---|---|---|---|
| his richest everywhere (his ranges) | 1,524 | 401 | 84–85 ms | — |
| one level down everywhere | 1,407 | 284 | 68–70 ms | 9.8 % of bytes differ |
| **each shape at its own size** | 1,409 | 286 | 73–74 ms | 7.8 % |

The middle row is the cheap answer and the wrong one: it takes the detail off
the houses, which are 89 pixels across and can carry it, to save what the
shrubs cost at 13. **The level is asked per shape** — `lodAt(scale, acrossM)`
— so a house keeps his hatch while the crowns beside it simplify. That is also
what a hand drawn plan does: detail where there is room for it.

The thresholds are in **pixels across**, not metres per pixel, because that is
the question being asked: 48 pixels for his richest (three rings in a crown
need about that), 14 for the middle one (below it nothing but an outline
survives). Measured on the sheet: the two pictures differ by 15 % of their
bytes at 20 m and by 10 % at 40 m, so the detail is real wherever it is drawn
— it is the *small shapes* that cannot show it, not the scale.

**The budget is not met, and this is the honest number.** Technisch measures
21 ms on the same machine on the same day (the 36 ms in doc 95's record is
another day's machine), so twice Technisch is 42 ms and the city costs 73 —
69 once the shadows stopped being wobbled.
What is left is not marks — 286 against the cheap answer's 284 — but his
washes: image tiles with masks, several on one plan. Trying it the other way
round, one wash for the whole plan and marks per shape, costs *more* (79 ms),
because his near tiles are the heavy ones. Whether 73 ms at a quarter speed —
about 18 ms on the phone itself — is a problem is a judgement for the owner,
and it is written down rather than tuned away.

## Paper and bleed, as filters

Everything else in this style is geometry (doc 97). These two cannot be:

- **The paper.** His file has a paper texture, already shipped and already
  under every wash he paints. The plan gets it under the whole drawing, tinted
  with the theme's paper colour — his paper, not a turbulence of our own,
  because his exists (doc 97's rule). The converter emits it as one more
  pattern, so it stays generated.
- **The bleed.** One filter on the objects group, the seam's `objectsFilter`,
  which Technisch has used since Wave 1: turbulence displacing the washes by a
  fraction of a metre so an edge looks soaked rather than cut. The ink layer is
  not in that group, so the line stays crisp over a soft wash — which is how
  watercolour under pen actually looks.

Both are switched off under `prefers-contrast: more` and `forced-colors`, as
the existing filter already is (doc 96), and both are measured on the sheet
before they stay: a filter over the whole group is a raster pass per frame.

## Business Rules

1. **One sun.** The drawing's shadow comes from `ninanatur/solar` through the
   API. Nothing computes a sun position in TypeScript.
2. **A shadow is the model's or it is absent.** No default direction, no
   invented height: `shadow` is `null` and nothing is drawn.
3. **The reference moment is one constant in one place**, named and dated in
   the code, so two drawings of one garden cannot disagree.
4. **The levels are tuned on the sheet**, and the budget is re-measured in the
   same run: a threshold is a look decision with a cost attached.
5. **His where he has it** (doc 97): the paper is his image, tinted; only what
   his file does not contain is ours.
6. **Every filter switches off** under `prefers-contrast: more` and
   `forced-colors`, and Technisch stays pixel-identical to its record.

## Dependencies

- Doc 07 (solar geometry), doc 32 (object heights), doc 38 (polygon shadows)
  for the sun and what casts a shadow.
- Docs 96–98 for the seam, his symbols and what we draw in his hand.
- Doc 95's contact sheet for every judgement here.

## Security

Nothing new is exposed: the shadow offset is derived from data the client
already has (a garden's obstacles, its position) and carries no token.

## Known Issues

## Bugs
