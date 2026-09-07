---
id: 65-the-shade-switch
title: The Shade Switch, and a Day Watched Through
edition: MDD
initiative: ninanatur
depends_on: [64-light-across-the-bed]
relates: [64-light-across-the-bed, 67-sun-plant-in-a-shade-spot]
source_files:
  - frontend/src/components/ShadeSwitch.tsx
  - frontend/src/components/SunMap.tsx
  - frontend/src/components/CanvasScene.tsx
  - ninanatur/solar/day.py
  - ninanatur/api/light.py
routes:
  - GET /api/v1/gardens/{token}/light
  - GET /api/v1/gardens/{token}/shadows
models: [light_grid]
test_files:
  - frontend/src/components/ShadeSwitch.test.tsx
  - tests/test_light_api.py
data_flow: reads-existing
last_synced: 2026-09-07
status: complete
phase: all
mdd_version: 11
tags: [shading, ui, heatmap, animation, contrast]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# The Shade Switch, and a Day Watched Through

## The switch

One toggle over the plan, and two things it can draw. **Sonnenstunden** is the
heat map; **Tagesverlauf** is the same garden with the day's moving obstacle
shadows over it.

Two choices rather than two layers. The heat map and the day's shadows used to
be drawn together whenever the switch was on, and each made the other harder to
read: a shadow crossing a dark wash is not visible, and a wash read through a
shadow is not a reading. They answer different questions — *how much sun does
this corner get all summer* against *where is the shade at four o'clock* — so
they are separate answers now.

### One map, two inks

Sonnenstunden was itself two modes until 2026-09-07: a dark wash on the shade,
or a yellow wash on the sun, whichever direction the gardener wanted to ask
from. Each left half the garden blank, so reading the whole picture meant
switching back and forth and remembering the other half. Yellow for sun and grey
for shade says both at once, and there is nothing left to choose between.

The ink is chosen by `washFor`, on the **absolute** band edges below rather than
against the garden's own brightest cell:

| hours | ink |
|-------|-----|
| ≥ 4 h | yellow, full at 6 h |
| 2.5–4 h | none — the plan shows through |
| < 2.5 h | grey, full at 0 h |

Absolute because two inks make a stronger claim than one did. A single wash only
ever said *more than the rest of this garden*; yellow says **sunny**, and a
yellow that meant 3 h in one garden and 9 h in another would be saying something
untrue in one of them.

The relative scale existed for the shaded courtyard — a garden that never gets
more than four hours still has a bright end and a dark one. That case survives,
because the ramps are continuous rather than five steps: a courtyard between
0.5 h and 1.5 h still shows its brighter corner, in two strengths of grey
instead of grey against yellow. Which is the honest picture of a courtyard.

Halbschatten takes no ink. It is the hinge the two readings turn on, and
painting it either colour would pick a side that three hours of sun does not.

Tagesverlauf keeps only the yellow half. A grey wash under a grey shadow hides
the one thing on the plan that is supposed to be moving.

The legend is banded and every band carries its hours, because "Halbschatten" is
a word people use for different things and 2.5–4 h is not. Its swatches are
painted by running a sample hour from each band through the map's own `washFor`,
so a swatch cannot drift out of agreement with the cells it explains — and the
legend is the only thing that says what the two inks mean:

| Band | Hours | Swatch |
|------|-------|--------|
| volle Sonne | ab 6 h | yellow, full |
| sonnig | 4–6 h | yellow, half |
| Halbschatten | 2.5–4 h | none |
| Schatten | 1.5–2.5 h | grey, faint |
| tiefer Schatten | 0–1.5 h | grey, strong |

### The colour took three tries

The first wash was near-black, which measures 1.09 contrast against the dark
theme's `#12160f` — invisible. Two more candidates landed at 1.02 and 1.22. What
works is a *lighter* cool grey (`#5b6c80`, 2.36): on a dark page shade has to be
drawn with light, not with more dark.

## The day

`GET .../shadows?month=` returns the shadows of one middling day — the 15th, at
every half hour the sun is above 5°. The play button walks the plan through it.

Fetched only in Tagesverlauf mode. It used to be fetched whenever the switch was
on, which asked the server for a thing nobody had chosen to watch.

Computed rather than stored: one day is a fraction of a season's work, and
nobody watches the same day twice in a row.

Leaving Tagesverlauf stops the playback rather than handing it over. The play
button means two things depending on the mode, and one that silently starts
animating the *year* because the map mode changed is a control that did
something nobody asked for.

The 15th rather than the 1st or the 31st because a month's edges differ by a
fortnight of sun, and the middle is the one that represents the month.

## The button comes first

The rebuild button is the first thing in the panel, above the toggle, with one
line saying why: *nach dem Anlegen neuer Objekte den Schatten einmal neu
berechnen — das passiert nicht mehr von selbst.*

It is there because nothing recomputes the light on a write any longer (see
`64-light-across-the-bed`), which makes this button the only way to get a map at
all. It is rendered even when there is no map yet — the old panel showed
"nothing drawn yet" *instead of* the button, which was survivable while a write
built the first map and would now be a dead end.

## A thing that had to be learned twice

The map was fetched in `refresh` only — and a garden opened from its share link
never goes through `refresh`. That function already carried a comment warning
about exactly this, written after the last feature it happened to. The comment
now names its second victim.
