---
id: 119-energy-not-hours
title: Energy, Not Hours — the Sun's Share Weighted by What It Brings
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-26
wave_status: active
depends_on: [118-the-sky-counts, 117-room-to-compute, 72-the-hill-that-eats-the-morning]
relates: [71-buildings-stand-on-the-ground, 70-the-horizon-ring, 07-solar-geometry]
source_files:
  - ninanatur/solar/beam.py
  - ninanatur/solar/raster.py
  - ninanatur/solar/raster_grid.py
  - ninanatur/solar/relative.py
  - ninanatur/solar/light.py
  - ninanatur/garden/lightcells.py
  - ninanatur/garden/lighting.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/garden/lightgrid_extent.py
  - ninanatur/api/schemas.py
routes:
  - GET /api/v1/gardens/{token}/light
  - POST /api/v1/gardens/{token}/light
models: [light_grid, element]
test_files:
  - tests/test_energy.py
  - tests/test_light_model_version.py
  - tests/test_relative.py
  - tests/test_light_grid_cost.py
  - tests/test_bed_light_fallback.py
data_flow: writes-existing
last_synced: 2026-09-22
status: complete
phase: all
mdd_version: 11
tags: [solar, light, energy, irradiance, incidence, slope, aspect, relative-illuminance, clear-sky]
path: Garden/Light/Energy
integration_contracts:
  - from: 118-the-sky-counts
    function: relative illuminance — direct share × H(1 − Kd) + sky share × H·Kd, month by month
    when: the direct share changes from hours to energy
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The sky's share is not weighted by incidence: a tilted cell sees its own sky through its own ring (doc 72), but each patch still counts by the cosine on level ground. Under an overcast sky, where the light is nearly even, that is the smaller error; a tilted-plane view factor is the fix."
  - "Cloud is taken as evenly spread over the day, as in doc 118: the month's beam has the clear-sky shape, scaled by the climate's direct radiation. Morning fog in a valley is not in a monthly climatology."
  - "The morning and afternoon halves are still hours, not energy, so the page's morning share does not yet say that the afternoon is the warmer half."
  - "Relative illuminance above 1 is real and shown as more than 100 % of open-field light; nothing in the page or the fit model treats it specially."
sister_projects: []
---

# 119 — Energy, Not Hours

## Why

Docs 71 and 72 name it. An hour of March sun at 8° counts in the model like a
June hour at 60°, though it brings a fraction of the light to level ground.
And a north slope "gains" hours by seeing over what stands below it, while
every one of them strikes it at a glancing angle. Relative illuminance (doc
118) took the sun's share of a month as hours over open ground's hours, so
both errors went into the number the page gives as "% des Freilandlichts".

This feature weights each lit moment by what it brings: the clear-sky beam at
that altitude, times the cosine of its incidence on the cell's own surface.

**What does not change.** The hours stay the headline, and hours they are.
The light value stays the hours' convention floored by the sky (the owner's
decision of 2026-09-22, doc 118). The sunshine to expect stays hours. This is
a weighting inside relative illuminance, reported relative to open level
ground: no kWh is claimed, and Wave 21's line — this is not a solar-yield
calculator — holds.

## The beam (`solar/beam.py`)

Altitude only, no data, no dependency:

    air mass       m(h) = 1 / (sin h + 0.50572 · (h + 6.07995°)^−1.6364)   (Kasten & Young 1989)
    beam, normal   B(h) = 0.7 ^ (m^0.678)                                   (Meinel & Meinel 1976)

relative to what arrives above the atmosphere — the constant cancels in every
ratio this feature takes. The plan named Haurwitz; it models global radiation
on level ground, not the beam, and the beam is what a shadow takes away.

## Incidence on the cell's own surface

A cell stands on the ground or on a roof, and both have a slope s and an
aspect a — measured uphill, clockwise from north, as every aspect in this
project is (`slopes.slope_at`, `roofshape.slope_aspect_at`). The surface
faces downhill, so for the sun at altitude h and azimuth A

    cos i = sin h · cos s − cos h · sin s · cos(A − a)

and a moment counts B(h) · max(cos i, 0). On level ground that is B(h) · sin h.
The sun behind the surface is already hidden by the cell's own ring (doc 72);
the clamp is its closed form.

