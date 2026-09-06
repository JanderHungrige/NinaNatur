---
id: 82-the-roof-it-actually-has
title: The Roof It Actually Has
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-19
wave_status: active
depends_on: [80-which-models-and-whose]
relates: [81-a-house-with-a-measured-height]
source_files:
  - ninanatur/geo/lod2.py
  - ninanatur/garden/roofs.py
  - ninanatur/api/schemas.py
  - frontend/src/roofs.ts
routes: []
models: [element]
test_files:
  - tests/test_lod2.py
  - tests/test_roofs.py
data_flow: greenfield
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [lod2, citygml, roofs, adv, eaves, buildings]
path: Map/Buildings
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Only Nordrhein-Westfalen's tile scheme is implemented; other states publish LoD2 differently or not addressably."
  - "329 of 768 flat roofs still yield an eaves value below their ridge — probably parapets. Harmless, because shading_height ignores eaves for a flat roof."
  - "Nothing yet joins these buildings to the ones in a garden. That is feature 3."
---

# The Roof It Actually Has

Feature 2 of Wave 19. A surface model says how tall a building is. Only the
official 3D model says what shape its roof has — and Wave 16 asks a person to
answer that, per building, for buildings that are not theirs and that they may
never have seen from the side.

## Two new members, because a survey is not an absence

`Mischform` is a fifth of the buildings in a Cologne tile and `Sonstiges`
another twentieth. Folding them into `unknown` would say "nobody looked" about
an answer a surveyor gave — in a project that carries provenance on every trait
value it stores.

| AdV | | Share | Roof | Rise kept |
|---|---|---|---|---|
| 1000 | Flachdach | 35.1 % | `flat` | 1.0 |
| 3100 | Satteldach | 22.4 % | `gable` | 0.5 |
| 5000 | Mischform | 19.9 % | **`mix`** | **0.8** |
| 2100/2200 | Pultdach | 17.3 % | `pent` | 0.6 |
| 9999 etc. | Sonstiges, Shed, Kuppel, Turm | 4.5 % | **`other`** | **1.0** |
| 3200/3300/3500 | Walm, Krüppelwalm, Zelt | 0.9 % | `hip` | 0.4 |

`mix` keeps 0.8 because a mixed roof casts from its tallest section — more than
a pure gable, less than a flat block. It is the weakest number in the roof model
and the first to revisit. `other` keeps everything: shed, barrel, dome and tower
all carry their bulk high. It shares a number with `unknown` and not a meaning.

The vocabulary now lives in four places — the model, the API schema, the
frontend picker and the AdV map — and a pytest guard fails when they drift, as
it already did the moment these two were added.

## A third of the tile is easy to lose

The first parser read 947 buildings from a tile that holds **2,189** roofs. The
missing two-thirds are `BuildingPart`s: CityGML lets a building consist of
wings, each with its own roof and height, and then the building itself carries
neither. In the Cologne tile 385 of 1,332 buildings are like that, made of 1,242
parts between them.

Emitting each part separately is also the better answer for shading. A long low
wing beside a tall gabled one is two prisms; treating it as one would shade with
whichever height happened to win.

The corrected parser returns exactly 2,189 — the same number as a plain count of
`<bldg:roofType>` in the file, which is the check worth having. And the
distribution and heights then match a measurement taken independently while the
wave was planned, down to the decimal: 35.1 % flat, median 14.2 m, p90 20.4 m.

## The footprint is labelled, not inferred

An earlier version took "the ring whose points sit lowest". That is the same
answer on level ground and quietly a **wall** for a building on a slope.

CityGML labels its faces, and there is exactly one `GroundSurface` per building
— 2,189 of them in a tile with 2,189 roofs. So the footprint is read.

## And the eaves came out of the same parse

The lowest point of the `RoofSurface`s is where the walls stop. **78 % of
buildings give one**, and for pitched roofs it lands at **0.78 of the height** —
against the 0.75 Wave 16 assumed.

That is a pleasing result twice over: the assumption was very nearly right, and
it no longer has to be one.

## Streamed, not loaded

A 36 MB document parsed into a tree is 36 MB of tree. `iterparse` with a
`clear()` after each building reads the same tile in 0.7 s and keeps a few
hundred bytes per building.

The clear happens **after** the building is read, not before: a part's end event
fires before its parent's, and clearing early would leave a parent no geometry
to find. That does not arise today — a parent with parts carries no roof and is
skipped — but it would the moment one did.
