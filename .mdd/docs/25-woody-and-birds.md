---
id: 25-woody-and-birds
title: Birds Count Too — Separately
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-6
wave_status: active
depends_on: [17-insect-groups]
relates: [18-insect-score, 16-nativeness]
source_files:
  - ninanatur/ingest/db.py
  - ninanatur/ingest/sources/birds_de.py
  - ninanatur/ingest/sources/gbif.py
  - ninanatur/data/interactions.py
  - ninanatur/ingest/catalogue.py
routes:
  - GET /api/v1/plants/{taxon_id}
test_files:
  - tests/test_birds_de.py
  - tests/test_partner_clades.py
data_flow: mixed
last_synced: 2026-08-28
status: draft
phase: "1"
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

Every one of those top plants is woody, and Wave 4 hides woody plants from every
bed by default. The bird number is therefore mostly invisible where it matters
until woody plants get somewhere to live.

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
- Woody plants still have no place of their own. The half of this feature that
  would give them one is a data-model question — bed-level or garden-level
  plantings — and is deliberately not answered here.

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
