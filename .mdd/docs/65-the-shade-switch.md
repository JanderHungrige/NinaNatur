---
id: 65-the-shade-switch
title: The Shade Switch, and a Day Watched Through
edition: MDD
initiative: ninanatur
depends_on: [64-light-across-the-bed]
relates: [64-light-across-the-bed, 67-sun-plant-in-a-shade-spot]
source_files:
  - frontend/src/components/ShadeSwitch.tsx
  - frontend/src/components/DayPlayer.tsx
  - frontend/src/components/PlanWorking.tsx
  - frontend/src/components/PlanArea.tsx
  - frontend/src/garden/useDay.ts
  - frontend/src/garden/useLight.ts
  - frontend/src/garden/useRebuild.ts
  - frontend/src/components/SunMap.tsx
  - ninanatur/api/schemas_light.py
  - frontend/src/components/CanvasScene.tsx
  - ninanatur/solar/day.py
  - ninanatur/api/light.py
  - ninanatur/api/relight_jobs.py
  - ninanatur/api/ratelimit.py
  - ninanatur/garden/relight.py
  - frontend/src/api/client.ts
routes:
  - GET /api/v1/gardens/{token}/light
  - POST /api/v1/gardens/{token}/light
  - GET /api/v1/gardens/{token}/light/status
  - GET /api/v1/gardens/{token}/shadows
models: [light_grid]
test_files:
  - frontend/src/components/ShadeSwitch.test.tsx
  - frontend/src/components/ShadeSwitch.waits.test.tsx
  - frontend/src/components/DayPlayer.test.tsx
  - frontend/src/App.waiting.test.tsx
  - tests/test_light_api.py
  - tests/test_relight_jobs.py
  - frontend/src/App.firstlight.test.tsx
  - frontend/src/garden/useRebuild.test.ts
  - frontend/src/api/client.test.ts
data_flow: reads-existing
last_synced: 2026-09-28
status: complete
phase: all
mdd_version: 11
tags: [shading, ui, heatmap, animation, contrast]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Fixed 2026-09-21: `ShadowFrame.minute`'s comment (now in `api/schemas_light.py`) called it local solar time; the server counts it from 00:00 UTC (`solar/day.py`), which is what the player reads and shows on a Europe/Berlin clock."
  - "The rebuild's words name its steps (Gelände, Gebäude, Laserdaten, Licht) without saying which one is running: the endpoint is one blocking request with no progress to report. Staged progress would need a job endpoint (decided against on 2026-09-21)."
  - "Revisited 2026-09-28: the first relight at a place ran past the preview proxy's 90 s, and the owner chose a job — `POST /light` answers 202 after 20 s and `GET /light/status` says when it is done. The status says running or not, still without the step: staged progress is still undone."
  - "`frontend/src/api/client.ts` was 636 lines before the relight job and is 655 after it; the length hook asks for a split of the client, which is not this feature's to make (as doc 114 recorded at 609)."
  - "The jobs live in the serving process: a restart while one runs — a deployment rolling the image — loses it. The status then says it knows none (`known`), and the page says the relight was interrupted, to be pressed again; the work already stored (ground, buildings, laser) makes the second press quick. One process serves the app; more would need the jobs in the database."
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

The ink is chosen by `washFor`, on **absolute** hour thresholds rather than
against the garden's own brightest cell.

### Ten steps, four of them above "volle Sonne"

The first version ramped from 4 h and reached full yellow at 6 — where the
plant-label convention stops caring. Measured on a real garden, **139 of its 165
answered cells were above 6 h**, so the map painted five sixths of the garden in
one flat colour. The honest reading of it was "it is sunny here", which the
gardener already knew.

A German garden's range, averaged March to October, runs to about 12.5 h. The
steps spread across that, so the thing the map is actually for — *which corner
is better than which* — is visible:

| hours | ink |
|-------|-----|
| ≥ 11 | yellow, full |
| 9–11 | yellow |
| 7.5–9 | yellow |
| 6–7.5 | yellow — *volle Sonne* begins |
| 5–6 | yellow |
| 4–5 | yellow, faintest — *sonnig* |
| 2.5–4 | none — the plan shows through — *Halbschatten* |
| 1.5–2.5 | grey — *Schatten* |
| 0.75–1.5 | grey |
| < 0.75 | grey, full — *tiefer Schatten* |

Steps rather than a continuous ramp: two hundred cells of smoothly varying
opacity read as mush, and the same cells in bands read as contours. On the
garden above the map now draws **seven** distinct strengths where it drew one.

The gardening names sit on the step where each band begins; the steps between
are increments of the same wash, not new names. A test asserts every name still
agrees with `bandFor`, whose bands begin at the server's `SUN_HOUR_ANCHORS`
(doc 07) — and since 2026-09-21 `tests/test_light_legend.py` holds the two
together, words included: until then the map called 6–8 h "volle Sonne" where
the server's table said "sunny", and nothing noticed.

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

### The roof is the surface, not the ground under it

A cell under a house or a shed is answered **on the roof** — at its own height
and its own pitch. It used to be answered on the ground beneath the building,
where the sun never reaches, all day, every day, and painted in the deep-shade
ink. True of that ground, and false of the picture: what a plan shows at a house
is the roof.

The pitch is folded into the sky exactly the way a hillside already is
(`slopes.ring_for`): a point on the north pitch has its own ridge standing
between it and the southern sun, so it loses the hours a north face should lose.
Measured on a 14 × 9 m house at 51°N with a 38° gable — **north 10.2 h against
south 11.7 h**, where a flat roof reads the same on both sides. A steeper pitch
costs the north face more, which is the mechanism rather than a coincidence of
one geometry.

Roof cells are flagged in the response and left out of two things: a bed's mean
and the garden's brightest point. Nothing is planted on a roof, and a sunny one
would otherwise set the scale for the garden below it. The readout says "Dach"
so a reader cannot take eleven hours on a roof for the bed underneath.

A tree is not roofed. There is real ground under it getting real dappled sun,
and somebody planting under an apple tree is asking about exactly that.

### One month, or the whole season

A dropdown beside the modes. The season average — March to October — is the
number a plant is placed by and the one the button computes and stores; a month
is a question asked while looking, and answered fresh from the same inputs.

While a month is computed, *Karte wird berechnet…* stands beside the dropdown —
outside its label, which would otherwise become part of the select's name — and
the map on the plan steps back to 40 % until the new one lands, because what it
shows meanwhile is the last period's answer. The dimming is a class on the plan's
cell in `PlanArea` (`workspace__plan--waiting .sun-map`), so the map itself knows
nothing of it. Two switches in a second send two requests; only the newest may
land or clear the note.

Measured on a garden with a house on its south side:

| | median | lowest cell |
|---|---|---|
| season | 10.6 h | 2.8 h |
| March | 7.3 h | 0.1 h |
| June | 14.8 h | 6.2 h |

One number for the season describes neither, and it is the March figure a
gardener needs before putting anything early-flowering in that corner.

Not stored: a month is sampled six times where the season is twenty-five, so it
costs about a quarter as much to answer on the spot. Storing all eight would
multiply the one slow operation in this app by eight, to answer a question most
gardens are never asked. A month view is therefore never stale, and says so; the
`misplaced` warnings stay on the stored season grid in every case, because
misplacement is a judgement about a growing season and warnings that appeared
and vanished while somebody scrolled the months would be noise.

### How fine the grid is

A time, not a cell count. It was a flat cap of 600 cells, set when every write
recomputed the light and half a second was the whole budget — and it left an
ordinary 24 × 33 m garden on 2 m cells, which is what "the raster is still
rather coarse" was about.

