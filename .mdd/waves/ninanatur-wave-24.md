---
id: ninanatur-wave-24
title: "Wave 24: A drawing of a garden"
initiative: ninanatur
initiative_version: 23
status: planned
depends_on: ninanatur-wave-23
demo_state: "Der Plan ist in Warren Davisons Draft-Sketch-Handschrift gezeichnet — mit seiner schriftlichen Erlaubnis, aus seinem Stil geholt und um das erweitert, was ein Garten braucht und eine Stadtkarte nicht: Blüten in ihrer Farbe, Laub- und Nadelbäume, Sträucher, Hecken, Dächer nach ihrer Form, Hochbeete, eine Kompassrose und ein Titelblock. Ein Schalter stellt den technischen Plan zurück. Beurteilt wurde am Kontaktbogen, und Davison hat es gesehen."
created: 2026-09-07
hash: eda106b2
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
| 0 | a-theme-is-a-thing | — | planned | — |
| 1 | look-before-you-argue | — | planned | 0 |
| 2 | draft-sketch-in-svg | — | planned | 1 |
| 3 | what-the-style-has-not-drawn | — | planned | 2 |
| 4 | paper-bleed-and-a-real-shadow | — | planned | 3 |
| 5 | lettered-by-hand | — | planned | 2 |
| 6 | the-switch-and-the-courtesy | — | planned | 0 |

Three stages, with a **review by the owner after stage 2 and after stage 3**,
and a courtesy round with Davison before stage 3 ships:

- **Stage 1 — the foundation:** 0, 1. No visible change; an interface and a
  way to see.
- **Stage 2 — his style, on our plan:** 2, 3. The converter, then the garden's
  own vocabulary in his hand.
- **Stage 3 — the finish:** 4, 5, 6.

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
