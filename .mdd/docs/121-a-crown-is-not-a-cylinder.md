---
id: 121-a-crown-is-not-a-cylinder
title: A Crown Is Not a Cylinder — an Ellipsoid on a Trunk, Passing Light by Its Depth
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-26
wave_status: complete
depends_on: [117-room-to-compute, 118-the-sky-counts, 120-a-roof-casts-as-a-roof, 107-the-cloud-under-the-crown]
relates: [66-a-tree-is-not-a-wall, 84-what-else-is-standing-there, 116-no-hull, 119-energy-not-hours]
source_files:
  - ninanatur/solar/crown.py
  - ninanatur/solar/moments.py
  - ninanatur/solar/raster.py
  - ninanatur/solar/raster_grid.py
  - ninanatur/solar/shading.py
  - ninanatur/solar/field.py
  - ninanatur/solar/light.py
  - ninanatur/garden/casting.py
  - ninanatur/garden/canopy.py
  - ninanatur/garden/lightview.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/garden/lightgrid_cost.py
  - ninanatur/garden/cloud_sync.py
  - ninanatur/garden/building_sync.py
  - ninanatur/geo/cloud_store.py
  - ninanatur/garden/models.py
  - ninanatur/garden/elements.py
  - ninanatur/garden/element_edits.py
  - ninanatur/ingest/schema_user.py
  - ninanatur/ingest/schema_computed.py
  - ninanatur/ingest/migrations.py
  - ninanatur/api/canopies.py
  - ninanatur/api/light.py
  - ninanatur/api/elements.py
  - ninanatur/api/gardens.py
  - ninanatur/api/schemas.py
  - ninanatur/api/schemas_garden_in.py
  - frontend/src/components/ElementForm.tsx
  - frontend/src/components/CrownBaseField.tsx
  - frontend/src/components/useStoredField.ts
  - frontend/src/garden/selection.ts
  - frontend/src/heights.ts
  - frontend/src/api/types.ts
  - frontend/src/testing/elementForm.tsx
  - scripts/measure_crowns.py
  - scripts/measure_crown_cost.py
routes:
  - GET /api/v1/gardens/{token}
  - PATCH /api/v1/gardens/{token}/obstacles/{obstacle_id}
  - POST /api/v1/gardens/{token}/canopies/{suggestion_id}
  - POST /api/v1/gardens/{token}/light
models: [element, cloud_window]
test_files:
  - tests/test_crown_heights.py
  - frontend/src/components/ElementForm.stored.test.tsx
  - tests/test_crown.py
  - tests/test_crown_casting.py
  - tests/test_crown_laser.py
  - tests/test_schema_upgrade.py
  - tests/test_light_model_version.py
  - tests/test_planted_shade.py
  - tests/test_sky_api.py
  - tests/test_kind_vocabulary.py
  - tests/test_canopies.py
  - frontend/src/components/ElementForm.crown.test.tsx
  - frontend/src/heights.test.ts
  - frontend/src/garden/selection.test.ts
