---
id: 118-the-sky-counts
title: The Sky Counts — Sky View, Relative Illuminance and the Sunshine to Expect
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-26
wave_status: active
depends_on: [117-room-to-compute, 64-light-across-the-bed, 106-which-source-said-so]
relates: [07-solar-geometry, 38-polygon-shadows, 65-the-shade-switch, 70-the-horizon-ring]
source_files:
  - ninanatur/solar/sky.py
  - ninanatur/solar/climate.py
  - ninanatur/solar/relative.py
  - ninanatur/solar/raster.py
  - ninanatur/solar/raster_grid.py
  - ninanatur/solar/light.py
  - ninanatur/geo/gauss_kruger.py
  - ninanatur/data/climate_de.json.gz
  - scripts/dwd_climate.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/garden/lightgrid_model.py
  - ninanatur/garden/lightgrid_store.py
  - ninanatur/garden/lighting.py
  - ninanatur/garden/credits.py
  - ninanatur/garden/elements.py
  - ninanatur/garden/models.py
  - ninanatur/ingest/schema_computed.py
  - ninanatur/ingest/schema_user.py
  - ninanatur/ingest/migrations.py
  - ninanatur/api/light.py
  - ninanatur/api/schemas_light.py
  - ninanatur/api/schemas.py
  - ninanatur/api/gardens.py
  - frontend/src/components/BedPanel.tsx
  - frontend/src/components/SunMap.tsx
  - frontend/src/canvas/useSunReadout.ts
  - frontend/src/components/SourceCredits.tsx
  - ninanatur/garden/lightgrid_extent.py
  - NOTICE
  - pyproject.toml
routes:
  - GET /api/v1/gardens/{token}/light
  - POST /api/v1/gardens/{token}/light
  - GET /api/v1/gardens/{token}/sources
  - GET /api/v1/gardens/{token}
models: [light_grid, element]
test_files:
  - tests/test_sky.py
  - tests/test_climate.py
  - tests/test_relative.py
  - tests/test_sky_api.py
  - tests/test_credits.py
  - tests/test_light_model_version.py
  - tests/test_supply_chain.py
  - frontend/src/components/BedPanel.sky.test.tsx
  - frontend/src/components/SourceCredits.test.tsx
  - frontend/src/components/SunMap.test.tsx
  - frontend/src/components/GardenCanvas.test.tsx
data_flow: writes-existing
last_synced: 2026-09-22
status: in_progress
phase: all
mdd_version: 11
tags: [solar, light, sky-view, diffuse, climate, dwd, relative-illuminance, ellenberg, sunshine, cie-overcast, tregenza]
path: Garden/Light/Sky
integration_contracts:
  - from: 117-room-to-compute
    function: grid_sums / point_sums over any Directions (sun moments or sky patches)
    when: a new kind of direction is counted
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Relative illuminance is shown, not matched by: on Ellenberg's thresholds it would put almost every garden spot at L 9 (owner's decision, 2026-09-22, below)."
  - "The direct share is sun hours over open ground's, not energy: a March hour at 8° counts like a June hour at 60°. Feature 4 weights by incidence."
  - "Cloud is spread evenly over the day: the expected sunshine scales every hour by the month's share of possible sunshine. Morning fog in a valley or afternoon convection is not in a monthly climatology."
  - "Two skies, not twelve: a crown passes the in-leaf sky's light in every month it is in leaf and the bare sky's in every other."
  - "A sky patch is tested at its centre and counts wholly in or out: beside a long wall the isotropic sky seen is within 0.013 of the closed form on Reinhart's sky (0.031 on Tregenza's, which the season's bare months still use); near crowns and houses 0.003 on average, 0.019 at worst, against a sky of 20,624 patches."
  - "Beyond the DWD's grid a garden takes a neighbouring German cell within 30 km (and says how far), or the country's mean. A garden in Basel or Strasbourg is described by the German side of the border."
sister_projects: []
---

# 118 — The Sky Counts

