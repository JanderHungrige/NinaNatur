---
id: ninanatur-wave-19
title: "Wave 19: Houses that measure themselves"
initiative: ninanatur
initiative_version: 20
status: planned
depends_on: ninanatur-wave-18
demo_state: "Ein Haus in der Nachbarschaft trägt seine gemessene Höhe und seine wirkliche Dachform, aus dem amtlichen Gebäudemodell statt aus drei Metern pro Geschoss — und der Plan sagt bei jedem Objekt, ob die Höhe gemessen, geschätzt oder von Hand eingetragen ist. Wer es besser weiß, überschreibt es, und das bleibt so."
created: 2026-09-05
hash: 85126275
---

# Wave 19: Houses that measure themselves

## Demo-State

Ein Haus in der Nachbarschaft trägt seine gemessene Höhe und seine wirkliche
Dachform, aus dem amtlichen Gebäudemodell statt aus drei Metern pro Geschoss —
und der Plan sagt bei jedem Objekt, ob die Höhe gemessen, geschätzt oder von
Hand eingetragen ist. Wer es besser weiß, überschreibt es, und das bleibt so.

*(This wave is not complete until this can be manually demonstrated.)*

## Why this is a wave

Every shading answer this app gives rests on a building height, and every
building height today is one of two guesses: `building:levels × 3 m` where OSM
says how many storeys, or a default where it does not. Wave 16 made the
consequence visible cell by cell, and Wave 17 will put those buildings on
measured ground. Standing a guess on a measurement is the wrong way round.

Wave 16 also asks the user to pick a roof shape by hand, per building, for
buildings that are not theirs and that they may never have seen from the side.

Both are already surveyed, statewide, as open data.

## What the data actually holds

Probed on 2026-09-05, against Geobasis NRW, and every figure below is measured
rather than quoted.

### LoD2 — the buildings

NRW ships the LoD2 3D-Gebäudemodell as **CityGML in 1 km² tiles** with a
machine-readable index, under **dl-de/zero-2-0**, "kostenfrei und zur Nutzung
ohne Einschränkungen oder Bedingungen". The tile name is computable from the UTM
coordinates — `LoD2_32_354_5643_1_NW.gml` is easting 354 km, northing 5643 km —
so no search step is needed to find the right one.

One tile over Cologne: **38.5 MB, 3.9 s, 2,189 buildings — every single one of
them carrying `measuredHeight` and `roofType`.** Also per building: the AdV
identifier, the municipality key, `Grundrissaktualitaet` (the footprint's own
date), and `DatenquelleDachhoehe` / `DatenquelleBodenhoehe` — provenance built
into the product, which is a pleasant thing to find in a project with this one's
rules.

The roof shapes in that tile:

| AdV | Shape | Share | Maps to |
|---|---|---|---|
| 1000 | Flachdach | 35.1 % | `flat` |
| 3100 | Satteldach | 22.4 % | `gable` |
| 5000 | Mischform | 19.9 % | **`unknown`** |
| 2100 | Pultdach | 17.3 % | `pent` |
| 9999 | Sonstiges | 4.5 % | **`unknown`** |
| 3200 | Walmdach | 0.8 % | `hip` |
| 3500 | Zeltdach | 1 building | `hip` |

**75.6 % land on one of the four shapes Wave 16 already models; 24.4 % become
`unknown`.** That is not a defect. `unknown` keeps the whole height in
`RISE_KEPT`, which is the conservative direction — a garden told it has more sun
than it has is the error that kills a plant.

Heights in the same tile: median 14.2 m, 10th percentile 3.3 m, 90th 20.4 m.
Stated accuracy **± 1 m**, with "grobe Abweichungen" possible on complicated
roofs. Derived July 2026 from measurement data of 2019–2025.

Compare that with what it replaces. A university building tagged
`building:levels=5` is 15 m under the storey assumption. It is 20 m.

### nDOM — everything else that is standing

The normalised surface model — surface minus terrain, so object height above
ground — is served by the **same WCS host, same licence, same bbox subsetting**
as the terrain in Wave 17, at **0.5 m**: `nw_ndom`, 640 KB for a 200 m window,
one request.

Over a Cologne suburb it reads as it should: a third of the window at ground
level, then hedges and cars, then garages, then roofs and crowns.

Crossed with footprints it measures buildings — and it measures its own failure
modes, which is why it is the *second* source here and not the first. A 30 m²
outbuilding read 17.0 m because a tree hangs over it. A 60 m² kindergarten read
6.5 m median against a 12.8 m 95th percentile, for the same reason. Footprints
have to be eroded before they are sampled.

### Trees are not labelled

NRW's nine point classes have **no vegetation class at all** — a tree is a
`Last Return nicht Boden`, like a car or a roof. So a crown is "tall nDOM
outside a building footprint", which is detection rather than lookup.

And no elevation product knows a species. Wave 16 needs the species, because a
crown's transmission depends on whether it drops its leaves. A detected tree
therefore arrives without one and falls to the existing default — broadleaf in
leaf — which is stated rather than hidden.

## The shape of the fetch: tile in, table out

A 38.5 MB tile is not a per-garden download and not a thing to keep. It is the
same pattern as Wave 17's horizon ring: **fetch something large once, distil it,
throw the source away.**

| | |
|---|---|
| In | one 1 km² CityGML tile, 1.5–40 MB depending on density |
| Kept | per building: id, footprint, height, roof shape, currency, source — a few hundred KB for two thousand buildings |
| Shared by | every garden in that square kilometre, forever, because it does not change between derivations |

