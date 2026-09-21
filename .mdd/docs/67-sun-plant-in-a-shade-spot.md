---
id: 67-sun-plant-in-a-shade-spot
title: A Sun Plant in a Shade Spot, and Which Hours It Gets
edition: MDD
initiative: ninanatur
depends_on: [64-light-across-the-bed]
relates: [64-light-across-the-bed, 65-the-shade-switch]
source_files:
  - ninanatur/garden/misplaced.py
  - ninanatur/fit/light_fit.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/solar/field.py
  - ninanatur/api/light.py
  - frontend/src/components/ShadeSwitch.tsx
routes:
  - GET /api/v1/gardens/{token}/light
models: [light_grid, planting, trait]
test_files:
  - tests/test_misplaced.py
  - tests/test_light_grid.py
  - frontend/src/components/ShadeSwitch.test.tsx
data_flow: reads-existing
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [ellenberg, warning, shading, morning, halbschatten]
path: Garden/Light
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Species without an EIVE light value are never flagged; EIVE covers a good part of the German flora, not all of it."
---

# A Sun Plant in a Shade Spot, and Which Hours It Gets

## The warning

Suggestions have always ranked by fit, light included, so what goes *into* a bed
is chosen against the site. Nothing ever looked at what was **already there** —
and until the grid existed nothing could: one number per bed can say the bed is
wrong, never the corner. "This bed is too dark" for a bed whose far end is in
full sun is the kind of advice that teaches people to ignore advice.

Each cluster's Ellenberg L is compared against the light in the cell it
actually stands in, and a warning is given when the light is **unsuitable** for
it: more than 1.5 of the species' own niche half-widths away (`03-niche-fit`).
That is the rule the suggestions cut by (`fit.light_fit`, shared by both), so a
species the list offers for a spot is never one the map then says stands in the
wrong light. A borderline difference says nothing: it is inside the noise of a
model whose building heights are mostly assumed, and a warning nobody can act
on is a warning people learn to scroll past.

Until 2026-09-21 the warning used a fixed distance of two classic rungs instead
(2.0, then 2.5 on EIVE's scale). With an open spot at 9.0 the list offered
*Quercus robur* (L 6.2, a niche 6.9 wide: 0.8 half-widths from full sun,
merely *suitable*) for full sun and the map then called it too bright — two
rules for one question (review, 2026-09-21).

**Where the light is read** is the one difference left. The list ranks a bed by
its average; the warning reads the cell a cluster stands in, because a corner
darker than its bed is what it is for. Where a cluster has no cell of its own
it is judged by the value the list ranks its bed by (`misplaced._hours_at`):
- **a cluster nobody placed** — what the list's add button plants. It stands
  nowhere in particular; read at the bed's middle, a bright cell of a bed half
  in shade, a species the list had just offered was warned about at once.
- **a raised bed**, whose light is sampled at its height, over whatever darkens
  the ground grid beside it;
- **a cell under a roof**: `LightGrid.at` answers None there, as it always said
  it did, and until the review it had handed back the roof's sun.

A placed cluster in a bed narrower than a cell reads its own cell like any other:
for a while the whole of such a border was judged by the one sample at its
middle, and its shaded end lost its warning. And the warning stays
on the season's grid when a month is shown (`api/light._read`): a month's grid
had quietly taken its place, and warnings came and went with the months.

Both directions are named. `too_bright` is as real as `too_dark` — a fern in the
open is as misplaced as a sedum under a hedge — and only one of the two ever
gets talked about.

**A warning, never a refusal.** The gardener may know something the model does
not: a cultivar bred for shade, a wall that throws light back, or simply that
they want it there. The panel says so in as many words, under the list.

That holds for what is already planted. What is *offered* became stricter on
2026-09-21, by the owner's decisions (review #9, `13-bed-suggestions`): the
suggestions leave out a species whose light is *unsuitable* here, too bright or
too dark — the best fit for the shade as much as for the sun.

## Which hours

The grid also counts the sun before the azimuth crosses due south, and the panel
reports the share. Afternoon sun is hotter and harsher, and a great many species
sold as *Halbschatten* want the morning specifically — a single total of four
hours cannot say which four.

Grids computed before the split existed keep working: `morning` comes back empty
and the panel leaves the line out until the next rebuild fills it.

## Tests worth keeping

`tests/test_misplaced.py` covers the same species being fine at the far end of
the same bed — which is the whole reason the grid had to come first — as well as
a difference just under tolerance, a species with no EIVE value at all, and a
garden with no grid.

`tests/test_light_grid.py` proves the split against geometry rather than
arithmetic: a wall to the east costs the morning specifically, and the morning
share behind it drops below 0.4.
