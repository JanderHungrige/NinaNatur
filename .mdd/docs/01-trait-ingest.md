---
id: 01-trait-ingest
title: Trait Ingest Pipeline & Coverage Report
edition: MDD
depends_on: []
relates: []
source_files:
  - ninanatur/ingest/db.py
  - ninanatur/ingest/provenance.py
  - ninanatur/ingest/names.py
  - ninanatur/ingest/http.py
  - ninanatur/ingest/sources/base.py
  - ninanatur/ingest/sources/gbif.py
  - ninanatur/ingest/sources/eive.py
  - ninanatur/ingest/sources/gift.py
  - ninanatur/ingest/sources/globi.py
  - ninanatur/ingest/coverage.py
  - ninanatur/ingest/cli.py
routes: []
models:
  - taxon
  - taxon_name
  - trait
  - interaction
  - source_run
test_files:
  - tests/test_provenance.py
  - tests/test_coverage.py
  - tests/test_eive.py
  - tests/test_names.py
data_flow: greenfield
last_synced: 2026-08-27
status: draft
phase: "1"
mdd_version: 11
tags: [ingest, traits, provenance, gbif, eive, gift, globi, coverage, sqlite]
path: Data/Ingest
integration_contracts:
  - function: upsert_trait(conn, taxon_id, key, value, source)
    when: any source writes a trait value
    note: every trait write must carry source, license and confidence — no bare inserts
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "flower_colour covers only ~13% of candidates (590 taxa) — GIFT holds the trait for 1810 taxa worldwide. Blocks the bloom-colour simulation until a second source is added."
  - "GloBI interaction records are global, not German. Achillea millefolium returns 1504 flower visitors including New Zealand taxa; the raw count overstates German relevance and must be intersected with a German insect checklist before it drives a score."
  - "pollination_syndrome covers ~27% — not on the critical path, since GloBI supplies counted relations directly, which is the harder evidence."
  - "One candidate name remains unresolvable (two accepted homonyms); recorded as AMBIGUOUS in taxon_name."
sister_projects: []
---

# 01 — Trait Ingest Pipeline & Coverage Report

## Purpose

Build a local SQLite trait database for German garden-relevant plants from open,
licensed sources — with per-value provenance — and report how much of the field
set the app actually needs is covered. The coverage number decides whether the
open-data route carries the product or whether a licensed source is required.

## Architecture

```
Zenodo (EIVE xlsx) ─┐
GBIF species API ───┤
GIFT API ───────────┼──> source adapters ──> provenance layer ──> SQLite
GloBI API ──────────┘      (normalise)        (source/license)      │
                                                                     v
                                                         coverage report (CLI)
```

Each source is an adapter implementing a single `run(conn)` method. Adapters
never write to `trait` directly — they call `upsert_trait()`, which is the only
write path and stamps `source`, `license`, `confidence` and `retrieved_at`.

Name resolution is the join key problem: every source uses its own spelling.
All names pass through `names.resolve()`, which calls the GBIF match API and
caches the result in `taxon_name`, so a taxon is only ever resolved once.

## Data Model

**taxon** — canonical taxa, keyed by GBIF usageKey
`taxon_id INTEGER PK, scientific_name TEXT, canonical_name TEXT UNIQUE,
 rank TEXT, status TEXT, family TEXT, genus TEXT, accepted_id INTEGER`

**taxon_name** — resolution cache (raw name → taxon)
`raw_name TEXT, source TEXT, taxon_id INTEGER, match_type TEXT,
 confidence INTEGER, PRIMARY KEY (raw_name, source)`

**trait** — one row per (taxon, trait, source); conflicting sources coexist
`taxon_id INTEGER, trait_key TEXT, value_num REAL, value_text TEXT, unit TEXT,
 source TEXT, license TEXT, confidence REAL, retrieved_at TEXT,
 PRIMARY KEY (taxon_id, trait_key, source)`

