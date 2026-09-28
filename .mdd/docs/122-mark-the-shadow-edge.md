---
id: 122-mark-the-shadow-edge
title: Mark the Shadow Edge — the Gardener's Eye Against the Model's Shadow
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-26
wave_status: active
depends_on: [115-the-measuring-instrument, 116-no-hull, 118-the-sky-counts, 120-a-roof-casts-as-a-roof, 121-a-crown-is-not-a-cylinder]
relates: [89-three-steps-in, 99-paper-bleed-and-a-real-shadow, 93-where-the-roof-came-from]
source_files:
  - ninanatur/solar/shadow_edge.py
  - scripts/blender_shadow_study.py
  - ninanatur/garden/shadow_marks.py
  - ninanatur/api/shadow_marks.py
  - ninanatur/api/schemas_marks.py
  - ninanatur/api/ratelimit.py
  - ninanatur/ingest/schema_user.py
  - ninanatur/web/app.py
  - frontend/src/shadowMarks.ts
  - frontend/src/garden/useShadowMarks.ts
  - frontend/src/garden/useGarden.ts
  - frontend/src/components/ShadowMarkPanel.tsx
  - frontend/src/components/ShadowMarkLayer.tsx
  - frontend/src/components/ElementDetails.tsx
  - frontend/src/components/PlanArea.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/GardenCanvasProps.ts
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/components/SceneWorld.tsx
  - frontend/src/components/ClusterLayer.tsx
  - frontend/src/components/ToolRail.tsx
  - frontend/src/components/GardenWorkspace.tsx
  - frontend/src/canvas/shapes.ts
  - frontend/src/canvas/useDrawingModes.ts
  - frontend/src/api/client.ts
  - frontend/src/api/types.ts
  - frontend/src/styles.css
routes:
  - GET /api/v1/gardens/{token}/shadow-marks
  - POST /api/v1/gardens/{token}/shadow-marks
  - DELETE /api/v1/gardens/{token}/shadow-marks/{mark_id}
models: [shadow_mark]
test_files:
  - tests/test_shadow_edge.py
  - tests/test_shadow_marks_api.py
  - tests/test_shadow_mark_heights.py
  - tests/test_security_matrix.py
  - frontend/src/shadowMarks.test.ts
  - frontend/src/garden/useShadowMarks.test.ts
  - frontend/src/components/ShadowMarkPanel.test.tsx
  - frontend/src/components/GardenCanvas.viewpoint.test.tsx
  - frontend/src/components/ToolRail.test.tsx
  - frontend/src/App.details.test.tsx
  - frontend/src/App.marks.test.tsx
  - frontend/src/App.sheet.test.tsx
  - frontend/src/testing/appFixtures.tsx
  - frontend/vitest.config.ts
data_flow: mixed
last_synced: 2026-09-28
status: complete
phase: all
mdd_version: 11
tags: [solar, shadow, calibration, instrument, observation, plan, sun-position, owner-check]
path: Garden/Light/Shadow marks
integration_contracts:
  - from: 116-no-hull
    function: shadow_rings — the shadow the page draws is the shadow the model counts
    when: a single moment's shadow of one standing thing is asked for
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The Blender sun study the plan asks for was not made: Blender was not installed where this was built, and installing it is a download the owner has to allow. The independent check was made against NREL's SPA and trigonometry instead (below); the case is written out so the Blender study can be made from it. *Resolved 2026-09-28: the owner allowed the download, and Blender 5.2.2's Cycles puts the corners within 0.1 mm of the hand's (`scripts/blender_shadow_study.py`, below).*"
  - "The predicted edge falls on level ground at the height of the thing's own ground, as the day's playback draws it (doc 116): on a slope the real edge lies nearer uphill and further downhill, and a mark there reads a height error that is the ground's."
  - "Only the marked thing's own shadow is read. Where another shadow joins it — a neighbour's tree, a hedge — the edge the gardener sees is their union's, and a mark on the other thing's part reads as this thing's error."
  - "The reading's height and angle are first-order: a mark near a corner of the shadow, where the way runs neither along the sun nor across it, reads whichever of the two is larger."
  - "The time field is the browser's clock and time zone: a device set to another zone marks another moment."
  - "A mark can only be placed with a pointer: a click or a tap on the plan, as the rail's Standpunkt is placed (doc 89). There is no keyboard way to put a point on the plan yet."
  - "Where a shadow begins — a crown's near end, cast by where the crown starts — the page says how much earlier or later the model begins it, and names no cause: a crown base, a crown's width and a crown's height all move it."
  - "The height a far edge amounts to is what a metre of the thing — lower or taller, as the mark asks — moves it: where that metre changes which part casts the edge — a gable's eaves giving way to its ridge — the height said is the metre's average, and a correction by it lands near the mark rather than on it. Where no metre of height moves the edge (eaves the gardener gave), no height is said, and the page does not say which other number would."
