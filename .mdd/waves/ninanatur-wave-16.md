---
id: ninanatur-wave-16
title: "Wave 16: The shade switch"
initiative: ninanatur
initiative_version: 20
status: planned
depends_on: ninanatur-wave-15
demo_state: "Ein Schalter legt eine Sonnenstunden- oder Schattenstundenkarte über den Plan, in Graustufen bzw. Transparenz. Der Play-Knopf lässt den Schatten über einen mittleren Tag des gewählten Monats wandern. Das Licht wird über ein Raster berechnet, nicht an einem Punkt je Beet — und eine Sonnenpflanze, die im Schatten steht, wird als solche benannt."
created: 2026-09-04
hash: 413f1abc
---

# Wave 16: The shade switch

## Demo-State

Ein Schalter legt eine Sonnenstunden- oder Schattenstundenkarte über den Plan,
in Graustufen bzw. Transparenz. Der Play-Knopf lässt den Schatten über einen
mittleren Tag des gewählten Monats wandern. Das Licht wird über ein Raster
berechnet, nicht an einem Punkt je Beet — und eine Sonnenpflanze, die im
Schatten steht, wird als solche benannt.

*(This wave is not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | light-across-the-bed | — | planned | — |
| 2 | the-shade-switch | — | planned | 1 |
| 3 | a-day-of-shadow | — | planned | 2 |
| 4 | sun-plant-in-a-shade-spot | — | planned | 1 |
| 5 | morning-sun-is-not-afternoon-sun | — | planned | 1 |
| 6 | a-tree-is-not-a-wall | — | planned | 1 |
| 7 | what-shape-is-the-roof | — | planned | — |

## What each one is

### 1. light-across-the-bed

The model computes light at **one point per bed** — the centroid of its polygon.
A 40 m² bed whose northern half sits in the house's shadow all day still gets a
single number, the one from its middle. There is nothing to draw a map from.

**To do:** a grid of sample points over the garden, stored like `sun_hours` is
today — computed when something changes, read back per request. A bed's own
`sun_hours` becomes the mean over the cells inside it, which is a truer answer
than its centroid was.

**The performance work is the feature**, and it was measured before planning:

| | per point | 1 m grid, 20 × 15 m |
|---|---|---|
| As it stands | 125 ms | **37 s** |
| Sun positions and shadow polygons hoisted out of the loop | 20 ms | 6.1 s |
| Plus a bounding-box rejection before each point-in-polygon test | **1.09 ms** | **0.44 s** |

All three are the same mistake in different places: work that depends only on
the sun and the obstacles, redone for every point. 630 sun positions and 16,380
shadow polygons are computed once for the whole garden rather than once per
sample.

Resolution follows the garden rather than being fixed: 1 m where that stays
under roughly 600 cells, coarser above. A 40 × 60 m plot at 1 m is 2,400 cells
and 2.7 s, which is too long to make somebody wait after moving a shed.

**This also settles an old exclusion.** A woody planting is left out of its own
bed's shading because a planting had no position and would sit exactly on the
sample point. Wave 15 gave clusters real coordinates, so the reason is gone: a
tree can now shade the part of its own bed that it actually stands over.

**When it recomputes, and how much.** Asked while planning, and the measurement
changed the answer.

The obvious design is a diff: recompute only the cells one changed object can
reach. Measured over a season, for an object three metres south of a 20 × 15 m
garden:

| | cells it ever touches |
|---|---|
| Shed, 2 m | 19 % |
| Hedge, 6 m | 71 % |
| House, 12 m | **100 %** |
| Anything taller | 100 % |

So a diff pays for sheds and for nothing else. It is not worth the second code
path, and a second code path through geometry is exactly where the two answers
drift apart.

**Not by classifying actions.** That was the first answer and it is the wrong
shape: a list of which operations change the light is a thing somebody has to
remember to extend, and forgetting is silent — a stale map that looks right. The
objection came from the user and it is correct.

A **signature over the shading inputs** instead: a hash of every obstacle's
geometry, height and roof, plus every woody planting's position and species.
Recompute when it differs from the one the stored grid was made with. That is
not a judgement about an action, it is a fact about the inputs, so a new feature
cannot forget to declare itself. Adding a bed changes no obstacle and the hash
does not move; nudging a shed by 10 cm moves it and the map follows.

Then three ways it actually runs:

- **On a settled change**, at 0.44 s. Not per drag frame — a drag already sends
  one request when the pointer is released.
- **In the background when the garden is closed**, if the signature moved and
  nothing has recomputed since. The next visit opens on a current map.
- **A "Schatten neu berechnen" button.** Belt as well as braces: if the map ever
  looks wrong, somebody can force the whole thing without knowing why. It also
  makes the staleness visible — the button says when the map was last computed,
  which is the honest thing for a number this expensive to produce.

### 2. the-shade-switch

**To do:** a switch on the plan that draws the grid as a map — greys and
transparency over the garden, and a choice between *sun hours* and *shade
hours*. Sun reads inverted: more sun, more transparent, so the plan shows
through where it is bright.

The legend has to carry the number. "Darker means less sun" is not a reading;
"3 Stunden" is.

### 3. a-day-of-shadow

**To do:** with the switch on, the play button walks a mid-month day rather than
the bloom year — the shadow moving across the garden from morning to evening.
Either every month in turn, or only the month selected below.

This is the same control doing two things depending on a switch, which is a
thing to be careful about: the button's label has to say which.

### 4. sun-plant-in-a-shade-spot

The suggestions already rank by fit, including light. What nothing does is look
at a planting that is *already there* and say it is in the wrong place.

**To do:** compare each cluster's Ellenberg L requirement against the light at
the cells it actually covers — which feature 1 makes possible for the first
time — and say so plainly where they disagree. A warning, not a refusal: a
gardener may well know something the model does not.

Placement of a new planting should prefer the part of the bed that fits it.

### 5. morning-sun-is-not-afternoon-sun

Asked directly: is half a day of sun what botany calls Halbschatten?

Largely yes — the horticultural bands are ≥ 6 h full sun, 3–6 h partial shade,
below that shade, and `SUN_HOUR_BANDS` already encodes that staffel. But hours
alone cannot tell two situations apart that gardeners do distinguish:

- **Dappled light all day** under a canopy versus three hours of direct sun and
  then nothing. Both come to "4 hours" and they are not the same place.
- **When** the sun falls. Afternoon sun is hotter and harsher, and a great many
  species sold as *Halbschatten* want morning sun specifically.

The second is cheap: every sample already carries its timestamp and the model
throws it away. Splitting the hours at solar noon costs nothing and gives the
plan something to say that a single number cannot.

The first is not answerable from this model at all — it needs canopy
transparency, which OSM does not hold and the catalogue does not either. It is
recorded here as a limit rather than approximated.

### 6. a-tree-is-not-a-wall

Asked directly: can shade through trees be diffuse, except for conifers?

Yes — and the catalogue can nearly answer it. **GIFT trait 2.4.1
`Deciduousness_1`** carries `deciduous | evergreen | variable`, from a source
already ingested under CC-BY-4.0, so this becomes a trait with provenance rather
than a hand-kept list of conifers. Coverage measured before planning: **452 of
954 German woody species, 47 %**, and the ones that matter are right — Picea
evergreen, Taxus evergreen, Ilex evergreen, Quercus and Fagus deciduous.

Two things follow, and the second is larger than the first:

- **A canopy transmits.** A broadleaf crown in leaf passes some light; a spruce
  passes almost none. `is_shaded` stops being a boolean for plantings and
  becomes a transmission factor, and sun hours stop being a count and become a
  weighted sum. Buildings stay opaque, which they are.
- **A deciduous tree is bare in March.** The season starts on 1 March and the
  model currently shades a garden under a leafless oak exactly as hard as under
  a wall. That is not a refinement — it is a large error in the two months when
  a gardener is deciding what to plant.

Leaf-out and leaf-fall dates are the open part. They are not in the catalogue,
they vary by species and by year, and a single German average is probably the
honest first answer — said as an assumption, the way assumed building heights
already are.

`variable` is a third state and must not be silently folded into either. 6
species, and pretending is worse than saying so.

### 7. what-shape-is-the-roof

A building is a prism at one height, and OSM's `height` is usually the **ridge**
— so a gabled house is modelled as though its gables were solid to the ridge. It
shades too much, everywhere, all the time.

**To do:** the user can say what shape a roof is — flat, gable, hip, pent — in
the same right-click menu that already sets a kind and a height. It is one of
the few things somebody can answer by looking out of the window, which is the
test this project applies to every question it asks.

The eaves height is the open part. `building:levels × 3 m` is the obvious
estimate and OSM sometimes carries `roof:height` outright; where neither exists
the answer is an assumption and must be labelled as one, beside the assumed
heights already there.

## What the model does not know

Asked while planning, and answered by measurement rather than by argument. The
ground projection was checked against marching the ray to the sun in three
dimensions across 263 random scenes of overlapping buildings: **no
disagreements**, raised beds included. `tests/test_shading_is_ray_tracing.py`
keeps it that way, which matters because feature 1 rewrites this exact path.

Overlap and interception need no special case. The model never asks where a
shadow lands; it asks, per obstacle, whether that obstacle stands between the
point and the sun — and what else is in the way cannot change the answer. A
tree's shadow does run straight through a taller house on paper, and the house's
own shadow covers everything it does and more.

What is genuinely missing, and none of it is fixed by this wave:

- **Flat ground.** There is no terrain anywhere in the code. A garden below a
  slope, or a neighbour uphill, is wrong and silently so. **Wave 17** takes it
  on with public elevation data.
- ~~Flat roofs.~~ Feature 7 asks the user.
- ~~Opaque canopies.~~ Feature 6, as far as the data reaches. What stays out of
  reach is *how much* a particular crown transmits: `deciduous` is not a density,
  and an old beech is not a young birch.
- **No diffuse or reflected light.** A white south wall throws light back and
  the model does not know it.

## Open Research

- ~~Whether a grid is affordable at all.~~ **Answered before planning.** 125 ms
  per point today; 1.09 ms after hoisting the shared work and rejecting by
  bounding box first. A 1 m grid over an ordinary garden is 0.44 s, and it is
  computed on change rather than per request. Measured, not estimated.
- Where the grid is stored. It is user data, per garden, and derived — so it
  belongs on the volume beside `sun_hours` and must be invalidated by exactly
  the things that already invalidate that.
- Whether the map should read the whole garden or only the beds. The garden
  ground is where somebody decides *to put* a bed, which argues for the whole
  plot; the cost argues for the beds. Worth deciding with a picture in front of
  us rather than in advance.
