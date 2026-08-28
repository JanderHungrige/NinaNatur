---
id: ninanatur-wave-2
title: "Wave 2: The data layer answers questions"
initiative: ninanatur
initiative_version: 3
status: planned
depends_on: ninanatur-wave-1
demo_state: "GET /api/v1/plants with a bed's site conditions returns ranked species with a graded fit score, every trait value carrying its source"
created: 2026-08-27
hash: 6062423a
---

# Wave 2 — The data layer answers questions

## Demo-State

`GET /api/v1/plants` with a bed's site conditions returns ranked species with a
graded fit score, every trait value carrying its source.

*(This wave is not complete until this can be manually demonstrated against the
running app.)*

## Why now

The ingest pipeline already fills the database — 4,437 candidates, 3,087 of them
core-complete. What is missing is the read side. Until it exists, no UI wave can
be built against anything real.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | niche-fit | 03-niche-fit | planned | — |
| 2 | trait-resolve | 04-trait-resolve | planned | — |
| 3 | insect-checklist-de | 05-insect-checklist-de | planned | — |
| 4 | plants-api | 06-plants-api | planned | 03, 04, 05 |

### 1 — niche-fit

Ingest the EIVE `*.nw3` niche-width columns, then score how well a species fits a
bed's site vector: how centrally the bed sits within the species' niche on each
axis, combined across axes.

Graded, never a threshold. A species with a very wide niche does match widely —
that is ecologically true — but must never outrank one whose optimum is exactly
this bed. Getting that ordering right is the whole feature; a boolean "fits"
would make the generalists drown everything else.

The score must also be explainable per axis, because Wave 4 needs to say
"borderline on moisture" rather than showing a bare number.

### 2 — trait-resolve

`resolve_trait()` — read-time selection across sources, returning the value **and**
which source it came from, so the API can cite every number it reports.

Measured before designing: EIVE and GIFT currently overlap in zero trait keys, so
there is no arbitration to perform. The function exists for the third source, and
must not invent a policy it cannot yet justify. When two sources do disagree, both
values stay visible rather than one silently winning.

### 3 — insect-checklist-de

GloBI's 600,131 relations are worldwide — *Achillea millefolium* returns 1,504
flower visitors including New Zealand taxa. Counting them directly would rank a
plant by how well studied it is globally, not by what visits it in a German garden.

Fetch the insects actually recorded in Germany from the GBIF occurrence facet
(`taxonKey=216`, 11.6M records) and intersect. This generalises
`fetch_german_species_keys()` rather than adding a source — the plant version
already does exactly this with `taxonKey=7707728`.

Wave 5 consumes the result; building it here keeps Wave 5 to scoring alone.

### 4 — plants-api

FastAPI under `/api/v1/`, mounted on the Wave 1 app:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/plants` | search by site conditions and design filters, ranked by fit |
| GET | `/api/v1/plants/{taxon_id}` | one species with every trait and its provenance |

Rules carried from CLAUDE.md and Wave 1:

- A validation failure returns **422, never 500** — a `ValueError` backstop sits
  below the specific handlers so a new raise site downstream cannot escape as an
  opaque error with the reason only in the log.
- `/healthz` stays dependency-free even though a database now exists. That is what
  keeps a broken deploy distinguishable from a broken database.
- Colour filters **softly**: selecting a colour must not drop the 88% of species
  whose colour was never recorded. Unknown is returned as unknown, never guessed.
- The catalogue is all core-complete species. No curated subset, no availability
  filtering — that is Wave 6.

The response shape is what Waves 3 and 4 consume unchanged, so it is worth getting
right here rather than reshaping later.

## Out of scope

Scoring (Wave 5), garden geometry (Wave 3), shops (Wave 6), and the TypeScript
client — deferred to Wave 3, where a frontend exists to consume it. FastAPI's
generated OpenAPI schema is the contract until then.

## Open Research

None blocking. Both questions this wave was carrying are answered: fit uses
per-species niche width, and source priority needs no policy because the sources
do not overlap.

## Definition of done

`GET /api/v1/plants?light=7&moisture=4&…` returns ranked species against the real
database, each trait value naming its source, and the per-axis fit explanation is
present in the response.