Cached on the volume like the terrain window, keyed by tile rather than by
garden, never in the image.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | which-models-and-whose | — | planned | — |
| 1 | a-house-with-a-measured-height | — | planned | 0 |
| 2 | the-roof-it-actually-has | — | planned | 1 |
| 3 | measured-surveyed-or-assumed | — | planned | 1 |
| 4 | what-else-is-standing-there | — | planned | 0 |

Two stages:

- **Stage 1 — the houses:** 0, 1, 2, 3.
- **Stage 2 — the rest of what stands there:** 4. Separable on purpose: it is
  the half that can fail, and the wave is worth shipping without it.

## What each one is

### 0. which-models-and-whose

The third registry, after orthophotos and terrain, and the same rule: read from
the service, not from a summary; a state with nothing gets no entry; a licence
that does not permit this use is a state without an entry.

Two products per state, and they are different questions:

- **LoD2** — how it is delivered. NRW's addressable 1 km² tiles with an index is
  the good case; a package per Gemeinde is the bad one, and a WFS with a bbox
  would be the best. **Unknown for fifteen states** and the main work of this
  feature.
- **nDOM or DOM** — a coverage service, the way Wave 17's registry already
  records one. Where only a DOM exists, the terrain has to be subtracted, which
  Wave 17 has fetched anyway.

### 1. a-house-with-a-measured-height

Tile → distilled table → matched to the buildings the surroundings model already
placed.

The matching is the part to get right. OSM gives what a building *is*
(`building=house`, `garage`, `greenhouse` — which drives the plan's skin and
whether it casts at all); LoD2 gives how tall it is. They have to be joined
spatially, and **terraced houses are the hard case**: centroids five metres
apart, and matching to the nearest one silently gives the neighbour's roof to
the neighbour's neighbour. Footprint overlap, not centroid distance.

A building with no match keeps the storey assumption. That is the current
behaviour and remains correct for states with no model.

### 2. the-roof-it-actually-has

The AdV code list onto `Roof`, per the table above, with `Mischform` and
`Sonstiges` going to `unknown` rather than to a guess.

**And the eaves, if the geometry gives them cheaply.** `eaves_m` is currently a
default fraction of the height. In LoD2 the eaves are where the wall surfaces
end and the roof surfaces begin — available in the solid, at the cost of parsing
more of it than the footprint needs. Take it if it comes out of the same parse;
fall back to `DEFAULT_EAVES_FRACTION` otherwise, and say which.

### 3. measured-surveyed-or-assumed

The wave's honesty half, and the reason it is stage 1 rather than an afterthought.

Every height in the plan gets a provenance, the same way every trait value does:
**gemessen** (LoD2 or nDOM, with the year and the ± 1 m), **geschätzt** (storeys
× 3 m, or the default), or **eingetragen** (the user).

And the ordering, which is the whole point: **the user's own entry wins over the
survey.** A gardener can see the house. The model saw it from an aeroplane in
2021. Where they disagree, the person standing in the garden is right — and their
value has to survive the next tile refresh, which means it is stored as an
override rather than as a value to be overwritten.

That is the same shape as the manual colours from Wave 15, and for the same
reason.

### 4. what-else-is-standing-there

nDOM above a threshold, outside every known footprint, segmented into blobs:
a measured height, a crown radius from the blob's extent, and a position. Entered
as obstacles of kind *tree*, marked measured, species unknown.

This is worth having because a large neighbouring tree currently does not exist
at all unless the user draws it — and it is the single most common thing that
shades a German garden.

It is also the feature that will produce nonsense if it is not careful: hedges,
cars, a pergola, a marquee, a bad terrain value under a slope. It needs a
minimum height, a minimum footprint, an exclusion around buildings, and a plain
way for the user to delete what is wrong. **A suggestion the user confirms, not
an object that simply appears** — the same standing as the misplacement warning
in Wave 16.

## What the model will not know

- **± 1 m on a building**, and worse on complicated roofs. Written next to the
  value, not buried.
- **The model is derived from flights of 2019–2025.** A house built in 2026 is
  not in it, a demolished one lingers until the next derivation, and
  `Grundrissaktualitaet` per building is the honest thing to show.
- **Mischform is a fifth of the buildings** — known to be complicated, unknown in
  shape, and treated as full height.
- **LoD2 is buildings, not garden structures.** A pergola, a polytunnel or a big
  shed may or may not be in the model, depending on whether it is in ALKIS.
- **A detected tree has no species**, and species is what the canopy model wants.
- **A tree that was 8 m in 2021 is not 8 m now.** Trees grow; buildings do not.
  The acquisition year matters more for feature 4 than for feature 1.

## Open Research

- **How the other fifteen states deliver LoD2.** NRW's indexed 1 km² tiles are
  the good case and may not be the common one. A package per Gemeinde would
  change this from "fetch a tile" to "fetch a city", and that would change the
  answer about whether to do it at all.
- **Footprint overlap or centroid.** Terraced housing decides this; test on a
  street of them, not on a detached house.
- **Whether LoD2 should replace OSM as the footprint source** where both exist.
  LoD2 footprints come from ALKIS and are more accurate; OSM carries the tags
  that say what a thing is. Probably both, joined — but that is a decision with
  consequences for `surroundings.py` and should be taken deliberately.
- **What the ±1 m does to a shade map.** Wave 16's grid is sensitive to height;
  a metre of building is several metres of shadow at a low sun. It may be worth
  showing the answer as a band rather than a line — which would be a change to
  how the whole map reads, and therefore its own wave if it is worth anything.

## Deliberately not in this wave

- **Tree species from anywhere.** Municipal Baumkataster carry species, height
  and crown for street and park trees in the cities that publish one — a
  patchwork, and garden trees are absent from all of them.
- **LoD3, textures, or anything about the inside of a building.**
- **Re-deriving heights from the point cloud.** LoD2 already did it properly.