## Why

The model counted hours of direct sun. A plant lives on light, and in a
German growing season half of it comes from the sky rather than the sun: the
DWD's diffuse fraction, 2015–2025, averages 0.46 in Freiburg and 0.50 in
Wuppertal over the months March to October. An open north bed and a spot under a
dense crown with a noon gap both read "4 h" and are not the same place — the
first sees two thirds of the sky, the second a fifth.

Ellenberg's light value is defined on exactly that: **relative illuminance**,
the light at a plant's place as a share of the light in the open. The hours
convention (`SUN_HOUR_ANCHORS`) stands in for it. This feature computes the
quantity the definition names, and says it on the page beside the hours.

## The sky a cell sees (`solar/sky.py`)

Tregenza's 145 patches are the standard subdivision for daylight: seven bands
12° high and a cap. Reinhart's 577 split each patch in four and are the finer
sky Radiance uses. Each patch is a direction like a sun moment, tested by the
same machinery (`raster_grid.grid_sums`, `raster.point_sums`): houses, crowns
with their transmission, the cell's slope ring, the horizon ring. Weighted for
the **CIE standard overcast sky** (Moon & Spencer, zenith three times as bright
as the horizon) times the cosine on level ground, the weights summing to one —
an open cell sees 1.

A patch is tested at its centre and counts wholly in or out. Against a sky of
20,624 patches, at garden spots near crowns and houses where the sky is at
least partly hidden, Tregenza's is off by 0.009 on average and 0.040 at worst,
Reinhart's by 0.003 and 0.019. Since a light value may be read from the sky
(below), **the sky a map shows is Reinhart's**; the season's bare-crown sky,
which only mixes into March, April and October, stays Tregenza's. Beside a long
wall seen at elevation β, where the isotropic answer is (1 + cos β) / 2, the
test sweeps β densely: within 0.013 on Reinhart's sky, 0.031 on Tregenza's.
(A first version claimed 0.025 for Tregenza, checked at three angles; it breaks
at 58° — review, 2026-09-22.)

A month's map shows that month's sky, bare crowns in March and April; the
season's map shows the sky in leaf. The first version showed the leafy sky
under a bare March crown while counting three quarters of the light through it.

Doc 117's raster was generalised for it: `Directions` (azimuth, altitude,
month, weight, group) replaces the sun's moments as what `grid_sums` sums, so
a sun sample and a sky patch are the same kind of thing. Hours are the sun's
directions weighted by the sampling step and grouped morning/afternoon.

## The climate (`solar/climate.py`, `scripts/dwd_climate.py`)

**Not PVGIS**, which the plan named first: re.jrc.ec.europa.eu's `robots.txt`
disallows every agent (checked 2026-09-22), and this project fetches nothing a
`robots.txt` refuses. The DWD was the plan's second source, and it is better
suited anyway: a climatology does not differ between two gardens in a village,
so it ships in the image and no garden waits on a request.

From the DWD Climate Data Center (`opendata.dwd.de`, no `robots.txt`,
**CC BY 4.0**), per month March–October, on its 1 km Gauss–Krüger grid
averaged to 10 km cells over whichever of their 1 km cells have values:

| Quantity | Grid | Period |
|---|---|---|
| Global radiation on level ground, kWh/m² | `radiation_global/multi_annual` | 1991–2020 |
| Diffuse fraction = Σ diffuse / Σ global | `radiation_diffuse/monthly`, `radiation_global/monthly` | 2015–2025 (the diffuse grids begin in 2015) |
| Sunshine duration, h | `sunshine_duration/multi_annual` | 1991–2020 |

The table is 120 KB (`ninanatur/data/climate_de.json.gz`, declared as package
data beside the catalogue). A garden is projected into the grid's coordinates
(`geo/gauss_kruger.py`: Krüger's series on the Bessel ellipsoid, meridian 9°,
false easting 3,500 km — tested against geokachel's UTM, the same series on
another ellipsoid). Then, in this order:

1. its own cell, if it has values — Helgoland's cell has three land squares
   in a hundred, and they are its climate (the first version required half,
   and gave the island the country's mean);
2. else the cell with values whose centre is nearest, within 30 km of the
   garden, measured, not counted in cells (the first version searched three
   cells either way and reached 49 km);
3. else Germany's mean, marked `assumed`. Outside 45–57° N, 3–17° E nothing is
   projected: at a pole or 90° from the meridian the series is undefined, and
   the first version answered `POST /light` with a 422 there.

The credit says which: *10 km, Monatsmittel*, *nächste Zelle, 14 km entfernt*
(Innsbruck), or *Mittel für Deutschland, angenommen* (Paris).

**Its credit** is the DWD's own wording for averaged values, "Datenbasis:
Deutscher Wetterdienst, Einzelwerte gemittelt" (dwd.de, *Vorlagen für
Quellenvermerke*), under `CC-BY-4.0`. `NOTICE` names the table, says it is
changed and how, and adds the DWD to the bodies this project is not affiliated
with.

## The mix (`solar/relative.py`)

Month by month, with the climate's global radiation H and diffuse fraction Kd:

    light(cell) = H·(1 − Kd) · direct share(cell) + H·Kd · sky share(cell)

where the direct share is the cell's sun hours over open ground's in that
month, and the sky share the sky-view factor with the crowns as they are that
month. Open ground has both shares 1 and gets H. **Relative illuminance** is
Σ light / Σ H over the months. Cloud does not cancel: it sets the mix. Where
the sky weighs more, lost sun costs less.

**The sunshine to expect**: each month's geometric hours times the share of
possible sunshine the DWD measured there (sunshine duration over the
astronomically possible hours), averaged over the calendar days. Open ground
in Wuppertal expects exactly the DWD's 1,340 h over 245 days: 5.5 h a day
against 13.1 geometric.

The grid computes everything in one pass (`grid_sky_light`); a bed narrower
than a cell, or raised, takes the point path (`point_sky_light`), which the
tests hold to the grid's answer at 1e-9, for the season and for a month in
leaf and a month bare.

## On the page

Hours stay the headline — the number on a plant label. Beside them, on a bed's
line and in the map's readout:

    4.0 h/Tag · erwartbar 1.8 h · sieht 60 % des Himmels · 47 % des Freilandlichts · L 6.3

A bed or a map computed before this model says only what it knows
(`4.0 h/Tag · L 6.3`): the new columns are nullable, the map's lists empty.

The DWD is credited whenever the garden has a map (`lightgrid_store.
shows_climate`): a month's map is computed on the spot and always has the
climate in it, even beside a season map stored before the sky counted. The
first version asked whether the stored map had a sky, and left the DWD
uncredited under its own numbers. Every credit now names its licence, linked
where its text is known (`credits.LICENCE_URLS`: CC BY 4.0, dl-de/by and zero,
ODbL), as CC BY 4.0 asks (§ 3(a)(1)(C)) — the page showed no licence before.

`MODEL_VERSION` is "26.3": the hours did not move, but a stored map without the
sky is out of date and the page offers the new one.

## Measured (the season, March–October)

A 20 × 30 m garden: its own 9 m house at the north end, an 8 m neighbour to the
east, a 1.8 m fence on the south boundary, a 10 m crown (transmission 0.2 in
leaf, 0.75 bare), a 2 m garden wall.