A count was the wrong shape anyway, because a cell is not a fixed price: it
costs what the obstacles around it cost. Measured, 0.24 ms in a garden with
three buildings and 1.9 ms in one with forty — which a single number has to be
wrong about at one end or the other. The budget is five seconds of the button
somebody pressed knowing it would take a moment, and the ladder picks the finest
cell that fits: **0.5 m** for an ordinary garden, 3 m for a 150 m street with
forty houses.

Half a metre is the floor and stays there. Below it the map would be saying more
than the model knows, given that most building heights are assumed and a roof
pitch is inferred from a rectangle.

### What is under the pointer

Hovering the plan reads out the cell: `8.4 h · sonnig`, or `Dach — kein Boden`
over a building. A wash cannot be read to one decimal place, and *Halbschatten*
is the word printed on the label the gardener is holding.

An HTML readout over the plan, driven by the surface's own pointer handler —
not a `<title>` on each cell. The map has `pointer-events: none`, which is what
lets a click reach the bed underneath; turning that on for a tooltip would make
the wash swallow every selection.

*Since the owner's check (2026-09-21, doc 113)* the map is drawn as one path per
wash rather than a rect per cell, the readout is its own component (a mouse move
re-renders the label and nothing else), and it is not read while a pan holds the
plan.

The coordinate is checked for being finite before it is used. An SVG that has
not been laid out measures zero and the viewport arithmetic returns NaN — and
NaN passes every bounds test, because every comparison against it is false. It
indexed the array with NaN, got undefined, and reported a roof over an open
lawn.

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
every half hour the sun is above 3° (5° until Wave 26). The day's player walks
the plan through it.
Each frame is every shadow at that moment as rings — outlines anticlockwise,
holes clockwise — drawn as one path under the non-zero rule (Wave 26, doc 116).
Until then it was one convex hull per obstacle, drawn one by one: an L-shaped
house's open corner was drawn shaded where the map counted sun, and two shadows
darkened where they overlapped. The route takes a heavy slot since then.

**The player stands in this panel, directly under the chips** (`DayPlayer`, since
2026-09-21). It used to be the dock's play button changing its meaning from
*Jahr abspielen* to *Tag abspielen* once the day had arrived — at the other end
of the page from the chip that asked for it, with nothing at all while the day
was computed, and silence when that failed. The owner asked for it beneath the
Tagesverlauf chip. The dock's player plays the year and nothing else now.

It has three parts: *▶ Tag abspielen* / *⏸ Anhalten*, a scrubber for any moment
by hand, and the clock time of the frame showing. Twelve seconds sunrise to dusk,
the pace the dock's button had. Under `prefers-reduced-motion` the scrubber is
the only control: a day that runs by itself is exactly the motion that setting
exists for, and the old button offered nothing at all there, so only dawn could
ever be seen.

The time is a **German clock's**: the server counts a frame's minutes from
midnight UTC, so 11:00 there is noon in March and one o'clock from April on. The
15th of the model's months never falls on a change of the clocks.

**The month is the panel's Zeitraum**, June for the whole season. It used to
follow the bloom filter, so playing the year in the dock refetched the day and
threw its frame back to dawn every half second.

While the day is computed the player says *Tagesverlauf wird berechnet…*; if it
fails it says *Tagesverlauf konnte nicht berechnet werden.*, offers *Noch einmal
versuchen*, and the toast says it too.

The play state lives in `useDay`, not in the button, so whatever hides the panel
can stop it. **Every change stops the playback and leaves it stopped**: leaving
Tagesverlauf, switching the map off, a new month (a new question, whose shadows
start from dawn), and selecting anything — which hides the garden's details and
the button with them. A timer running behind a control nobody can reach is not
playback, it is a leak.

Fetched only in Tagesverlauf mode. It used to be fetched whenever the switch was
on, which asked the server for a thing nobody had chosen to watch.

Computed rather than stored: one day is a fraction of a season's work, and
nobody watches the same day twice in a row.

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

### While it computes

