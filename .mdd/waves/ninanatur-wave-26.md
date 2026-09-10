---
id: ninanatur-wave-26
title: "Wave 26: Light, not hours"
initiative: ninanatur
initiative_version: 23
status: planned
depends_on: ninanatur-wave-25
demo_state: "Ein Beet im Winkel eines L-Hauses bekommt seine vier Stunden Sonne statt keiner. Ein offenes Nordbeet zeigt, dass es sechzig Prozent des Himmels sieht und deshalb Halbschatten ist, nicht Schatten — die Stufe folgt Ellenbergs Definition der relativen Beleuchtung, die Bewölkung kommt aus der Klimatologie des Orts, nicht aus einer Annahme. Und wer die Schattenkante seines Hauses im Plan markiert, sieht, wie weit das Modell danebenliegt."
created: 2026-09-07
hash: c4cc662f
---

# Wave 26: Light, not hours

## Demo-State

Ein Beet im Winkel eines L-Hauses bekommt seine vier Stunden Sonne statt
keiner. Ein offenes Nordbeet zeigt, dass es sechzig Prozent des Himmels sieht
und deshalb Halbschatten ist, nicht Schatten — die Stufe folgt Ellenbergs
Definition der relativen Beleuchtung, die Bewölkung kommt aus der Klimatologie
des Orts, nicht aus einer Annahme. Und wer die Schattenkante seines Hauses im
Plan markiert, sieht, wie weit das Modell danebenliegt.

*(This wave is not complete until this can be manually demonstrated.)*

Detailed plan, in German, with the measurements and the climatology sources:
`.mdd/plans/03-sonne-und-schatten-genauer.md`.

## Why this is a wave

The light model is geometrically careful and honest about its assumptions, and
nineteen waves have refined it. It has never been checked against anything but
itself, and it measures the wrong quantity. Two errors were **measured** on
2026-09-07 rather than suspected:

| Error | Measured |
|---|---|
| Convex hull of the swept footprint | a point in the notch of an L-shaped house: **0.00 h** under the hull, **3.98 h** exact (two rectangles); a second point 0.00 h against 2.82 h |
| Sampling every 10th day, every 30 min | systematically ~2 % low: 10.84 h → 11.06 h at 5 min / 1 day; the docstring's "fine enough that the answer stops moving" is not true, and no convergence test exists |
| Sun below 5° discarded | 0.71 h/day of the season's 13.3 h potential lies between 2° and 5° |

And the conceptual one: the model counts **hours of direct sun**. A plant
experiences **illumination** — direct plus diffuse. PVGIS for Wuppertal
(SARAH-3, 2015–2020): the diffuse fraction is 0.48–0.52 from April to
September, 0.54 in March, 0.61 in October — **half the light of the growing
season is diffuse**, and the model has no term for it. An open north bed (sky
view ~90 %) and a spot under a dense crown with a noon gap (sky view ~20 %)
both read "2 h" today.

It is also the definition the model claims to serve. Ellenberg's L is defined
on **relative illuminance** — L9 rarely below 50 % of open-field light, L8
rarely below 40 %, L7 down to ~30 %, L6 rarely below 20 %, L5 mostly above
10 %, L3 mostly below 5 %, L1 below 1 % — and classically it is *measured under
an overcast sky*, i.e. from diffuse light. `SUN_HOUR_BANDS` replaces that
definition with a convention out of hours; its own comment says so. With a sky
term the number becomes a derivation from the definition.

## What is already there, and stays

