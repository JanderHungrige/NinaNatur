---
id: ninanatur-wave-24
title: "Wave 24: A drawing of a garden"
initiative: ninanatur
initiative_version: 23
status: in_progress
depends_on: ninanatur-wave-23
demo_state: "Der Plan ist in Warren Davisons Draft-Sketch-Handschrift gezeichnet — mit seiner schriftlichen Erlaubnis, aus seinem Stil geholt und um das erweitert, was ein Garten braucht und eine Stadtkarte nicht: Blüten in ihrer Farbe, Laub- und Nadelbäume, Sträucher, Hecken, Dächer nach ihrer Form, Hochbeete, eine Kompassrose und ein Titelblock. Ein Schalter stellt den technischen Plan zurück. Beurteilt wurde am Kontaktbogen, und Davison hat es gesehen."
created: 2026-09-07
hash: 5818d75a
---

# Wave 24: A drawing of a garden

## Demo-State

Der Plan ist in Warren Davisons Draft-Sketch-Handschrift gezeichnet — mit
seiner schriftlichen Erlaubnis, aus seinem Stil geholt und um das erweitert,
was ein Garten braucht und eine Stadtkarte nicht: Blüten in ihrer Farbe, Laub-
und Nadelbäume, Sträucher, Hecken, Dächer nach ihrer Form, Hochbeete, eine
Kompassrose und ein Titelblock. Ein Schalter stellt den technischen Plan
zurück. Beurteilt wurde am Kontaktbogen, und Davison hat es gesehen.

*(This wave is not complete until this can be manually demonstrated.)*

*Re-planned on 2026-09-10: Warren Davison gave written permission to use and
adapt Draft Sketch. The wave of 2026-09-07 built a licence-clean imitation of
its qualities; this one takes his marks as the base and extends them in his
hand. The swappable theme stays — no longer as a licence fallback, but because
a theme that can be switched is one that can be improved, and because
"Technisch" is what the plan falls back to should the permission ever end.*

Detailed plan, in German, with the converter mapping and the permission
checklist: `.mdd/plans/06-zeichenstil-skizze.md`.

## What we have, and what it is made of

**Draft Sketch** (ArcWatch, April 2020) is an ArcGIS Pro style by Warren
Davison, downloadable as a `.stylx` from its ArcGIS Online item: point, line
and polygon symbols at **three levels of detail** — trees as a point with a
buffer effect (the canopy size) and as a polygon, buildings with hatching and
overshoots at the vertices, a fountain polygon, inky splotches, paint bleed,
lines that wobble and vary in weight. The style sheet in the article lists
every element.

**The format is kind.** A `.stylx` is a **SQLite database**: an `ITEMS` table,
one row per symbol, its definition as **CIM JSON** in `CONTENT`. Readable with
`sqlite3` and `json` from the standard library. An MIT-licensed tool
(notebook and geoprocessing tool, stdlib only) already exports **point/marker
symbols** to SVG — vector markers as `<path>`, picture markers (Base64 PNG) as
files, the y axis flipped once. Lines, fills and geometric effects it does not
cover; that is feature 2.

We will also ask him for the **source assets** (SVG/AI/PNG at full resolution,
the *Field Notes* marks his article says the style was built from): scanned ink
embedded at symbol size holds at map scale, not at a plan's close zoom.

## The permission is a document

Kept outside the public repository, like the security plan; `THIRD_PARTY.md`
in the repo records the date, the scope in one sentence, and the agreed credit
line. The repository carries **no LICENSE** (checked 2026-09-10) — public, all
rights reserved — so his assets sit under their own notice: *used and adapted
with permission of Warren Davison; not licensed to third parties.* A clone of
the repo transfers no rights it does not have.

To be confirmed with him if the permission does not say so — a mail is enough,
and it joins the record: publication of the assets and our derivatives in the
public repo; **commercial** use (Wave 27 makes this a product with revenue);
extensions in his style under the same terms; whether the *Field Notes* assets
are included; his preferred credit; what happens on revocation. And the
courtesy of showing him the result before it goes live.

## What still holds from the first plan

