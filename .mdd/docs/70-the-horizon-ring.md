---
id: 70-the-horizon-ring
title: The Horizon Ring
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-17
wave_status: active
depends_on: [68-which-ground-and-whose, 69-a-window-of-ground]
relates: [69-a-window-of-ground, 64-light-across-the-bed]
source_files:
  - ninanatur/geo/horizon.py
  - ninanatur/geo/terrain_store.py
  - ninanatur/ingest/schema_user.py
routes: []
models: [terrain_horizon]
test_files:
  - tests/test_horizon.py
data_flow: mixed
last_synced: 2026-09-05
status: complete
phase: all
mdd_version: 11
tags: [terrain, horizon, solar, azimuth, wcs, scalefactor]
path: Map/Terrain
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Measured from the bare-earth model, so a forest edge is invisible to it although it genuinely blocks the low sun."
  - "Earth curvature is ignored: 1.7 m of drop over 5 km with refraction, 0.019°."
---

# The Horizon Ring

Feature 2 of Wave 17. A garden in a valley loses the winter sun to the hillside
long before the sun sets, and no amount of detail about its own 200 m of ground
will say so.

## Five kilometres in, 2 KB out

One request per location: a 10 km box, downscaled by the service itself, walked
into **360 numbers** — for each degree of azimuth, the highest angle above the
horizontal the land reaches. The raster is measured and thrown away.

**Every one of the six services accepts `SCALEFACTOR`**, and it is faster than
`SCALESIZE` where both work — Niedersachsen 21.6 s against 7.3 s, Brandenburg
7.7 against 3.0. Baden-Württemberg accepts only `SCALEFACTOR` and returns 404
for `SCALESIZE`, so the uniform choice is also the only one that covers all six.
Without either, the same box at 1 m would be 400 MB.

Stored rings run about 2.1 KB.

## It does nothing in flat country, on purpose

Measured against the live services:

| Place | Highest | Where | South sector |
|---|---|---|---|
| Potsdam | 4.80° | 182° | 4.80° |
| Winterberg, Sauerland | 5.12° | 222° | 5.12° |
| **Wolfach, Schwarzwald** | **12.54°** | 135° | **12.54°** |
| Eschwege, Werratal | 6.63° | 271° | 4.38° |

Midwinter noon at 51°N is 15.5°. Potsdam's 4.80° is below the light model's own
`MIN_ALTITUDE = 5°` and changes nothing at all. Wolfach's 12.54° to the south
means the sun barely clears the ridge at noon in December — which is the whole
reason for the feature, and a thing no garden-sized model could ever have said.

A test asserts the flat case explicitly, because a feature that appears to do
nothing is otherwise indistinguishable from a broken one.

## Azimuths are true north, and that is not free

Rays are walked in the **garden's** frame, not the raster's, using the same
measured affine map the window resampling uses. Grid north is 2.33° off true
north at 6°E, and a ring built on grid azimuths would be turned by two of its own
one-degree bins against the sun positions it is compared with.

The test puts a compact hill four kilometres due south *in the garden's frame*
and requires it back at azimuth 180 exactly. Replacing the frame map with the
identity — grid north — moves it to 182, and the test says so.

Four kilometres out because a three-cell hill spans less than a degree there.
The first version of this test used a ridge one kilometre away, which produced a
plateau from 166° to 185°, and `max` picked its first entry. The code was right;
the test's idea of a peak was not.

## What it will not know

- **It is bare earth.** A forest edge 200 m to the south genuinely blocks the
  winter sun and is invisible here. Using a surface model instead would bring
  buildings with it, and buildings are already in the obstacle model — see the
  wave's Open Research for the rule that would be needed.
- **Curvature is ignored.** Over five kilometres the drop is about 1.7 m once
  refraction is allowed for, which is 0.019° — two orders of magnitude below a
  terrain model that states ± 0.3 m.
- **A negative horizon is clamped to zero.** Ground below the garden would mean
  the sun arriving from underneath, which is true of a clifftop and is not a
  question this model is asked.