| Spot | Place | Hours | L (hours) | Sky | Relative | Expected |
|---|---|---|---|---|---|---|
| Open lawn | Wuppertal | 8.97 h | 9.00 | 0.80 | 0.75 | 3.75 h |
| 1 m north of the fence | Freiburg | 4.90 h | 6.81 | 0.66 | 0.54 | 2.38 h |
| | Wuppertal | 3.83 h | 6.11 | 0.66 | 0.50 | 1.69 h |
| | Kiel | 3.30 h | 5.66 | 0.66 | 0.47 | 1.64 h |
| Under the crown | Wuppertal | 3.99 h | 6.25 | 0.19 | 0.29 | 1.61 h |
| North of the house | Wuppertal | 5.71 h | 7.32 | 0.67 | 0.57 | 2.47 h |
| 1 m south of the house | Wuppertal | 10.12 h | 9.00 | 0.55 | 0.67 | 4.25 h |
| 1 m west of the wall | Wuppertal | 6.68 h | 8.01 | 0.61 | 0.56 | 2.79 h |

The fence bed and the crown read the same hours (3.8 and 4.0) and differ by
nearly half in light (0.50 against 0.29). That is the point of the feature.

**Cost**: 4,800 cells at 0.5 m, 3,846 sun moments, this garden with its
deciduous crown: hours alone 836 ms, hours and sky 996 ms — 577 directions in
leaf and 145 bare, +19 %. The cost estimate (`lightgrid_extent.estimate_ms`)
scales its part and cell terms by the directions swept, (3,846 + 577, + 145
with a deciduous crown) / 3,846, and the scale is in `grid_model`, so the
budget still picks the cell (the first version's estimate fell just below the
real cost at the budget's edge).

## The light value (owner's decision, 2026-09-22)

Ellenberg's thresholds, as the plan quotes them: L9 rarely below 50 % of
open-field light, L8 below 40 %, L7 down to ~30 %, L6 rarely below 20 %, L5
mostly above 10 %, L3 mostly below 5 %. Ellenberg measured forest floors, where
1–10 % is common; a garden rarely goes below 20 % outside a dense crown.

Measured on the real catalogue (8,939 candidates; Wuppertal, loam, fresh), top
20 herbaceous suggestions against today's:

| Spot | Hours | Today (hours) | On relative light | Lower of hours and sky |
|---|---|---|---|---|
| Open lawn | 8.8 h | 9.00 | 9.00 | 9.00 |
| West of a 2 m wall | 6.7 h | 8.01 | 9.00 — 7 of 20 left | 8.01 |
| North of the house | 5.0 h | 6.89 | 9.00 — 6 of 20 | 6.89 |
| 1 m north of the fence | 3.8 h | 6.11 | 9.00 — 1 of 20 | 6.11 |
| Under a crown (t 0.2) | 4.0 h | 6.24 | 7.41 — 12 of 20 | 6.11 — 18 of 20 |
| Under a dense beech (t 0.05) | 2.7 h | 5.18 | 6.12 — 9 of 20 | 2.48 — 2 of 20 |

Relative light on Ellenberg's thresholds gives every spot outside a crown the
open lawn's list. The hours alone read a dense beech as half shade, because
its bare months let the sun through. **The owner chose the third**: the light
value is the hours' convention, never brighter than Ellenberg's thresholds say
of the overcast sky in full leaf — which is how Ellenberg measured. It changes
nothing in the open, where that sky saturates at L 9 from a share of 0.42 up,
and under a dense beech it lists *Galium odoratum*, *Carex sylvatica* and
*Euphorbia amygdaloides* instead of meadow plants. Part 2 builds it; values
under crowns will move again with feature 6, which lifts crowns onto trunks.

## Business rules

1. An open cell sees the whole sky (1) and has the whole of open ground's
   light (relative 1); open ground expects exactly the DWD's sunshine.
2. The sky is tested by the machinery the sun is tested by: one occlusion
   model, not two.
3. Every climate value carries its source, licence and attribution; a
   borrowed cell says how far it is, and an assumed climate says so. The DWD
   is credited wherever its numbers can be shown.
4. Hours stay the headline. The light value is the hours', floored by the sky
   in leaf (part 2).

## Security

No new route and no new input. The climate is a file in the image, read once
(`lru_cache`); no request leaves the server for it, and a coordinate outside
the grid is never projected. The sky adds 577–722 directions to a computation
that `check_extent` bounds with them counted, run in the light worker's
process.
