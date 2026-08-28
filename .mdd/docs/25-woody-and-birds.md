---
id: 25-woody-and-birds
title: Birds Count, and Woody Plants Get Room
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-6
wave_status: complete
depends_on: [17-insect-groups]
relates: [18-insect-score, 16-nativeness]
source_files:
  - ninanatur/ingest/db.py
  - ninanatur/ingest/sources/birds_de.py
  - ninanatur/ingest/sources/gbif.py
  - ninanatur/data/interactions.py
  - ninanatur/ingest/catalogue.py
  - ninanatur/garden/canopy.py
  - ninanatur/garden/store.py
  - ninanatur/solar/shading.py
  - ninanatur/api/filters.py
  - ninanatur/api/planning.py
  - frontend/src/components/SuggestionList.tsx
routes:
  - GET /api/v1/plants/{taxon_id}
test_files:
  - tests/test_birds_de.py
  - tests/test_canopy.py
  - tests/test_planted_shade.py
data_flow: mixed
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [birds, globi, gbif, partners, clade, insect-score]
path: Data/Partners
integration_contracts:
  - function: partner_totals / partner_summary
    when: any partner count is shown or scored
    note: counts are per clade; the insect score reads insects and is unchanged by adding birds
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 25 — Birds Count Too, Separately

## Purpose

Birds join insects as counted partners. GloBI already holds the relations: ten
common German bird genera alone account for **26,261** interaction rows in the
600k already ingested, so this is reading data we have rather than fetching new
data.

## The decision that shapes this: birds do not enter the insect score

Folding birds into the existing partner counts would silently change every score
this product has ever shown. *Salix caprea*'s 1,055 partners would grow, every
garden's number would move, and nothing in the UI would explain why.

The metric is called **Insektenwert**, and it stays insect-based. Birds are
counted alongside, as their own number. This is the same rule that governs
sources in this project: **things that mean different things do not overwrite
each other, they sit next to each other and are labelled.**

## Data Model

`insect_de` gains a `clade` column (`insect` | `bird`), defaulting to `insect`
so every existing row keeps its meaning without a data migration.

The table keeps its name. It now holds birds, which makes the name imprecise,
and renaming it was rejected on risk rather than taste: it is a shipped
catalogue table on a live volume, the migration machinery handles added columns
and not renames, and the exact shape of that gap — schema created fresh, old
table lingering with the data — is the failure this project has already hit
three times. An explicit `clade` column makes the semantics unambiguous where it
matters, which is at every read site. Recorded under Known Issues rather than
quietly accepted.

Bird counts go in a **new `partner_birds` table** rather than a clade column on
`partner_summary`. The insect score's queries then keep working untouched, which
is the difference between adding a number and silently changing every score
already shown. The insect aggregates gain `AND d.clade = 'insect'` so birds
cannot leak in — verified by a test that summarises before and after adding a
bird and asserts the insect total does not move.

The aggregates are the intersection of GloBI and the checklist, so they must be
rebuilt with `ingest.cli summarise` after this change — what CLAUDE.md already
says about them, and adding a clade is exactly the kind of change it means.

## Ingest

`BirdsDeSource` reuses `fetch_german_scientific_names(AVES_KEY)` — the same
facet trick Wave 2 used for insects, roughly 19 calls instead of 19,000. Species
only: a GloBI partner recorded as "Passeriformes" matched against "Germany has
Passeriformes" is vacuously true and would inflate every plant's count, the same
trap the insect checklist documents.

## Business Rules

- **A bird partner is counted only if the bird is on the German checklist**, the
  same rule insects already follow. A plant's partners in Chile are not a
  reason to plant it in Brandenburg.
- **The insect score reads `clade = 'insect'` and is numerically unchanged** by
  this feature. A test pins that.
- **Bird counts are shown, not scored.** What a good bird count is worth relative
  to a good insect count is a judgement this product has not made and should not
  imply by inventing a combined number.

## What the bird number is, and is not

Measured before shipping it, because the first UI draft read "58 Vogelarten"
beside *Bellis perennis* and that did not look like ecology:

- **99.7% of bird relations are `eatenBy`** — 97,999 rows against 266
  `visitedBy` and 29 `pollinatedBy`. The number counts birds recorded eating the
  plant, mostly fruit and seed, and the UI says so instead of implying a score.
- **Generalists dominate, in both clades.** Mallard, greylag goose and blackbird
  are each recorded on ~1,700 plants. That is the same shape as *Apis mellifera*
  on 1,067 plants, which the insect count already lives with — the median is 10
  plants per insect and 9 per bird. So this is not a bird-specific defect and
  not a reason to withhold the number; it is a reason to label it.
- **The top of the ranking is ecologically right**: *Sambucus nigra* 100,
  *Crataegus* 95, *Prunus spinosa* 87, *Juniperus communis* 86 — the classic
  German bird shrubs, in order. The signal is noisy and the ordering is real.

Every one of those top plants is woody, and Wave 4 hid woody plants from every
bed. That is the other half of this feature.