The rebuild is the longest wait in the garden — terrain, buildings, the laser
points, then the light; 12.9 s measured for a garden of 87 elements — and the
plan used to sit perfectly still through it. Now, for as long as it runs
(`useLight`'s `rebuilding`):

- the button reads *Wird berechnet…* with a turning ring, here and in the first
  steps' *Schatten berechnen*;
- a band of sunlight sweeps across the plan, with a note in its middle:
  *Schatten wird berechnet — Gelände, Gebäude, Laserdaten, Licht…*
  (`PlanWorking`, rendered by `PlanArea` around the canvas, taking no pointer);
- the toast says *Schatten wird berechnet…* when it starts and *Schatten
  berechnet.* when it is done.

The words name the steps and never claim to know which one is running: the
request reports nothing until it is done. Under `prefers-reduced-motion` the
sweep is a still, faint wash and the ring stands still.

### A first analysis longer than a request

The owner's report of 2026-09-28: the first press ran a long time and ended
with nothing, and a second press began again. The first relight at a place
reads the ground, the building model and — in the seven states that publish
one — the laser before the light: 31 s on a workstation, past 90 s on the
preview, whose proxy then answered 504. The page took that for the end; the
server went on and stored the map nobody was waiting for. Wave 26 made every
garden meet it once, by reading each stored laser window again for the crown
bases (doc 121).

*Where the minutes went* (2026-09-29): run in the image, a garden in
Köln-Ehrenfeld logged *laser 385.4 s*, and 381 of those seconds were the test of
which points stand inside a building — every point against every edge of the
4,359 outlines the building model brought. Each outline now meets only the
points in its box, and that laser takes 3.2 s (doc 107). The job below stays:
a first analysis still fetches tens of megabytes, and a slow portal can still
outlast a request.

So a relight is a job (`api/relight_jobs.py`; the chain in
`garden/relight.py`, each run's steps timed in the log). Done within 20 s,
`POST /light` answers with the map as it always did; not, it answers **202**
and goes on, holding its heavy slot until it ends. The page then says *Erste
Analyse läuft – Gelände, Gebäude und Laserdaten werden geladen*, asks `GET
/light/status` every three seconds, and reads the season's map once the job
is done — or says it failed, and gives the button back; or that it was
interrupted, where a restart lost the job and the status knows none.

The review of the job (c2ec593) found where the first version of it hurt:

- **A press while the job runs is answered 202 at once**, and joins by asking
  the status. It waited for the running job at first, holding one of the
  server's forty threads for twenty seconds with no slot and no count: 45 such
  presses took a plain garden read from 2 ms to 4.5 s while `/healthz` stayed
  green. It is decided under a lock, before the visitor's allowance is
  counted, so two presses at once start one job and count once.
- **The slot is given back whatever ends the job**, a connection that will
  not open included; it was taken before the `try`, and two such failures
  answered every heavy route with 429 until a restart.
- **Jobs are kept by share token.** SQLite gives a deleted garden's id to the
  next one, and a new garden joined the job of the one deleted before it.
- **The page waits outside `run`.** `run` is what makes the page busy, and
  waiting inside it stood every drawing tool and undo disabled for up to ten
  minutes. The requests go through it; the wait sets only the rebuild's own
  flag, which its buttons and the Zeitraum read (`garden/useRebuild.ts`). A
  second press while one runs starts nothing and says it still runs.
- **What it says is its own**, in the problem tone: failed, interrupted, or
  that it takes unusually long *and goes on* — `run` would have called the
  last one "fehlgeschlagen". Four unanswered status requests in a row are
  ridden out, as a deployment answers 502 for a few seconds and then that the
  job is gone; the fifth ends the wait with *Der Server antwortet nicht*.
- **Nothing lands in a garden that was left.** Every answer is checked
  against the workspace still being open: the garden, set again after the
  gardener had gone home, opened itself over the front page.

## A thing that had to be learned twice

The map was fetched in `refresh` only — and a garden opened from its share link
never goes through `refresh`. That function already carried a comment warning
about exactly this, written after the last feature it happened to. The comment
now names its second victim.
