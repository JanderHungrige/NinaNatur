---
id: ninanatur-wave-17
title: "Wave 17: The ground is not flat"
initiative: ninanatur
initiative_version: 20
status: planned
depends_on: ninanatur-wave-16
demo_state: "Ein Garten am Hang bekommt ein Höhenprofil aus öffentlichen Daten, und die Schattenkarte rechnet damit: ein Nachbarhaus bergauf verschattet mehr als eines auf gleicher Höhe, eines bergab weniger. Woher die Höhen stammen und wie genau sie sind, steht neben dem Ergebnis."
created: 2026-09-04
hash: cabd8fe9
---

# Wave 17: The ground is not flat

## Demo-State

Ein Garten am Hang bekommt ein Höhenprofil aus öffentlichen Daten, und die
Schattenkarte rechnet damit: ein Nachbarhaus bergauf verschattet mehr als eines
auf gleicher Höhe, eines bergab weniger. Woher die Höhen stammen und wie genau
sie sind, steht neben dem Ergebnis.

*(This wave is not complete until this can be manually demonstrated.)*

## Why this is a wave and not a detail

Every shadow in this project is computed on a plane at z = 0. There is no
terrain anywhere in the code — the word does not appear. A garden below a slope
gets an answer that is confidently wrong, and nothing on the page says so.

Wave 16 makes that visible for the first time: a shade map invites somebody to
trust it cell by cell, which a single number per bed never did. The moment the
map is believable, being silently flat becomes the largest error in it.

## What it is

The shading model needs one more number per point — the ground height — and one
per obstacle: the height of the ground it stands on. A building whose base is
three metres above the garden casts as though it were three metres taller.

That is a small change to `is_shaded` and a large change to where the data comes
from.

## Open Research — all of it, before anything is built

- **Which source.** Germany has statewide DGM (digital terrain models) at 1 m,
  several states publish them as open data, and the licences differ per state —
  the same problem the orthophotos already solved once, in `orthophotos.py`, and
  that solution is the pattern to follow. There is also the EU's Copernicus DEM
  at 30 m, one licence for the whole country and far coarser. Which is right may
  differ by state, and "no data here" has to remain an answer.
- **How much accuracy is enough.** A 30 m grid says nothing about a garden. A
  1 m DGM says a great deal and is a large download. The question is not which
  is better but which changes the answer: a slope of 1° over 50 m is 0.9 m and
  probably below the noise of an assumed building height.
- **Terrain versus surface.** DGM is the bare ground; DOM includes buildings and
  trees. Mixing them would count a house twice — once as terrain and once as an
  obstacle. This is the trap to write down before starting.
- **Where it is stored, and how big.** A per-garden height grid is user data on
  the volume, like Wave 16's light grid. A DGM tile is not, and must not end up
  in the image.

## Deliberately not in this wave

Slope and aspect as *growing conditions* — a south-facing bank is warmer and
drier than flat ground, and that belongs to the site model rather than the
shading one. Worth its own wave once the heights exist.
