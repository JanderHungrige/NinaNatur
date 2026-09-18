---
id: ninanatur-wave-21
title: "Wave 21: The roof, said properly"
initiative: ninanatur
initiative_version: 21
status: in_progress
depends_on: ninanatur-wave-19
demo_state: "Ein Haus aus dem Kartenimport kennt seine Traufhöhe, ohne dass jemand sie eintippt, und sagt woher; die Nordseite eines Satteldachs bekommt sichtbar weniger Sonne als die Südseite, weil die Neigung gemessen und nicht angenommen ist."
created: 2026-09-07
hash: 8e0ac448
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

## What was already there (found 2026-09-18)

The eaves row of the table above was half answered before this wave was
written. Wave 19's reader takes the eaves from the lowest edge of the roof
surfaces (doc 82: 78 % of buildings give one, and pitched roofs land at 0.78 of
the ridge), and a matched house stores it. What nothing does is say so: an
eaves height from the survey, one from the storey count, one somebody typed and
the ¾ assumption look exactly alike on the page. And the form that shows them
sends every field back on save, so renaming a surveyed house marks its height
as typed — after which no refresh measures it again.

The ridge row is worse than it looked. Measured on 2026-09-18 against three
cached NRW tiles (two in Köln, one in Wuppertal), comparing the ridge the roof
faces say with the one `roofshape` assumes:

| Gable parts | Ridge within 10° of the long axis | Turned by 45° or more |
|---|---|---|
| 1,725 | 610 (35 %) | **1,114 (65 %)** |

The turned ones are typically narrow, deep footprints whose ridge runs parallel
to the street — terraced houses — but not only: among footprints of 80–250 m²
at least 1.3 times as long as wide, 197 of 351 are turned too. Their pitches,
which the model calls north and south, face east and west. With the surveyed
ridge the pitch the model derives from eaves, ridge height and span matches the
surveyed faces to a median of 0.1°, against 6.9° with the assumed ridge (13.1°
for the turned ones). For hip roofs the faces cancel each other out, and the
roof's highest edge is the better reading: it finds a ridge on 44 of 46, and
agrees with the faces on 99 % of the gables where both exist.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | where-the-roof-came-from | — | planned | — |
| 2 | which-way-the-ridge-runs | — | planned | 1 |

### 1. where-the-roof-came-from

The eaves get their own provenance beside `height_source` and `roof_source`:
surveyed, from the storey count, typed, or nobody has said — and then the page
says that ¾ of the ridge is assumed. The gardener's word wins per value rather
than per building: a typed roof shape or eaves height survives the next
refresh even where the height was left to the survey. The form sends only what
was changed, so saving a name never turns a measurement into an entry.
`building:levels` stays the fallback at import, now labelled as one.

### 2. which-way-the-ridge-runs

The ridge direction comes from the survey: the highest edge of the roof for a
gable or a hip, the fall of its faces for a pent. It is stored per building on
the garden's own axes, and `roofshape` orients the pitches by it instead of by
the long axis — and a pent roof whose fall is known is pitched at last, rather
than left flat. The page says which way the ridge runs, the pitch that gives,
and whether both were measured or assumed.

## Scope, decided 2026-09-18

The first draft of this wave (2026-09-07) listed five items. They became the
two features above, except:

- **The other eleven Bundesländer moved to Wave 25**, feature 3
  (every-roof-in-the-country), which already calls itself the rest of this
  wave. Plan 04 did the research on 2026-09-07; what is left is building
  adapters, and that is Wave 25's subject.
- **A roof as a shadow caster stays in Wave 26** (feature 5,
  a-roof-casts-as-a-roof). This wave supplies its inputs; the shadow a house
  throws on the garden is still the `RISE_KEPT` prism.

## Open Research

(none)

## Deliberately not in it

- A general 3D building model. The roof is a surface for the sun to land on, not
  a thing to render.
- Solar-yield figures. The model reports **hours of direct sun**, not energy,
  and a roof that reads 11 h is not a kWh claim. Turning this into a solar
  calculator would need irradiance, angle of incidence and a weather series —
  a different project, and one where being approximately right is not good
  enough.