The lessons of doc 58, twice paid for: two-octave wobble, colour variation in
the wash's own hue rather than grey noise, tiles of 2–3 m with 40–50
hand-scattered marks and never a lattice, thin part-transparent outlines —
these now apply to **our extensions**, so they sit beside his marks without a
seam. And the rule that decided both failures: **look, do not reason** — the
Browser pane returns blanks for this SVG; a raster harness is the instrument.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | a-theme-is-a-thing | docs/96-a-theme-is-a-thing.md | complete | 1 |
| 1 | look-before-you-argue | docs/95-look-before-you-argue.md | complete | — |
| 2 | draft-sketch-in-svg | docs/97-draft-sketch-in-svg.md | complete | 1 |
| 3 | what-the-style-has-not-drawn | docs/98-what-the-style-has-not-drawn.md | complete | 2 |
| 4 | paper-bleed-and-a-real-shadow | — | planned | 3 |
| 5 | lettered-by-hand | — | planned | 2 |
| 6 | the-switch-and-the-courtesy | — | planned | 0 |

Three stages, with a **review by the owner after stage 2 and after stage 3**,
and a courtesy round with Davison before stage 3 ships:

- **Stage 1 — the foundation:** 1, then 0. No visible change; a way to see,
  and an interface.

*Order changed on 2026-09-18, before either was built: the contact sheet comes
first. Feature 0's acceptance is that "Technisch" renders pixel-identical to
today's plan, and only a raster of today's plan, taken before the extraction,
can prove that — the wave's own rule, look do not reason. Nothing in the plan's
drawing is tested for its pixels until then.*

*Decided with the owner on 2026-09-18: stage by stage, and I release stage 1;
stage 2 goes to the preview for the owner's review first. Davison's written
permission covers the public repository and commercial use. The work is done
from the `.stylx` alone — his source assets are not asked for.*
- **Stage 2 — his style, on our plan:** 2, 3. The converter, then the garden's
  own vocabulary in his hand.
- **Stage 3 — the finish:** 4, 5, 6.

## Progress

- **2026-09-18 — feature 1, look before you argue** (doc 95), built first.
  `npm run plan:sheet` draws the app's own plan for three synthetic gardens at
  12, 40 and 120 m and with the sun map, in Chromium, one page per cell, and
  keeps a SHA-256 of every cell's pixels in `frontend/sheet/baseline.json`:
  24 cells, light and dark, recorded before anything else in the wave touched
  the plan. The paint budget: 36 ms median for the 102-element city block at
  40 m with the CPU slowed four times.
- **2026-09-18 — feature 0, a theme is a thing** (doc 96). The plan's look
  behind one seam — defs, fills per symbol and level of detail, a bed's fill,
  the one filter — with today's plan as Technisch. All 24 cells as recorded;
  the filter still switches off under `prefers-contrast` and `forced-colors`.
  `CanvasScene.tsx` went from 390 lines to 187.
- **2026-09-18 — stage 1 in production** as **V0.23.200** (merge `9b17cbe`,
  which also carried the close of Waves 21 and 23). Checked on the preview
  first (V0.23.199): the plan drawn through `plan-theme--technisch`, the filter
  in effect, twelve patterns, a fill per kind, no new console error; the smoke
  test passed in both windows. Production serves `index-DXOCVJ1H.js` and
  `index-QKIWPeuJ.css`, the preview's assets.
- **2026-09-18 — stage 2 settled with the owner.** `Draft_Sketch.stylx`
  (17,096,704 bytes, ArcGIS Online item 3215e720f62d42008d125ca1a3219b14, owner
  WarrenDz, changed 2021-01-13) is downloaded once and pinned by its SHA-256,
  not committed; only the generated theme is. `THIRD_PARTY.md`: permission of
  2026-09-10, to use and adapt Draft Sketch in NinaNatur including this public
  repository and commercial use; credit *Zeichenstil nach Draft Sketch von Warren
  Davison, verwendet und angepasst mit seiner Erlaubnis*, with the assistance of
  Louis Hill (@NKYmapLAB) that his item credits.
- **2026-09-18 — feature 2, Draft Sketch in SVG** (doc 97). His style as a
  theme, derived from the pinned file by `python -m scripts.stylx_to_theme`
  and checked byte for byte: 13 of his symbols as patterns and overlays, his
  8 images shipped once (344 KB) and tinted in SVG. Where CIM is silent his own
  style sheet decided: a tint multiplies, a linear ramp starts where its angle
  points, a circular ramp's first colour is its rim, buildings carry ticks.
  Drawn only on the preview by `?theme=draft-sketch`, as a chunk of its own
  that production never fetches and would not serve (`assets/draft-sketch/`);
  his credit on the plan whenever it is his style; `THIRD_PARTY.md` written.
  Paint budget: 69 ms for the city at 40 m against Technisch's 36 — first
  221 ms, until a pattern held one rect and its marks were recorded once.
  Technisch's 24 cells as recorded. Known issues are the review's agenda:
  no bleed yet, no buffered rims, levels of detail at his print ranges.
