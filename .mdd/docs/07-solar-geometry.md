---
id: 07-solar-geometry
title: Solar Position, Shading and Bed Light
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-3
wave_status: complete
depends_on: []
relates: [08-garden-model, 09-garden-api]
source_files:
  - ninanatur/solar/__init__.py
  - ninanatur/solar/position.py
  - ninanatur/solar/shading.py
  - ninanatur/solar/light.py
routes: []
models: []
test_files:
  - tests/test_solar_position.py
  - tests/test_shading.py
  - tests/test_bed_light.py
  - tests/test_light_model_version.py
  - tests/test_light_legend.py
data_flow: greenfield
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [solar, shading, ellenberg, light, geometry]
path: Garden/Light
integration_contracts:
  - function: bed_light_value(location, bed, obstacles)
    when: deriving a bed's Ellenberg light value
    note: returns the value AND the sun hours behind it — a light value must always be traceable to the obstacles that produced it
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects:
  - /opt/3dmap2
---

# 07 — Solar Position, Shading and Bed Light

## Purpose

Derive a bed's light value from where the sun actually is, rather than from the
user picking "sunny" out of three buckets. Pure arithmetic — no dependency, no
network, no API key.

## Architecture

```
location + time  ->  position.py   ->  sun altitude, azimuth
sun + obstacles  ->  shading.py    ->  is this point in shadow?
sampled year     ->  light.py      ->  mean daily sun hours -> Ellenberg L
```

## Coordinate conventions

Stated once, because getting these wrong produces plausible, confidently wrong
numbers rather than an error:

- Garden coordinates are metres, `x` = east, `y` = north.
- Azimuth is degrees clockwise from north (0 = N, 90 = E, 180 = S, 270 = W).
- Altitude is degrees above the horizon; negative means below.
- Times are UTC. The garden's local time is irrelevant to the geometry.

## Verification anchors

The algorithm is checked against values derivable from physics rather than from
another implementation, so a shared error cannot pass:

| Anchor | Expected | Why |
|---|---|---|
| Equator, equinox, solar noon | altitude ≈ 90° | sun overhead at the equinox on the equator |
| Berlin (52.52°N), summer solstice noon | ≈ 60.9° | `90 − latitude + 23.44` |
| Berlin, winter solstice noon | ≈ 14.0° | `90 − latitude − 23.44` |
| Berlin, any solar noon | azimuth ≈ 180° | the sun is due south at local solar noon |
| Berlin, winter solstice midnight | altitude < 0 | sanity: the sun is down |

## Shading model

Obstacles are vertical cylinders: a position, a radius and a height. That is
enough for the walls, trees and sheds a garden actually has, and it keeps the
test for "is this point shaded" to a line-distance check.

```
shadow length L = height / tan(altitude)
shadow axis    = opposite the sun's azimuth
point shaded   <=> distance along axis in (0, L] and perpendicular distance <= radius
```

**A sun below `MIN_ALTITUDE` counts as no sun at all.** Near the horizon the light
is weak and in practice blocked by whatever is around the garden anyway; without
this floor, `1/tan(altitude)` also produces shadows kilometres long.

## Sun hours to Ellenberg L

The honest weak point of this feature, so it lives in one table with its
reasoning rather than inside a formula. Since 2026-09-21 on **EIVE's own 0–10 scale**, the scale every species value is
on, and as **straight lines between anchors** rather than steps
(`solar/light.py::SUN_HOUR_ANCHORS`):

| Mean daily direct sun (growing season) | L (EIVE 0–10) | Classic Ellenberg | The map's word |
|---|---|---|---|
| 0 h | 2.5 | 3 | tiefer Schatten |
| 1.5 h | 3.75 | 4 | Schatten |
| 2.5 h | 5.0 | 5 | Halbschatten |
| 4 h | 6.25 | 6 | sonnig |
| 6 h | 7.5 | 7 | volle Sonne |
| ≥ 8 h | 9.0 | between 8 and 9 | open ground |