data_flow: writes-existing
last_synced: 2026-09-28
status: complete
phase: all
mdd_version: 11
tags: [solar, shadow, crown, tree, ellipsoid, transmission, beer-lambert, laser, crown-base]
path: Garden/Light/Crowns
integration_contracts:
  - from: 117-room-to-compute
    function: a part that attenuates by the depth of its crossing rather than a fixed share
    when: a caster stops being a solid of one transmission
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Crowns shade far less than they did, by the plan's own calibration: k makes the *longest* chord pass the old share, so a typical chord — two thirds of it — passes 0.2^(2/3) = 0.34 in leaf, and a crown on a trunk a third of its height up, as wide as two thirds of its height, lets all but the high summer sun in beneath it. A lone 12 m lime takes about 1.5 h at most from anywhere around it; the spot at its foot reads 12.98 h and L 9 where the cylinder said 4.37 h and L 6.25 (What moved). Never darker along any ray, as promised — but a gardener will read L 9 under a lone tree. Levers, the owner's to choose: calibrate k on the mean chord (a crown's average shade stays the old number), a lower assumed base, a wider crown for trees (`canopy.CROWN_RATIO`, a third of the height as radius)."
  - "The ellipsoid's underside is round. An open-grown broadleaf's lowest branches spread nearly flat at its base, so the ground under a real crown is shaded at lower suns than the model's — the model errs light there."
  - "The old cylinder was the 16-gon `footprint_of` inscribes in the crown's radius, and the round crown bulges past its flat faces by 1.9 % of the radius — 7.7 cm on the lime. A ray grazing a face there passed all and passes 0.8 now: darker by up to 0.0016 h on a planted evergreen shrub's rim, below every stored rounding (review, 2026-09-28)."
  - "A planted tree's crown base cannot be entered: it is always the assumption (a third of its height, the ground for anything else). Only a drawn tree or shrub has the Kronenansatz field."
  - "The laser's base is the median of `CloudWindow.crown_at` over the crown's middle half: for a round crown about 0.07 of its vertical semi-axis above the true base, and a shrub standing under the tree reads as the crown."
  - "A laser window stored before 2026-09-28 carries neither the garden it was read around nor a building model's classification, and gives no crown base until its place's light is next computed, which reads the tile again (tens of megabytes, once a place). A state with a point cloud and no building model never gives one."
  - "A roof neither the survey's building model nor the garden's drawing knows — a garage nobody drew, in a state whose model misses it — still reads as a crown to the laser."
  - "The plan's decorative drop shadow (Draft Sketch, doc 99) still sweeps a tree's outline by the offset of its top, from the ground: one offset per object cannot be an ellipse, as doc 120 says of a roof. The day's playback draws the crown's shadow exactly."
  - "The API takes a crown base above the tree's height; casting keeps it inside the tree (a crown two centimetres deep at its top) rather than refusing it, since the height may change afterwards."
  - "Sightlines still see a tree as a prism to its full height (`api/sightlines.py`): a crown on a trunk hides a view whole, where the light model sees under and through it."
  - "Reading every stored laser window again for the crown bases made each garden's first relight after the update as long as a first analysis — past the preview proxy's 90 s, which answered 504 while the server went on (the owner, 2026-09-28). The relight is a job since (doc 65): the page waits for it."
  - "A crown is priced the same whatever its size, fitted on crowns 6–8 m across: a garden of small crowns is estimated high and drops a rung it could afford. Sixty drawn shrubs 1.5 m across on a 24 × 40 m plot get 5 m cells, where 3 m took 3.4 s against an estimate of 5.6, and a garden of crowns 3–7 m across gets 1 m where 0.5 m took 3.8 s (estimated 5.6). The estimate stays above what they take, so no budget is broken (review of 8040ffc); a price by a crown's size would give them their rung back."
sister_projects: []
---

# 121 — A Crown Is Not a Cylinder

## Why

A crown was a cylinder from the ground to its top, passing a fixed share of
the sun — a fifth in leaf, three quarters bare, a twelfth for a conifer —
whenever a ray touched it at all. So the ground under a crown, where shade
beds are planned, kept only that share at every sun angle, though a low sun
passes under a crown on a trunk and a ray through its rim crosses a
hand-width of leaves, not the whole tree.

And a tree the gardener drew, or took from the laser survey, was not even
that: it cast as an opaque block to its top, a wall (docs 118, 120, known
issues). The canopy model's own words — "a tree was modelled as a wall; it is
not one" — held only for trees planted from the catalogue, and the suggestion
endpoint's promise of "a broadleaf in leaf" for a laser tree was never kept.

## The crown

An **ellipsoid on a trunk** (`solar/crown.py`): centred over the tree, its
horizontal semi-axis the crown's radius r_h, its vertical one
r_v = (top − base)/2, its centre at base + r_v. Below the base there is only a
trunk, which is thin and casts nothing the model counts.

**The crown base** is where the canopy starts:

1. what the gardener entered (`crown_base_m`, source `user`);
2. what Wave 25's laser read (`CloudWindow.crown_at`, source `measured`) —
   stored since doc 107 and read by nothing until now — for every tree
   nobody has given a base, drawn or taken from the survey's suggestions
   (`cloud_sync.fill_crown_bases`, on the light's path and when a suggestion
   is accepted). The median over the cells within half the crown's radius
   (`crown_base_under`): nearer the rim, the lowest leaves of a round crown
   are its side rather than its base; rounded to the centimetre, and leaving
   out the cells inside a drawn house or shed;
3. otherwise assumed (`canopy.crown_base`): a third of the height for a tree,
   as the plan says; the ground for a shrub, which branches from it — a third
   would leave a gap under a shrub that no shrub has.

### What the laser can be trusted with

The review of 2026-09-28 found Wave 25's windows unfit to read a tree's base
from, for two reasons that did not matter while nothing read them:

- **Whose axes.** A window is shared by every garden in its place (the 100 m
  key the terrain uses) and was drawn on the axes of the garden that read
  it. A second garden 53 m away read it on its own axes and took the first
  garden's tree for its own. The window now keeps the garden it was read
  around (`cloud_window.anchor_lat`/`anchor_lon`), and another garden moves
  it onto its own axes by where it stands from the first (`load_cloud`).
- **Roof or crown.** NRW's cloud has no building class, and the light path
  read it without the survey's building model, so a roof's lowest returns
  were a crown base. The survey's model is passed on now
  (`building_sync.Measured.buildings`), the window says whether one
  classified it (`classified`), and only a classified window gives a base.

A window missing either is read again at its place's next light
computation. The terrain windows share the first flaw; that is its own task.

## Light by depth

A ray crossing the crown passes what Beer–Lambert says a crown of even
density passes over the length L of the crossing:

    T = exp(−k·L),   k = −ln(T₀) / (2·max(r_h, r_v))

with T₀ the share the model used before (`canopies.transmission`: 0.20 in
leaf, 0.75 bare, 0.08 evergreen). The **longest** chord a crown has passes
exactly T₀, and every other passes more — the plan's promise, kept along
every chord; a ray through the rim, or under the crown, is lighter, as it is.
The ellipsoid lies inside the circle the old cylinder's 16-gon was inscribed
in, not inside the 16-gon, so at its faces it reaches 1.9 % of the radius
further (known issues).

The chord is the ray–ellipsoid intersection, solved as a quadratic along the
ray the raster already cuts its parts with — by horizontal distance towards
the sun (`crown.chord`). The grid asks it once a crown and a moment, over
the cells under the **ellipse the crown throws** at any height from the
grid's highest cell to its lowest, not the square round it swept from the
ground: the trunk casts nothing, and most of that sweep is lit
(`raster_grid._shade_crown`). The sky's patches (doc 118) cross crowns by the
same arithmetic, so the spot under a tree sees the low sky between the trunk
and the crown.

## Which casters are crowns

- a woody plant from the catalogue (`lightview._crown_of`), which was a
  cylinder with the right shares — and, as before, anything planted that
  grows past 1.5 m (`canopy.shades`);
- a **tree or shrub the gardener drew**, and a tree taken from the laser
  (`casting._crown`) — which were opaque blocks. They take a broadleaf's
  shares, as the canopy model does for a species whose leaves the catalogue
  does not know. A circle is its centre and radius; another outline gives
  its centroid and the radius of a circle of its area, so the crown holds as
  many leaves as the shape drawn — when it is round enough to be one crown
  (`casting.crown_disc`: its centroid inside it, no corner beyond 1.5 times
  that radius; a 2:1 oblong is, a 3:1 one is not). A row drawn as a line, a
  band or an L is not: it casts as its outline, passing a crown's share
  wherever a ray meets it, as planted crowns did until now. The review of
  2026-09-28 found a row of shrubs cast as one ball at its middle, shading
  open ground and leaving the row's own side lit;
- a **hedge** stays a solid prism: it is leaves to the ground, not a crown on
  a trunk.

The slow field (`solar/field.py`) casts prisms only and refuses a crown, as
it refuses a roof.

## Who says where a crown starts

The same rule as the eaves (doc 93): only the server writes
`crown_base_source`. A PATCH that carries `crown_base_m` marks it `user`, an
emptied one makes it nobody's again — and the laser may answer it, as the
survey answers emptied eaves; the laser marks what it fills `measured`; a
client that names a source is not heard. Two columns, added to
`CREATE TABLE element` and to `COLUMN_MIGRATIONS`. The crown base enters the
map's signature, so a changed base makes the map stale.

The element form asks a tree and a shrub for their **Kronenansatz** — and
says, under the field, what the model reckons with when nobody has said
("mit einem Drittel der Höhe, 4,0 m" for a tree, "ab dem Boden" for a shrub),
or that the laser measured it. The assumption is mirrored in `heights.ts`
and held to the server's by `test_kind_vocabulary`.

Two corrections from the review of stage 3 (2026-09-28). Where no crown fits
what was drawn — a line, a band, an L — the thing casts as the solid a row
is, from the ground, and a base changes nothing: the answer says so for every
outline, beds included (`crown_fits`), so a form that turns a hedge or a bed
into a tree knows it too, and the form says why instead of asking. And the laser fills a base when the light is computed, often while
the form is open: a field that kept the value it opened with then sent the
old one back on the next save, as the gardener's. An untouched field follows
the store now, and a touched one keeps what was typed (`useStoredField`) —
the height, the roof and the eaves as well.

## What the plan draws

A crown's shadow on the ground is an ellipse — the ellipsoid is a sphere
stretched, and so is its shadow: the image of the unit disc under the
projection, found by a Cholesky factor of its shape matrix (`crown.outline`).
The drawn ring is pushed out by 1/cos(π/n) so it holds the ellipse rather
than cutting its rim; the counted shadow is the exact ellipse
(`test_the_plan_draws_the_shadow_where_the_ray_meets_the_crown`, outside a
5 cm band at the rim).

## What it costs

`python -m scripts.measure_crown_cost` prints what follows, on this machine:
drawn trees 8 m across and 12 m tall on a 94 m plot, at forced cells from
2 m to 0.5 m, and the cell the ladder picks. A crown on the grid costs about
71 ms and 0.0008 ms a cell, against a part's 95 ms and 0.002. It was priced
as the part it is at first, with room; with the room the stretch below adds,
gardens with trees and a tall house dropped a rung they could afford
(review of 7108fff), so it is priced as a crown now: 75 ms and 0.001 ms a
cell (`NEAR_CROWN_MS`, `CELL_NEAR_CROWN_MS`) — 36 trees took 4.8 s at 0.5 m
against an estimate of 5.7, and 12 get 0.5 m. Before the grid asked only the
cells under the crown's ellipse, and before the quadratic lost its redundant
branches, the same 36 trees took 11.3 s — above the estimate, which is how
it was found.

Off the grid a crown costs more than a far part: one just past the grid's
edge throws its shadow in at most moments, not only while shadows are long.
24 laser trees 12 m outside the plot took 0.96 s at 2 m cells where the far
price said 0.75 (review, 2026-09-28); each far crown now adds
`FAR_CROWN_MS`, 15 ms, and the estimate holds from 6 m out to 30.

And a crown asks about more cells the further the grid's cells stand apart
in height: the grid sizes each crown's box of cells from the grid's lowest
cell to its highest, so a slope, or a roof on the plot, stretches every box
towards the sun by the height between them. The review of stage 3 found a
garden from the map at 6.6 s on a slope where the estimate said 4.8. The
first price was keyed on what raises the cells — terrain, pitched planes —
and the review of its fix found level surveyed ground paying for a slope
(12 trees: estimated 13.3 s, took 2.8, pushed off the 0.5 m rung) while a
15 m house of no known shape paid nothing (took 5.3 s where 3.5 was said).
It is keyed on the height itself now (`lightgrid_load.relief_of`: the
ground's range over the box and the ridge of every roof on it, of any
shape), and priced per crown by the cell's size: the stretch is in metres,
so the cells it adds go with 1/cell², and priced per cell of the whole grid
an ordinary 24 × 40 m garden was estimated under what it took, two of them
past the budget (review of 596a89f). Measured by difference — trees and a
house, less the trees, less the house — per crown and metre: 1.4, 4.7 and
17.7 ms at 2, 1 and 0.5 m on the 94 m plot, a millisecond and 4.3/cell²; on
the small plot the second part came to 0.56 of that at every cell, a
smaller grid clipping the stretched boxes (taken as its width over 60 m).
Priced at 1 ms + 4.5/cell² ms per crown and metre (`CROWN_RELIEF_MS`,
`CROWN_RELIEF_M2_MS`, `RELIEF_REACH_M` 70 m), and added whole: the fit is
of whole runs, the sky's sweep in it, and multiplying it by the sky's share
again made every crown garden pay a fifth more (review of 7108fff). Every
case in `scripts.measure_crown_cost` holds, most within a third of what
they take: level surveyed ground and a flat 9 m house on the 94 m plot get
0.5 m; the small plot with 16 trees and a 15 m house gets 0.5 m (took 3.9 s,
estimated 4.8), with 20 trees, the house and neighbours 1 m, where 0.5 m
would take 5.5 s.
Narrowing each box to the heights under it was tried and saved nothing;
`test_crown_heights` holds every cell beside a roof to the point's answer,
whichever way the box is sized.

## What moved

A lime of 12 m, its crown 8 m across from 4 m, in Wuppertal over the season
(`python -m scripts.measure_crowns`):

| North of the trunk | block (drawn) | cylinder (planted) | crown |
|---|---|---|---|
| at its foot | 0.00 h, sky 0.00, L 2.5 | 4.37 h, sky 0.20, L 6.25 | 12.98 h, sky 0.80, L 9 |
| 3 m | 0.00 h, sky 0.00, L 2.5 | 4.37 h, sky 0.20, L 6.25 | 11.80 h, sky 0.85, L 9 |
| 6 m | 9.08 h, sky 0.78, L 9 | 10.52 h, sky 0.82, L 9 | 11.64 h, sky 0.91, L 9 |
| 10 m | 11.09 h, sky 0.92, L 9 | 11.83 h, sky 0.93, L 9 | 12.51 h, sky 0.96, L 9 |

**Decided, 2026-09-28.** The owner kept crowns as they are, rather than
denser leaves, a lower assumed base or wider planted crowns: the geometry is
checked, and density is better tuned later against shadow marks under real
trees (doc 122).

Open ground reads 13.08 h. From its foot, this crown fills the sky within
30° of the zenith — sin⁻¹(4/8) — which the sun at 51° N passes only around
noon in high summer, so its shade falls north of it far more than under it.
A 24 m oak in Berlin: the bed it stands in keeps 13.0 of 13.14 h and loses a
fifth of its sky; the bed 4–8 m north of it drops to 11.9 h. The light value
stays 9 in both (known issues).

## Business rules

1. A crown is an ellipsoid on a trunk; its base is the gardener's, the
   laser's, or an assumption that says it is one.
2. A crown passes light by the depth of the crossing, and never less than
   the share the model used before along any chord.
3. The drawing shows a crown's shadow where a ray meets the crown — the
   region the model attenuates (doc 116).
4. Only the server writes where a crown's base came from.
5. Every change to what the model answers raises `MODEL_VERSION` — 26.6.