- **2026-09-18 — feature 3, what the style has not drawn** (doc 98). Roofs by
  type from the server's own roof model (`roof_lines`: ridge, hips, a pent's
  upper edge with a fall arrow), raised beds with a second edge and a shadow,
  hedges hatched on the shaded side, shrubs as his Tree 2, fences and walls in
  his Wood Fence and Brick Wall (a wall's fitted to its own faces), blooms as
  dabs of his watercolour, the viewpoint in his ink, and a north arrow, a true
  scale bar and a title block; his credit a caption beneath the plan. Each
  shadow now falls beneath its own shape. Not drawn, named: conifers (no tree
  carries its kind) and sightlines (no plan draws them). A fourth sheet garden
  for other themes shows it all. Paint budget 85 ms against the 72 ms limit —
  a stage-3 finding; 66 ms with production React against Technisch's 17.
- **2026-09-18 — stage 2 on the preview for the owner's review** as
  **V0.23.203** (merge `ef9b45f`; the first, `9c2ef89`, failed CI: a bare
  `pytest` could not import `scripts`, fixed by pytest's `pythonpath`). Checked
  there with a garden of every kind, made and deleted by a probe: drawn in
  Draft Sketch only with `?theme=draft-sketch`, Technisch without; the theme's
  chunk, stylesheet and twelve images all from `assets/draft-sketch/`, none
  inline; the credit word for word beneath the plan; the server's `roof_lines`
  live (a gable's ridge, a hip's five lines). No console error but the
  anonymous `accounts/me` 401 every page gets. The smoke test passed in both
  windows. The probe's first run failed before it held its garden's token and
  left an empty "Draft-Sketch-Probe" garden on the preview, beyond reach
  without the token; preview data is for testing and goes with the next reset.
- **2026-09-20 — the owner's first review of stage 2**, three notes, all on the
  phone. (1) *"so white"*: the garden's ground is now his lawn wash at half
  opacity — pale green paper with a real lawn darker on it
  (`--plan-ground-fill`); ours is unchanged. (2) *"zooming in removes all
  buildings"*: reproduced on the preview with a garden imported from the map —
  59 streets, 10 houses. Nothing vanishes; the houses stand outside the plot,
  so a zoom into the middle of the garden lands on empty ground, which was a
  blank white sheet and is now grass. Technisch does the same. No code changed
  for it; if it still reads as a bug with the ground drawn, it belongs to the
  view, not the theme. (3) *"the streets overlap and look funny, drawn as edges
  and nodes"*: right — a street is one element per way, so an outline per band
  crossed every junction. The seam grew a `Plan` member, drawn once for the
  whole plan, and `ours/Roads.tsx` draws the network's outline masked by
  itself: only the line outside the roads survives, nothing crosses a junction
  (doc 98). Worked out once per garden and zoom step, not per drag frame.
  Technisch's 24 cells as recorded, the converter's output byte for byte,
  paint 83 ms. On the preview afterwards, with that imported city on a phone
  and the CPU slowed four times, a zoom step costs 98 ms in his style against
  Technisch's 66 — 1.5×, inside the wave's rule, where the sheet's synthetic
  city at 40 m is over it. Looking at the result showed a fourth thing, from
  feature 3 rather than from today: the tool's hint and his credit were drawn
  over each other at the plan's bottom edge, in both layouts. The hint now
  hangs inside the drawing, under the zoom controls at its top edge — the first
  try put it on the title block instead, which is what the bottom corner is
  for — and the caption has its line. Measured in both layouts: no two of the
  controls, the hint, the title block and the credit touch. A pale wedge of
  paper where two ways meet at a bend is left, and named in doc 98: it is the
  bands' own fill, which Technisch is missing too.

- **2026-09-20 — feature 4, paper, bleed and a real shadow** (doc 99). Three
  things, each decided by a measurement rather than by taste. **Levels of
  detail** are now asked per shape, in pixels across — 48 for his richest, 14
  for the middle one — because the plan-wide answer has to take the detail off
  the houses (89 pixels at 40 m) to save what the shrubs cost (13): the city
  goes from 401 marks and 85 ms to 286 and 73. **The shadow** is the one the
  sun casts: `solar/drawing` fixes the moment at mid-June, three hours after
  solar noon at the garden's own longitude, and every obstacle carries the
  offset its shadow has then, from the same `shading_height` the light model
  uses; the drawing sweeps the outline rather than moving it, and does not
  wobble it, which took the frame to 69 ms — cheaper than the style's pretend
  shadows. **The paper** is his own texture in his own lightest tint, emitted
  by the converter as a pattern of its own and drawn under the whole plan; how
  much of it shows is ours. **The bleed was tried and dropped**: believable, it
  is invisible; visible, it warps his textures, because his washes are
  photographs of paper and a displacement map moves the grain with the edge.
  Either way it cost 8–13 ms of the frame. Technisch's 24 cells as recorded.
  The budget rule is still not met — Technisch measures 21 ms today, so twice
  it is 42 against the plan's 69 — and doc 99 says so rather than tuning it
  away.

- **2026-09-20 — feature 6's switch, ahead of feature 5** (doc 100). The
  gardener picks the style in the header's menu — a fieldset of radios, one per
  style — and their browser remembers it (`ninanatur.plan-theme`). The address
  still decides where it is given (`?theme=`), the deployment still decides what
  is on offer (Draft Sketch only where its files are served), and
  `prefers-contrast: more` or `forced-colors` takes the choice away and says so:
  a style made of washes and pencil is the wrong answer to "make this clearer",
  where doc 98 used to answer it by hiding the ink and leaving a drawing with
  none of its marks. Checked on the local app: Technisch at first, his style
  after choosing, still his after a reload. What is left of the feature is the
  courtesy — showing Davison the result — which is the owner's to do.
- **2026-09-20 — feature 5 is waiting on one decision.** His file has no
  lettering at all: 97 symbols, 48 polygons, 35 lines, 14 points, and not one
  font name or text symbol in any of them. So there is no hand of his to match,
  and the plan's lettering is a choice of ours: an OFL hand — *Patrick Hand*
  reads upright like a draughtsman's, *Caveat* is more of a note — bundled with
  the app, since the policy allows no CDN (`font-src 'self'`). That is a
  third-party file in a public repository, so it waits for the owner. What
  could be done without it is done (doc 101): the plan's lettering measures
  15.3:1 in the title block, 12.2:1 over the darkest part of his paper grain,
  5.5 and 7.6 for his credit on a light and a dark page — every one of them
  past 4.5:1, to be measured again once a thin hand replaces the system sans.

## What each one is

### 0. a-theme-is-a-thing

Unchanged in substance. A `PlanTheme` interface — tokens, symbols per kind and
level of detail, filters per layer, rules (LoD ladder, overshoot length,
splotch density, shadow moment, label style), modes — and the canvas reads
everything through it. **"Technisch"** is extracted as the first theme with no
visible change and every test green; it is also the fallback the permission
question needs. The **provenance rule** replaces the clean-room rule: every
symbol file carries a header naming its author — *Warren Davison (Draft
Sketch)*, *adapted from Draft Sketch*, or *NinaNatur, in the style of Draft
Sketch* — and a test refuses a file without one.

### 1. look-before-you-argue

`npm run plan:sheet`: the real `CanvasScene` for three fixture gardens (small,
farmyard, city) at three zoom levels, rendered to PNG with Playwright/Chromium,
laid out as a contact sheet; a before/after gallery in the feature doc. The
performance budget is measured here too: paint time at a hundred elements on a
phone, one filter chain per layer, the interactive layer filter-free.

### 2. draft-sketch-in-svg

`scripts/stylx_to_theme.py`, standard library plus Pillow, deterministic,
generating `frontend/src/themes/draft-sketch/` — `tokens.css`, `symbols.svg`,
`rules.ts` — from the `.stylx` checked in under `assets/draft-sketch/` with its
notice. A test regenerates and diffs: the theme is a derivation, not handwork.

| CIM layer | SVG | Note |
|---|---|---|
| `CIMVectorMarker` | `<symbol>` with `<path d>`, curves 1:1, one y-flip transform | covered by the MIT tool |
| `CIMPictureMarker` / `CIMPictureFill` (Base64 PNG) | `<image>` / `<pattern>` with `<image>`, tiles in **metres** (doc 41) | keep 2× resolution; measure bundle bytes, sprite-sheet past a few hundred KB |
| solid fills and strokes | `fill`/`stroke`, alpha 0–100 → 0–1, colours as **tokens** — his palette becomes the theme's; dark mode derived per doc 41 | |
| `CIMHatchFill` | rotated `<pattern>` of the line symbol | building hatching |
| effects `Wave`, `Jog`, `Offset`, `Dashes` | **geometry in `canvas/`**, precomputed with his parameters; dashes as `stroke-dasharray` | never a filter on the hit layer; vertex overshoots come the same way |
| `Buffer` effect (tree point → canopy) | our crown radius (`canopy_of`, editable) | data, not a symbol parameter |
| `CIMCharacterMarker` | glyph outline as `<path>` only if the font is free; else redrawn | feature 5 checks the font |
| three scale ranges | our LoD ladder over `spacing` | points at print scale → metres: a rule per symbol, set on the contact sheet |

Named losses: ArcGIS label placement (we have labels), "random" waveforms
(emulated with a fixed seed), anything true only at a print scale.

### 3. what-the-style-has-not-drawn

A garden plan needs what a city map does not. Each extension is bound to data
the plan already has, and drawn in his hand — same medium as his assets (ink
and scan if his are scanned; the same stroke set if vector), same paper, same
ink, same wobble:

| Need | Data | Drawing |
|---|---|---|
| **blooms** in ten colours, three sizes | `bloom/palette.py`, doc 56, secondary colour from plan 08 | painted dabs, grey out of season |
| **deciduous vs conifer** trees, crown by size, three LoDs | `deciduousness`, `growth_form`, `canopy_of` | two crown families — lobed / serrated; a bare deciduous crown in the winter day playback |
| shrubs | `growth_form` | smaller, denser crowns |
| **hedges** | kind `hedge` | a clipped mass, hatched on the shade side |
| **houses by roof type** | `roof`, `roofshape` (ridge direction, eaves) | ridge along the long axis, hip lines, flat as a plane, pent with one eaves edge — the drawing says what the model knows |
| sheds, walls, fences | kinds | battens, masonry, posts in his line |
| **raised beds** | `height_above_ground` > 0 | double outline with a shadow edge |
| garden boundary | kind `garden` | a dashed sketch line |
| lawn, gravel, paving, paths, streets, pond | kinds | his fills where they exist; otherwise new, under the doc 58 rules |
| **compass rose, scale bar, title block** (name, date, scale) | `GardenOut` | a drawing has them; today the plan says "N ↑" |
| viewpoint, sightlines | Wave 9 | in the same ink |

The sun map and the day shadows keep their two flat inks (doc 65): they are
statements, not decoration.

### 4. paper-bleed-and-a-real-shadow

The paper grain and the paint bleed as filter primitives where SVG cannot do
them as geometry, tuned on the contact sheet; the LoD thresholds set in metres;
and **a shadow the sun actually casts** — the drawing shadow of standing things
is the real shadow of one reference moment (15 June, 15:00), short and pale.
No other plan knows where the sun is.

### 5. lettered-by-hand

Which font his text symbols use is checked first: free (OFL) → bundled;
otherwise an OFL hand font (*Patrick Hand*, *Caveat*) — labels in the plan
only, UI text stays the system font, no CDN (Wave 20's CSP). Dark-mode tokens
for every wash; contrast measured for labels, the sun map and the bloom dabs
over paper; `prefers-contrast: more` and `forced-colors` select "Technisch".

### 6. the-switch-and-the-courtesy

The theme picker in the header menu, remembered per viewer; the credit line on
the page and in `THIRD_PARTY.md`; the third slot documented; and Davison shown
the result before it goes live.

## Acceptance

- Somebody shown the contact sheet calls it a drawing of a garden, not a
  diagram of one — doc 58's criterion, now testable.
- "Technisch" renders pixel-identical to today's plan.
- Regenerating the theme from the `.stylx` yields byte-identical output.
- Every symbol file carries its provenance header; no external asset loads at
  runtime; the permission record and `THIRD_PARTY.md` exist before feature 2
  merges.
- Paint time at a hundred elements stays within the measured budget on a phone.

## Open Research

- Raster or vector: what his assets are made of decides how the extensions are
  made. Ask, and open the `.stylx` before feature 3 is scoped.
- Units: CIM points at print scale into plan metres — set per symbol on the
  contact sheet, not computed.
- Bundle weight of picture fills as data URIs; when a sprite sheet is needed.

## Deliberately not in this wave

- Any change to what the plan means: sun map, bloom colours, selection and hit
  targets keep their semantics and their accessibility.
- Using anything of Esri's own default styles. The permission is Davison's, for
  his work.
- Filling the third theme slot.