Between two anchors the value is on the line (3 h → 5.42, 1 h → 3.33); beyond
the ends it is flat.

- **Why EIVE's scale.** The staircase before it had classic-looking rungs, 3–8,
  and was compared with EIVE values, which squeezed every bed towards the
  middle: full sun read as classic 7.4, deep shade as 3.4. EIVE scaled each
  source system linearly onto 0–10 (Dengler et al. 2023, Methods), which for
  Ellenberg's 1–9 is (L − 1) × 1.25. Each anchor is the old rung at its old
  threshold carried through that rescale — the scale and the steps changed,
  not the judgement.
- **Why lines.** 3.99 h and 4.01 h are the same place; a step made them a whole
  class apart, enough to drop a species from a list.
- **Why lower edges.** Anchored where the old steps began, each value leans a
  little bright of the middle of its old interval — on purpose, because the
  model counts direct sun only and a bed in the open with a wall to its south
  still sees most of the sky.
- **Why 9.0 from 8 h.** That long in direct sun is open ground; the hours past
  eight are low sun at the ends of the day. EIVE's 9.5–10 is dunes and scree.
- **Why not below 2.5.** Classic 1–2 is a closed forest floor; a bed with no
  direct sun still has the sky.

`LIGHT_MODEL` names the convention, and the light map's signature carries it:
a new convention makes every stored map, and every bed list ranked by its
values, read stale once (doc 13). A bed's value comes from its hours as stored,
so the two always agree.

Sun hours are physical; an indicator value is ecological, read from where
plants are found growing. **This conversion is a convention, not a
measurement.** It is a table so that it can be argued with and adjusted in one
place, and so that nobody mistakes it for physics.

The growing season is March to October — a plant's light experience in December
does not decide where it can live.

## Business Rules

- **Every light value carries the sun hours it came from.** A bare number the
  user cannot trace back to their own obstacles is not explainable, and this one
  will surprise people.
- **Location is rounded to four decimal places before use and storage** (~7 m).
  A garden's exact coordinates are personal data, and the fifth place buys
  nothing a 1 m terrain grid can see.

  It was 0.1° (~11 km) until 2026-09-07, which is genuinely invisible to solar
  angles — the reasoning was sound for what the coordinates were then for. Wave
  17 gave them a second job: a 100 m terrain window, a 5 km horizon ring and a
  1 km² building tile are all fetched from this anchor, and 6.6 km of error puts
  every one of them on a different hillside. At Wuppertal the rounded point
  reads 268 m where the garden's ground is 147.

  Gardens created before the change cannot be recovered — the precision is gone,
  not hidden. `garden.terrain_sync.is_precise` recognises them by their sitting
  exactly on the old 0.1° grid in both axes, and leaves them on flat ground
  rather than serving somebody else's hill.
- **Computation happens on save, not per request.** Sampling a season for several
  beds is far too slow to repeat on every page load.

## Security

Pure computation. No I/O, no external calls, no untrusted input beyond numbers
that are range-checked by the caller.

## Known Issues

- Sun hours are astronomical, not meteorological: they count when the sun is
  geometrically above the horizon and unobstructed, with no allowance for cloud.
  An open Berlin bed computes 12.6 h/day averaged over the season, which is real
  daylight rather than usable garden sun. Fine for *comparing* beds, which is all
  the Ellenberg mapping needs — but the number should never be shown as "hours of
  sunshine" without that caveat.
- Beds are evaluated at a single point. A long bed running north-south past a
  wall is partly shaded in reality and uniformly scored here. Sampling several
  points per polygon is the obvious upgrade once beds have real geometry.
- Obstacles are opaque. A deciduous tree shades far less in March than in July,
  and modelling that needs a leaf-on/leaf-off season per obstacle.

## Bugs

(none yet)