- NOAA sun position with tested conventions; the 2D projection agrees with a
  3D ray (`test_shading_is_ray_tracing.py`); raised beds; north and south roof
  pitches distinguished (10.2 h against 11.7 h, Wave 21's measurement).
- Terrain under every cell and obstacle, the per-cell slope ring, the 5 km
  horizon ring, deciduous crowns by month, the stale signature.
- The order *user > survey > measurement > assumption*, stated everywhere.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | the-measuring-instrument | — | planned | — |
| 1 | no-hull | — | planned | 0 |
| 2 | room-to-compute | — | planned | 0 |
| 3 | the-sky-counts | — | planned | 2 |
| 4 | energy-not-hours | — | planned | 3 |
| 5 | a-roof-casts-as-a-roof | — | planned | 1 |
| 6 | a-crown-is-not-a-cylinder | — | planned | 1 |
| 7 | mark-the-shadow-edge | — | planned | 3 |

Three stages:

- **Stage 1 — measure first, then the largest error:** 0, 1, 2.
- **Stage 2 — the right quantity:** 3, 4. This is the demo-state's second
  sentence and the bulk of the value.
- **Stage 3 — the shapes, and the world:** 5, 6, 7.

Every model change bumps a `MODEL_VERSION` that enters `signature_of`, so a
stored grid computed by an older model shows `stale` rather than an old answer
with a new date. The page says which model version computed a map.

## What each one is

### 0. the-measuring-instrument

Nothing in this wave is "more accurate" until something can say so. Three
instruments, built before the model is touched:

1. **Sun position against a reference.** `pvlib` (BSD) as a *dev* extra; a test
   over 200 random moments and places in Germany, altitude and azimuth within
   0.5°. Catches convention errors the plausibility tests cannot.
2. **Geometry against a ray.** Extend the ray-tracing agreement test to random
   *concave* footprints, roof planes and ellipsoids; the L-house from the table
   above as a fixed regression case (0 h → ≈ 4 h).
3. **A convergence suite.** Halve the day and minute steps; a bed's value may
   move by less than 0.2 h. Runs with every later model change.

### 1. no-hull

`shadow_polygon` takes the convex hull. It goes. A point is shaded when the ray
towards the sun meets a **wall** of the prism (segment–ray intersection in 2D,
height compared in 3D) — exact for any polygon, concave included, and the basis
feature 5 needs anyway. The LoD2 path, which already emits building parts
separately, is unaffected. The bounding-box prefilter stays.

### 2. room-to-compute

The field is pure Python per moment × obstacle × cell, and the 5 s budget forces
3 m cells at forty houses. Features 3–6 add rays, 145 sky directions and three
times the moments. Rasterise each moment's shadow masks as numpy boolean arrays
on the grid (bbox slices, vectorised point-in-polygon), accumulate transmission
multiplicatively, batch the ray tests per moment; run the whole grid in the
process pool Wave 20 introduces so it never holds the request thread. Then the
sampling moves to **10 min / 5 days** and the cutoff to **3°** — the +2 % and
the 0.7 h that were thrown away, within the same budget.

### 3. the-sky-counts

Per cell a **sky-view factor**: the hemisphere sampled in 145 Tregenza patches
(or 36 azimuths × 8 altitude bands), each direction tested with the same
occlusion machinery as a sun sample — obstacles, slope ring, horizon ring —
weighted for a **CIE overcast sky** (zenith brighter than the horizon, which is
where obstacles block). 145 directions against ~1 200 sun moments: cheaper than
the season grid.

Then the climatology, which answers the owner's question *how is cloud
handled*: **not a three-year average** — interannual sunshine varies ±10–20 %
and three years are noise — but a climatology per location:

| Source | Gives | Licence |
|---|---|---|
| **PVGIS `MRcalc`** (JRC) | monthly global, direct-normal and diffuse fraction per coordinate, SARAH-3 satellite + ERA5, 2005 onwards; one GET per garden, no registration, 30 calls/s per IP, server-side only; **`usehorizon=0`** — PVGIS folds its own DEM horizon in otherwise, and this model has its own | "free and there are no restrictions on its use" |
| **DWD Climate Data Center** | 1 km grids: global radiation multi-annual **1991–2020** (a 705 KB zip that can ship in the image), sunshine duration multi-annual, diffuse radiation monthly from 2015 | **CC BY 4.0** (`Terms_of_use.txt`) |

Both verified on 2026-09-07. PVGIS is primary (per point, direct/diffuse split
ready), fetched once per garden and cached on the volume like the terrain
window; DWD is the cross-check and the offline fallback. The registry pattern
of Wave 17 applies: source, licence, attribution stored with the numbers.

The light of a cell and month:

    light = D(month) · f_direct(cell, month) + Hd(month) · SVF(cell)

with `D = H(h)·(1 − Kd)` and `Hd = H(h)·Kd` from the climatology, `f_direct`
the geometry's share of clear-sky beam (feature 4 adds the incidence
weighting). **Relative illuminance** `r.B. = light(cell) / light(open field)`;
Ellenberg L from the thresholds above. Cloud does not cancel in the ratio — its
effect is the **mix**: in Kiel the sky share weighs more and lost sun hours
less than in Freiburg, which is physically right and impossible with hours alone.