`lightcells.Surface` carries slope and aspect; `raster_grid.Cells` carries each
cell's surface as three coefficients (cos s, −sin s cos a, −sin s sin a), None
where every cell is level — the common garden, and a fast path.

**A raised bed is a box.** Its soil lies level however the ground falls under
it, so the point path gives it `LEVEL` while keeping the hillside's ring: the
slope still stands between it and the low sun. It inherited the hillside's
tilt at first, and a 0.8 m bed on a 22° north slope read 17 % too dark
(review, 2026-09-22).

## One sweep, two sums

The occlusion is the cost (doc 117). `raster_grid.grid_sweep` asks it once per
moment and adds what passes twice: to the hours, as before, and weighted by
the moment's beam on each cell's surface, to that month's energy
(`raster.Incidence`). `raster.point_sweep` does the same for a point.

## The share, and the mix

Month by month, the sun's share becomes

    direct share = Σ lit B(h) · max(cos i, 0) / Σ open B(h) · sin h

the second sum over every moment the sun stands above `MIN_ALTITUDE`,
unobstructed, on level ground. It can exceed 1: a south slope takes more of
the beam than level ground does. The mix is doc 118's, unchanged:
H·(1 − Kd) · direct share + H·Kd · sky share. Relative illuminance above
100 % on a south slope is what the page then says, and is true.

## What moved (the season, Wuppertal, doc 118's garden)

| Spot | Hours | Relative, by hours | by energy |
|---|---|---|---|
| Open lawn | 8.97 h | 0.75 | **0.79** |
| 1 m south of the house | 10.12 h | 0.67 | **0.74** |
| 1 m west of a 2 m wall | 6.68 h | 0.56 | **0.63** |
| 1 m north of the fence | 3.83 h | 0.50 | **0.47** |
| North of the house | 5.71 h | 0.57 | **0.45** |
| Under the crown | 3.99 h | 0.29 | **0.30** |

What rises loses only the low sun at the ends of the day — a neighbour's
house to the east, a fence 1.8 m high. What falls loses the middle of the
day: the strip north of a 9 m house keeps its hours and loses a fifth of its
light. The model's three pinned answers move the same way: open ground 1.00,
behind a house 0.569 → 0.454, the corner of the L 0.451 → 0.404.

And the slope itself, through `compute_grid` on a hillside of 0.4 m a metre
(22°) in Wuppertal, a bed 10 m square:

| | Hours | Sky | Relative |
|---|---|---|---|
| Level | 13.08 h | 1.00 | 1.000 |
| Facing south | 12.44 h | 0.98 | **1.071** |
| Facing north | 12.79 h | 0.98 | **0.834** |

The north face has *more hours than the south face* — doc 72's complaint,
exactly: at 51° N the June sun rises and sets north of east and west, and a
south-facing slope's own ground stands in front of it then. By hours the
north face is the brighter bed. By what the sun brings it is a sixth darker
than level ground, and a fifth darker than the south face.

A roof's two pitches part the same way, and this is the other half of a cell's
surface: on a 39° gable at Wuppertal the south pitch reads 1.05 of open level
ground's light and the north pitch 0.66.

**Cost**: 4,800 cells at 0.5 m, 3,846 moments. Hours alone 811 ms; with the
sky 981 ms as before, since level cells take the beam by one number a moment;
with every cell tilted 1,069 ms. The extra is a cost *per cell* — 0.018 ms
measured at 4,800 cells and again at 48,841 — and `estimate_ms` prices it as
one (`TILTED_CELL_MS`), on the condition that actually turns it on: terrain,
**or** a pitched roof, which tilts cells in a garden nobody surveyed. Charged
as a tenth on top of the whole raster instead, it under-priced a large grid
by 800 ms and over-priced a crowded small one (review, 2026-09-22).

## Business rules

1. Hours, the light value and the sunshine to expect are untouched.
2. Open level ground has a direct share of 1, whatever the month.
3. A lost low sun costs less than a lost high one; a surface tilted towards
   the sun gains, one tilted away loses.
4. Every change to what the model answers raises `MODEL_VERSION`.

## Security

No new route, input or dependency. The sweep adds a multiply per moment and
cell to a computation bounded by `check_extent` and run in the light worker.
