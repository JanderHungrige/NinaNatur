---
id: ninanatur-wave-21
title: "Wave 21: The roof, said properly"
initiative: ninanatur
initiative_version: 21
status: planned
depends_on: ninanatur-wave-19
demo_state: "Ein Haus aus dem Kartenimport kennt seine Traufhöhe, ohne dass jemand sie eintippt, und sagt woher; die Nordseite eines Satteldachs bekommt sichtbar weniger Sonne als die Südseite, weil die Neigung gemessen und nicht angenommen ist."
created: 2026-09-07
hash: d2ff046b
---

# Wave 21: The roof, said properly

## Demo-State

Ein Haus aus dem Kartenimport kennt seine Traufhöhe, ohne dass jemand sie
eintippt, und sagt woher; die Nordseite eines Satteldachs bekommt sichtbar
weniger Sonne als die Südseite, weil die Neigung gemessen und nicht angenommen
ist.

*(This wave is not complete until this can be manually demonstrated.)*

## Why it is its own wave

On 2026-09-07 the sun stopped being computed on the ground under a building and
started being computed on its roof, at the roof's own height and pitch. That
works, and a north pitch now genuinely reads darker than a south one — measured,
10.2 h against 11.7 h on a 38° gable.

It rests on three assumptions, and each of them is doing real work:

| Assumed | Because | What it costs |
|---|---|---|
| The ridge runs along the long axis of the footprint | Nothing stored carries a ridge direction | An L-shaped or turned house gets its pitches pointed the wrong way |
| The eaves are at 75 % of the ridge | `building:levels` is the better answer and OSM often lacks it | A 9.5 m house gets a 28° pitch instead of 38–45°, so the north/south difference is roughly halved |
| A pent roof has no known fall | It genuinely has none in the data | Its two faces are not distinguished at all |

The eaves are the one that decides how big the whole effect is, which is why it
is the first thing here. A field was added to the element menu so somebody
*can* type it — but a feature that only works when the user does homework is a
feature most gardens will never see.

## Scope, provisionally

- **Eaves from the survey, not from a fraction.** NRW's LoD2 already carries
  labelled `GroundSurface` and `RoofSurface` polygons, and Wave 19 already
  parses that file for heights. The eaves height is the lowest edge of the roof
  surfaces — it is in the data this project is already downloading.
- **And the ridge direction with it.** From the same surfaces. That removes the
  long-axis assumption entirely for every building in NRW, and the roof type
  becomes a measurement rather than a shape ratio.
- **`building:levels` as the fallback** wherever OSM carries it; `eaves_from_levels`
  exists already and is only used at import.
- **Say which it is.** A measured eaves height and an assumed one must not look
  alike, exactly as `height_source` already distinguishes a surveyed height from
  a guessed one.
- **The other eleven Bundesländer.** NRW is the only state whose LoD2 is
  addressable by coordinate. What the rest can offer, if anything, is research.

## Deliberately not in it

- A general 3D building model. The roof is a surface for the sun to land on, not
  a thing to render.
- Solar-yield figures. The model reports **hours of direct sun**, not energy,
  and a roof that reads 11 h is not a kWh claim. Turning this into a solar
  calculator would need irradiance, angle of incidence and a weather series —
  a different project, and one where being approximately right is not good
  enough.