On the page: sun hours stay the headline (the number on a plant label), beside
it *sieht 62 % des Himmels* and the derived L; and **"erwartbare
Sonnenstunden"** — geometric hours × climatological sunshine / astronomically
possible — the number a gardener understands: 7.5 in June rather than 15.

### 4. energy-not-hours

Docs 71 and 72 name it: an hour of March sun at 8° counts like a June hour at
60°, and a north slope "gains" hours by seeing over obstacles while receiving
less energy. Each lit sample is weighted with a **clear-sky beam irradiance
× cos(incidence on the cell's own plane)** — a simple altitude-only model
(Haurwitz / Kasten-Czeplak), no data, no dependency — reported **relative** to
the open field, so still no kWh claim (Wave 21's line holds). Slope and aspect
become scorable; the morning/afternoon split gains meaning (afternoon is hotter).

### 5. a-roof-casts-as-a-roof

`RISE_KEPT` (gable 0.5, hip 0.4, pent 0.6, mix 0.8) is a shape guess, and a
gable's shadow is full ridge height along the ridge and eaves height across it —
a mean is wrong both ways. The roof surfaces exist (`roofshape.surface_of`) and
are asked only for cells *on* the roof; now shadows are cast by ray against the
real planes — two pitches plus gable triangles plus walls. `RISE_KEPT` is
retired for gable, hip and pent; `mix` and `other` stay prisms. Wave 21 (eaves,
ridge direction from LoD2) and Wave 25 (LoD2 everywhere) supply the inputs.

### 6. a-crown-is-not-a-cylinder

A cylinder from the ground to the top shades its whole footprint at every sun
angle, so the spot under a crown — where shade beds are planned — keeps only the
transmission. A crown becomes an **ellipsoid** on a trunk (centre at
height − r_v, semi-axes r_h, r_v); the ray–ellipsoid intersection gives the path
length L and `T = exp(−k·L)`, k calibrated so a full-diameter path reproduces
today's 0.20 / 0.08 / 0.75 — nothing gets worse where the old numbers held.
The **crown base** comes from Wave 25's point clouds where they exist, else a
default of a third of the height, editable per element like the crown width
already is.

### 7. mark-the-shadow-edge

The instrument that reaches reality. The gardener marks on the plan where the
shadow edge of their house falls *now* (date and time); the model draws its
prediction beside it and states the offset. Cheap, honest, and it catches the
three errors no test can see: a wrong height, a wrong north, a wrong anchor.
Once, in the feature doc: a synthetic case compared against an independent
tool (a sun study in Blender), documented rather than automated.

## What the model will still not know

- Reflected light (bright walls), penumbra, the daily course of cloud (valley
  fog, afternoon cumulus), microclimate, single years. A 1 km monthly
  climatology is the right grain for *what can grow here*; forecasting is a
  different product.
- Leaf-out is 1 May for every deciduous tree; late April in reality, varying by
  species and year. DWD phenology could refine it; not in this wave.
- Near-field terrain still does not shade unless something stands on it (doc
  71). Ray-marching the DGM1 window where the slope exceeds 5° is the fix and
  is deferred.

## Open Research

- Isotropic versus CIE-overcast sky weighting for the SVF — check both against
  the Ellenberg thresholds on a set of reference gardens.
- Which number leads on the page: hours, expected hours, or relative
  illuminance. Recommended: hours large, sky share and L beside.
- Whether the climatology window should be 1991–2020 (WMO) or the satellite
  era (PVGIS, 2005 onwards; PVGIS 6 beta reaches 2014–2024). Recommended:
  PVGIS's full range, DWD 1991–2020 as the check.

## Deliberately not in this wave

- A solar-yield calculator. Relative energy is a weighting, not a kWh.
- Weather forecasts or per-year light.
- Changing what the suggestions rank on beyond feeding them the new L — the fit
  model is untouched.