**interaction** — plant↔animal relations for the insect score
`taxon_id INTEGER, partner_name TEXT, partner_group TEXT, interaction_type TEXT,
 source TEXT, license TEXT, n_records INTEGER,
 PRIMARY KEY (taxon_id, partner_name, interaction_type, source)`

**source_run** — audit trail per ingest run
`source TEXT, started_at TEXT, finished_at TEXT, rows INTEGER, status TEXT, note TEXT`

### Canonical trait keys

`ellenberg_l` (light), `ellenberg_m` (moisture), `ellenberg_n` (nutrients),
`ellenberg_r` (reaction/pH), `ellenberg_t` (temperature) — 0–10 continuous;
`height_max_m`, `flowering_start_month`, `flowering_end_month` (1–12),
`flower_colour`, `growth_form`, `life_form`, `lifecycle`,
`pollination_syndrome`, `occurs_de` (boolean).

## Business Rules

- **Provenance is mandatory.** `upsert_trait()` rejects a write with an empty
  `source` or `license`. There is no code path that inserts into `trait` directly.
- **Sources do not overwrite each other.** The primary key includes `source`, so
  two sources disagreeing on height both persist. Resolution to a single value is
  a later read-time concern (a `resolve_trait()` priority function), not an
  ingest-time one — the raw disagreement stays visible.
- **Name resolution is cached and never silently guesses.** A GBIF match below
  confidence 90 or of type `NONE`/`HIGHERRANK` is stored but not used to attach
  traits; those rows surface in the coverage report as unresolved.
- **Every run is resumable.** Re-running a source is idempotent (upsert), and
  network fetches are cached to `data/cache/` so a rerun costs no API calls.
- **Rate limiting.** GloBI and GIFT are queried per taxon; requests are serialised
  with a delay and retried with backoff. A source that fails mid-run records
  `status='partial'` in `source_run` rather than rolling back.

## Coverage Definition

Candidate set = EIVE taxa whose GBIF distribution includes Germany.

- **Core complete** — has light, moisture, nutrients, height, and both flowering
  bounds. This is the minimum for bed matching plus the bloom timeline.
- **Full** — core complete plus flower colour plus at least one interaction record.
  This is what the colour simulation and the insect score need.

Coverage is reported per trait key and for both thresholds.

## Data Flow

Greenfield — no existing code analysed.

## Dependencies

None. This is the foundation feature.

## Security

The pipeline makes outbound network calls to four public APIs and reads the files
it downloads. Untrusted input is the API response body: taxon names from GloBI and
GIFT are written into SQLite via parameterised statements only, never string
interpolation. Downloaded archives are read with `openpyxl`/`csv` — no pickle, no
eval, no archive extraction to arbitrary paths. No credentials are involved; none
of the four sources requires a key.

## Known Issues

Measured on the first full run (2026-08-27, candidate set 4425 taxa):

| Gap | Extent | Consequence |
|---|---|---|
| `flower_colour` | 590 taxa (~13%) | The bloom-colour simulation cannot run on the open data alone. Candidate second sources: Wikidata, structured German determination floras, or hand-curating the ~600 horticulturally relevant species. |
| GloBI geographic bias | all interaction rows | Records are worldwide. Counting them directly would rank a plant by how well-studied it is globally, not by what visits it in a German garden. Intersect with a German insect checklist before scoring. |
| `pollination_syndrome` | ~27% | Not blocking — GloBI's counted relations are stronger evidence for the same question. |
| Ambiguous names | 1 taxon | Two accepted homonyms; recorded as `AMBIGUOUS` rather than resolved arbitrarily. |

### Resolved during the first run

- **GIFT truncates lists at 10,000 rows** without signalling it. Flowering-start
  data silently arrived at exactly half its documented size until paging was
  added. Treat every undocumented list endpoint as truncating.
- **`canonical_name UNIQUE` is invalid for a taxonomic backbone.** 198 of 8939
  German candidate keys share a name with another key, mostly ACCEPTED/DOUBTFUL
  pairs. See the fix commit for why dropping the constraint alone would have
  replaced a crash with a silent wrong-taxon attachment.

## Bugs

(none yet)
