---
id: ninanatur-wave-6
title: "Wave 6: A catalogue you can actually browse"
initiative: ninanatur
initiative_version: 10
status: in_progress
depends_on: ninanatur-wave-5
demo_state: "A user finds a plant by its German name, filters by height and colour, clicks a month to see only what flowers then, and opens any species for a description and a photo"
created: 2026-08-28
hash: 3da710de
---

# Wave 6 — A catalogue you can actually browse

## Demo-State

A user finds a plant by its German name, filters by height and colour, clicks a
month to see only what flowers then, and opens any species for a description and
a photo.

## Why this before more drawing

The catalogue holds 3,087 usable species and the UI exposes them as a ranked list
of Latin binomials. Nobody browses that. Every drawing feature after this is
worth more once the plants behind it are findable and legible.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | german-names | 21-german-names | complete | — |
| 2 | species-info | 22-species-info | complete | — |
| 3 | catalogue-filters | 23-catalogue-filters | planned | 21 |
| 4 | month-suggestions | 24-month-suggestions | planned | 23 |
| 5 | woody-and-birds | 25-woody-and-birds | planned | — |

### 1 — german-names (#4)

GBIF carries vernacular names, checked before planning: 10–20 German names per
species, *including* spellings with and without umlauts — `Frühlings-Schlüsselblume`
and `Fruehlings-Schluesselblume` both appear. That is exactly what a search box
needs, and it arrives free.

One preferred name for display, all of them searchable. Search matches German and
scientific names alike; a user should never have to know that *Sal-Weide* is
*Salix caprea*.

### 2 — species-info (#5)

**API, not a crawler** — verified: `de.wikipedia.org/api/rest_v1/page/summary/…`
returns a summary and a thumbnail, and redirects the scientific name to the
German article (`Achillea millefolium` → *Gemeine Schafgarbe*). Content is
CC-BY-SA 4.0, so **attribution and a link back are required, not optional**.

**Fetched on demand and cached, not stored in the catalogue.** Three reasons, and
they settle the question asked:

- A live fetch on every view adds latency and an external dependency to a page
  that currently has neither.
- Baking summaries into the shipped catalogue makes it stale on a yearly cycle
  and inflates an image that just got trimmed to 10 MB.
- The cache belongs on the volume, not in the catalogue — same lifecycle split as
  gardens, for the same reason.

Falls back to English when there is no German article, and says which it showed.

### 3 — catalogue-filters (#6)

Height, colour, flowering window, growth form, nativeness — as filters over the
same ranking, with the rules already established: colour ranks rather than
excludes, unknown is never silently dropped, and every active filter is visible
and removable.

### 4 — month-suggestions (#1)

Clicking a month in the bloom year restricts suggestions to species flowering
then. This is the shortest path from *seeing a gap* to *fixing it*, and it is the
reason the timeline exists.

Wrapping intervals must be honoured here too — a November-to-March species
belongs in the March list.

### 5 — woody-and-birds (#7b)

Trees, shrubs and woody plants stop being a filtered-out nuisance and become a
category with its own place: they are the highest-value forage plants in the
catalogue. *Salix caprea* leads the whole database with 1,055 German partners,
and Wave 4 hides it from every bed.

Birds join insects as counted partners — GloBI already holds the relations, and
`insect_de` becomes an animal checklist with a group per clade.

## Risks

- Wikipedia titles are not stable identifiers. A cached miss must be retried on a
  schedule rather than remembered forever as "no article".
- Adding vernacular names and an animal checklist grows the shipped catalogue.
  Measure it against the 10 MB baseline rather than assuming.

## Open Research

None blocking. Both external sources were verified before this plan was written.

## Definition of done

Searching "Schlüsselblume" finds *Primula veris*; filtering to yellow flowers
under 50 cm narrows the list; clicking June shows only June bloomers; and any
species opens a description with its photo and a Wikipedia credit.