sister_projects: []
---

# 122 — Mark the Shadow Edge

## Why

Every test in this wave compares the model with something that shares its
inputs: the sun against NREL's algorithm, the geometry against a marched ray,
the sampling against a finer one (doc 115). None of them can see the three
errors that live in the inputs themselves:

- **a wrong height** — the survey's ridge, the storey count, a guess;
- **a wrong north** — a plan drawn a few degrees off, or imported from a map
  whose outline sits rotated on the garden's axes;
- **a wrong place or clock** — an anchor in the next street, a moment read
  in the wrong time zone.

The gardener can. They stand in the garden and see where the shadow of their
house ends, now. Marked on the plan, with the moment, that is an observation
the model can be held to — the cheapest instrument that reaches reality.

## The mark

A point on the plan where the gardener sees the **edge of the shadow of one
standing thing**, and the moment they saw it:

- the thing: an element that casts (`casting.casts`) — a house, a shed, a
  wall, a hedge, a tree;
- the point: garden metres, where the plan is clicked once the thing's
  details have armed it;
- the moment: now by default, or the time they type (the gardener's own
  clock on the page, UTC in the store). A moment in the future is refused —
  a mark is an observation, not a question; five minutes of a phone's clock
  running fast are allowed — and so is a moment the sun is below the model's
  lowest altitude (`MIN_ALTITUDE`): there was no shadow to see.

Marks are the gardener's, like the garden: a `shadow_mark` table on the
volume, deleted with the garden and with the thing whose shadow they mark.
What is stored is only the observation, and at most fifty a garden
(`MAX_MARKS`): an instrument, not a diary.

## The prediction

The model's answer is computed on every read, never stored: the sun at that
moment for the garden's anchor (`sun_position`), the thing cast as the light
model casts it (`garden.casting` — a roof as its planes, a crown as its
ellipse), and its shadow rings at that moment (`shading.shadow_rings`, the
same drawing the day's playback uses — doc 116's rule that the shadow drawn
is the shadow counted). So a mark keeps measuring the model as the model
changes, and as the gardener corrects the height it disagrees with.

From the rings, the **nearest point on the predicted edge on the ground**,
and the offset from the mark to it:

- its **length**, in metres;
- its **sign**: the model's shadow reaches past the mark (*too long*) or stops
  short of it (*too short*) — whether the mark lies inside the predicted
  shadow;
- its **components** along the sun's direction and across it;
- **which edge** it is: one facing away from the sun, which a top cast
  (*far*); one facing it, where a shadow begins — a crown's, cast by where
  the crown starts (*near*); or a side.

The drawn shadow holds the thing's own outline too, and its sunlit walls are
not an edge anybody marks: they are left out (`shadow_edge._on`). The review
of 2026-09-28 found a mark in a lit courtyard read against the courtyard's
wall, 2 m away, where the model's shadow ended 2.8 m away — and a crown's
near end read as a height, the page saying "zu kurz" and "zu hoch" at once.

## What the offset says

