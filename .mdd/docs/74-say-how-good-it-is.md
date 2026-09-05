---
id: 74-say-how-good-it-is
title: Say How Good It Is
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-17
wave_status: active
depends_on: [69-a-window-of-ground]
relates: [65-the-shade-switch, 73-which-way-does-it-fall]
source_files:
  - ninanatur/garden/relief.py
  - ninanatur/api/light.py
  - frontend/src/components/ReliefMap.tsx
  - frontend/src/components/ShadeSwitch.tsx
  - frontend/src/styles.css
routes:
  - GET /api/v1/gardens/{token}/terrain
models: [terrain_window]
test_files:
  - tests/test_relief.py
  - tests/test_light_api.py
  - frontend/src/components/ReliefMap.test.tsx
  - frontend/src/components/ShadeSwitch.test.tsx
data_flow: reads-existing
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [relief, hillshade, provenance, licensing, contrast]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The acquisition year is not shown: it is per flight strip, and no coverage service reports it in a GetCoverage response. The BKG states 2000–2022 nationally."
  - "A uniform hillside draws a uniform, near-invisible tint. That is correct hillshading and it means the picture carries structure while the words carry the fall."
---

# Say How Good It Is

Feature 6 of Wave 17, and the one the whole wave is for. Wave 16 made a map
somebody could trust cell by cell; being silently flat then became the largest
error in it. This is the part that stops being silent.

## The ground, drawn

`GET .../terrain` returns relief shading — how each cell stands to a lamp in the
north-west at 45°, the cartographic convention. Lighting relief from the
south-east makes valleys read as ridges to most people, which is why every atlas
in the world puts the lamp where the sun never is.

**0.5 means level**, and that is the contract rather than a detail. Lit
absolutely, flat ground comes out at 0.854 — the cosine of the lamp's own
altitude — and a drawing treating 0.5 as neutral would then wash the whole plan
in a uniform tint. That is exactly what the first version did, and the browser
said so: a median opacity of 0.186 across every cell.

Two more things the first version got wrong, both found by looking rather than
reasoning:

**39,999 rectangles.** The stored window reaches 100 m out because the shading
needs the neighbours; the drawing is the garden, which is twenty. Cropping to
the plan's own extent plus ten metres took it to **1,319 cells and a 7 KB
payload** — in a canvas that redraws on every pan.

**A dark ring around every gap.** Unsurveyed ground fell back to a fixed 0.5
while level ground lit at 0.854, so every hole in the data drew a darker patch —
the one shape a viewer would be certain meant something. Now a gap lights
exactly like level ground, and a test compares the two rather than a constant.

The drawing itself is opacity and nothing else: one grey, two directions, no
ramp of colour. The plan already spends its colour on flowers and on what things
are. Measured on a real hillside in Wuppertal: 0.4 % to 7.4 % opacity — present
when looked for, invisible while placing a bed.

## Saying how good it is

Under the map, in words:

> Gelände 253–279 m ü. NHN, 25.9 m Unterschied · © Geobasis NRW · Gitterweite
> 1 m, Höhengenauigkeit etwa ± 0,3 m

The credit is not decoration. dl-de/by-2-0 and CC-BY-4.0 both require it, and a
height shown without it is a height used outside its licence — the same rule
that governs every trait value in this project.

The accuracy is not decoration either. A number shown without it invites more
confidence than it earned, and Baden-Württemberg gets its own sentence:

> Höhen nur in ganzen Metern — feinere Neigungen sieht dieser Dienst nicht.

## And where there is none

> Für diese Adresse liegen keine Höhendaten vor — der Plan rechnet mit ebenem
> Gelände.

Nine Bundesländer have no service in the registry. A garden there is computed on
flat ground exactly as every garden was before Wave 17 — which is fine. Being
quiet about it is what this wave exists to end.

Three states, and the page distinguishes all three: ground fetched, no service
for this address, and *not asked yet* — which says nothing at all, because a
garden nobody has looked at is not a flat garden.

## The dark theme, again

Wave 16 learned that nothing can be painted onto `#12160f` that reads as darker;
a near-black wash measures 1.09 contrast against it. The same applies here and
the answer is the same: in dark mode the **lit** side of a slope carries the
whole signal and the shadowed side is barely there. Stated in the stylesheet
next to the tokens rather than left for somebody to rediscover.

## What is still not said

The acquisition year. It is a property of a flight strip, not of a coverage
response, and no service in the registry reports it in the GeoTIFF it hands
back. The BKG's national statement is 2000–2022; per garden, this model does not
know, and the honest thing was to omit it rather than print a range that looks
like a fact about this address.