## Woody plants: the model question, answered by the user

The plan called for woody plants to get "a category with its own place", and the
obvious readings were a bed *type* or garden-level plantings. Both were wrong,
and the user said why:

> Im Endeffekt sind Beete ja nur markierte Bereiche in denen ich etwas pflanzen
> will […] ob dort ein Baum steht oder eine Blume ist erstmal egal. Eine Blume
> kann auch direkt an einem Baum gepflanzt werden… hat halt dann viel Schatten.

A bed is an area; what stands in it is a fact about the planting. So there is no
bed type and no second planting model. What actually follows from planting a
tree is spatial, and there are two consequences:

**It needs room.** The bed's polygon gives its area, so the honest question is
not "is this woody" but "does this fit". A plant too large is shown with what it
would take — `braucht ~79 m²` — rather than hidden. Same rule as everywhere else
here: name what you left out instead of dropping it quietly.

**It changes the light.** The shading model already describes obstacles as
vertical cylinders, which is the shape of a tree; it had simply never been told
about the ones the user plants. Planting one now recomputes the garden, and
removing it gives the light back.

Sizes are **estimated from height** — the catalogue has no crown width — and
marked as estimates. `Canopy.estimated` exists so a measured source can arrive
without changing callers.

### Presentation is not the model

Ranking woody plants into the one list did not work: they sorted below roughly
2,000 perennials, which is the same invisibility Wave 4 caused by excluding
them, only better argued. Verified in the running app — not one of the twenty
visible suggestions carried a size note.

So the answer is a second *list*, not a second model: `woody` beside `items`,
ordered by German animal partners rather than by site fit. Ordering it by fit
again put mistletoe and Ruscus at the top of every bed and left *Salix caprea*
below the cut. A shrub is planted for what visits it.

## Catalogue size

The wave plan asked for this to be measured against the 10 MB baseline rather
than assumed. Wave 6 took the shipped catalogue from **10 MB to 14.8 MB**:
vernacular names are the bulk of it, birds and their counts add ~0.3 MB. Still
far below the 93 MB that summarising avoids, and worth watching rather than
acting on.

## Known Issues

- `insect_de` holds birds. The name is now imprecise; `clade` carries the truth.
  A rename wants a table-level migration path that does not exist yet, and is
  not worth inventing under a live volume for a naming improvement.
- The bird count cannot distinguish seed dispersal from grazing, because GloBI's
  `eatenBy` does not. *Sambucus nigra* and *Bellis perennis* differ by a factor
  of two where the garden difference is larger than that.
- **A planting does not shade the bed it stands in.** It has no coordinates, so
  it is placed at the bed centroid — where the light is also sampled, which made
  every plant sit exactly on the sample point. Wave 7's drawing tool gives
  plantings a position and this exclusion goes with it.
- **The woody shortlist is Salix-heavy** — seven of eight entries are willows,
  because willows genuinely dominate German insect partner counts. Truthful and
  monotonous; a diversity constraint would help.
- **`height_max_m` is an upper bound**, so the room estimate is too: *Quercus
  robur* is reported as needing ~873 m², which is a 50 m specimen rather than a
  garden oak.

## Bugs

**The catalogue sync copied rows positionally.** `INSERT OR REPLACE INTO t
SELECT * FROM shipped.t` couples the shipped schema to the live one by column
order. Adding `insect_de.clade` made the shipped rows one value short and the
sync failed outright — caught here by a test, which is a first for this class of
bug in this project. A *dropped* column would have been worse: the counts would
have matched and every value landed one field to the left, silently. Sync now
names the intersection of both schemas explicitly.

**The suggestion list claimed woody plants were hidden while showing them.** The
sentence was hardcoded and went on asserting it after the user switched them on.
Found by reading the screen, not by a test; there is a test now.

**The ground under an obstacle counted as full sun.** The cast-shadow test
starts at the obstacle's centre and runs away from the sun, so a point directly
beneath it scored `along == 0` and fell through. A bed under a recorded tree
read Ellenberg 8. Pre-existing since Wave 3, found while making plantings cast
shade.

**Two light fixtures were geometrically degenerate**, and only passed because of
that bug: obstacles of radius 8 m placed 3 m from the bed enclosed it. The
south-versus-north test stopped meaning anything the moment footprints counted,
so the fixtures now put the obstacles outside the bed.

**Planting a tree did not recompute the light.** Every unit test of planted
shade called `recompute_light` itself and passed; the running app left the bed
at 12.6 hours with a willow in it. The invariant now belongs to the store, for
the same reason the light computation already did — it must hold whatever the
entry point.

**Then it recomputed to zero.** With shading wired up, one 2 m shrub took a
16 m² bed from 12.6 sun hours to 0.0 and Ellenberg 8 to 3, because the plant sat
on the light sample point. Both of these were visible only by clicking Pflanzen
and reading the bed label.

**"1 Art(en) gepflanzt"** — the German plural dodge, a fourth time, and a test
asserted the broken string.