- **Along the sun, at a far edge**: the shadow is too long or too short, and
  the page says it in metres of height ("als stünde es 0,6 m zu niedrig"),
  not at all under 5 cm. For a block a length error δ at sun altitude h is a
  height error of δ·tan h. But since roofs cast as roofs (doc 120) a far edge
  is often a gable's eaves', which the ridge hardly moves: at a 62° sun a
  mark behind such an edge read "a metre too low", a height no correction
  could satisfy (review of stage 3, 2026-09-28). So the height said is what
  a metre of the thing, as the model would make it — eaves the gardener gave
  staying where they are, eaves and a crown base it assumes moving with it,
  eaves above a lowered ridge coming down to it — moves that very point of
  the edge, measured from it along the sun (`shadow_edge.reach_past`), and
  in the direction the mark asks for: a metre lower where the model's shadow
  reaches past the mark, a metre taller where it stops short (half a low
  thing's height, where that is less). Probed upward only, the roof's own
  switches answered for the wrong direction: a gable cast flat said no
  height, eaves just above the ridge said 2.5 m where 0.75 was right, and
  eaves that only just cast the edge said "0,4 m zu hoch" of a ridge no
  lowering could help (review of 45eb56a). No point of an edge moves faster
  than a block's; one that seems to is a gap between two shadows closing,
  and is taken at a block's rate. Where a metre moves it less than a quarter
  of what it moves a block's, no height is said: the number would be more
  than four times a block's.
- **At a near edge**: the model begins the shadow earlier or later ("Im
  Modell beginnt der Schatten 0,8 m früher") — no height.
- **Across the sun**: the shadow points the wrong way — the plan's north, or
  the thing's outline, is turned. The page gives the angle it is turned by,
  as seen from the thing; a miss that runs straight towards or away from the
  thing turns it through far less than its length, and is called no turn.
- **Both, growing through the day**: a clock or an anchor. Two marks at
  different hours tell a turned plan (the same angle at both) from a wrong
  time (an angle that follows the sun's motion).

One mark says how far out the model is; it does not correct anything. The
height, the north and the anchor stay the gardener's to change, where they
already can.

## On the page

- The details of a thing that casts carry a **Schattenkante** panel: what the
  instrument is for, a time field (*Gesehen am*) that means *now — the moment
  of the click* until the gardener types another, and **Im Plan markieren**.
  Pressing it arms the plan — the hint over it says so; a second press,
  Escape, or choosing anything else puts it down, and Escape leaves the thing
  chosen — and the next click is the mark, placed the way the rail's
  *Standpunkt* places a viewpoint (doc 89). On a phone a sheet raised over
  the plan comes down. It is armed from the thing's details rather than from
  the rail because a mark is always of one thing's shadow: the details
  already say which. The field first held the moment the garden was opened,
  and a mark placed hours later was read against that sun (review,
  2026-09-28).
- A thing that no longer casts keeps its panel while it has marks, so they
  can be forgotten.
- The panel lists the thing's marks: when each was seen, what it found in a
  sentence ("Das Modell wirft den Schatten 0,8 m zu kurz — als stünde es
  0,6 m zu niedrig"; a turn asks whether the plan's north is right), and a
  button to forget it. The sentence is also said in the status line when the
  mark is placed.
- The plan draws every mark as a cross, the model's shadow of its thing at
  its moment as a dashed outline, and a line from the cross to that
  outline's nearest point — above the shapes, and never a target
  (`ShadowMarkLayer`).
- The marks are read when the garden opens and again with each change to a
  garden that has any, since every reading is the model's as it now is; a
  garden without marks costs no request per edit. Only the newest answer
  counts, and none from before a mark was placed or forgotten. Opening reads
  once — the marks the first read brought were a reason to read again — and
  a read a busy server turns away (the heavy slot, 429) is asked again after
  the seconds it names, three times, before the page says the marks could
  not be read (review of stage 3, 2026-09-28). A mark placed or forgotten
  while a read is under way, or after one failed, asks again: it drops that
  read's answer, and the marks it would have brought stayed hidden until the
  next edit (review of 45eb56a).
- While a mark is armed the plan takes the click wherever it lands, a
  planted patch included: the patches kept their clicks, and a mark aimed at
  a planted bed chose the planting instead.

## What it costs

Reading casts the thing's shadow — for a many-cornered roof the dearest
geometry the app has (a 480-corner concave house: 25.6 s for its first
decomposition, measured in the review). Both routes that read take a heavy
slot, as the day's playback does; marking counts against its own allowance
(30 in ten minutes); each thing is cast once per read however many marks it
has — twice, with the copy a metre taller that says what a height moves, and
the two share one outline and so one decomposition. The fifty-mark limit is counted in the insert itself, so two requests
at once cannot both slip under it.

## The independent check

The plan asks for one synthetic case compared once against an independent
tool, documented rather than automated. Blender was not available (known
issues), so the case was compared against the two things that share nothing
with the model: NREL's SPA for the sun — the reference table pvlib made for
doc 115 — and trigonometry for the shadow.

**The case.** A flat block 10 × 8 m and 9 m high, its middle at the garden's
origin, near Osnabrück (52.1682° N, 8.3837° E), on 13 August 2026 at
11:38:25 UTC. SPA puts the sun at 52.3785° altitude and 182.8007° azimuth;
the model at 52.3801° and 182.8020°. The block's northern corners cast to
9·cot h straight away from the sun: by hand, (−4.661, 10.928) and
(5.339, 10.928) m. The model's drawn shadow has its corners **0.4 mm** from
those points, and a mark placed at either reads under a centimetre
(`test_the_shadow_ends_where_nrels_sun_and_a_hand_put_it`).

**In Blender.** The owner allowed the download on 2026-09-28, and Blender
5.2.2 LTS (blender.org, checksum verified, installed for every project) made
the study: `blender --background --factory-startup --python
scripts/blender_shadow_study.py`. A 10 × 8 × 9 m box on a plane, north along
+Y, a sun lamp at SPA's altitude and azimuth with no angular size, a black
world and no bounced light; Cycles renders 20 × 20 m straight down at a
centimetre a pixel, and the shadow's edges are read off the render to a
fraction of a pixel. Its far corners: (−4.6611, 10.9281) and (5.3389,
10.9281) m — **0.1 mm** from the hand's, so the model's drawn shadow is
within half a millimetre of what Blender renders, the difference being the
model's own sun against SPA's. Nothing of NinaNatur runs in it: the geometry
is Cycles', the sun SPA's.

## Business rules

1. A mark is an observation: a point, a thing, a moment in the past with
   the sun up. Only the observation is stored.
2. The prediction is the model's current answer, recomputed on every read,
   through the same casting and drawing the light map uses.
3. The offset is stated, never applied.
4. Marks belong to the garden and go with it.
