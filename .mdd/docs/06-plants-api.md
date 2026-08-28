---
id: 06-plants-api
title: Plants Search and Detail API
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-2
wave_status: complete
depends_on: [03-niche-fit, 04-trait-resolve, 05-insect-checklist-de]
relates: [02-web-shell]
source_files:
  - ninanatur/api/__init__.py
  - ninanatur/api/schemas.py
  - ninanatur/api/plants.py
  - ninanatur/api/search.py
  - ninanatur/api/deps.py
  - ninanatur/web/app.py
routes:
  - GET /api/v1/plants
  - GET /api/v1/plants/{taxon_id}
models:
  - taxon
  - trait
  - interaction
  - insect_de
test_files:
  - tests/test_plants_api.py
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [api, fastapi, search, ranking, provenance]
path: API/Plants
integration_contracts: []
satisfies_contracts:
  - from: 03-niche-fit
    function: score_species(site, species)
    when: ranking any species against a bed
    status: done
    verified_at: "ninanatur/api/search.py:149"
  - from: 04-trait-resolve
    function: resolve_trait(conn, taxon_id, trait_key)
    when: reading any trait value for display
    status: done
    verified_at: "ninanatur/api/plants.py:144"
  - from: 05-insect-checklist-de
    function: german_partner_counts(conn, taxon_id)
    when: reporting a plant's animal partners
    status: done
    verified_at: "ninanatur/api/plants.py:146"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 06 — Plants Search and Detail API

## Purpose

Expose the data layer: given a bed's site conditions, return species ranked by
fit, each value citing its source. This is the contract Waves 3 and 4 consume
unchanged, so its shape matters more than its implementation.

## API Endpoints

### `GET /api/v1/plants`

| Parameter | Type | Notes |
|---|---|---|
| `light`, `moisture`, `nutrients`, `reaction`, `temperature` | float 0–10 | at least one required |
| `height_min`, `height_max` | float, metres | optional |
| `flowering_month` | int 1–12 | species flowering in that month |
| `colour` | string | **soft** — ranks, never excludes |
| `limit`, `offset` | int | paging, limit ≤ 200 |

Response: `{ "total": N, "items": [PlantSummary] }`, ordered by fit descending.

### `GET /api/v1/plants/{taxon_id}`

Every trait with its provenance, plus German partner counts. 404 when unknown.

## Business Rules

- **A validation failure returns 422, never 500.** A `ValueError` backstop sits
  below the specific handlers so a new raise site downstream cannot escape as an
  opaque error with the reason only in the log.
- **At least one site axis is required.** A request with none would rank the
  entire catalogue by nothing and return an arbitrary 200.
- **Colour filters softly.** Selecting a colour must not drop the 88% of species
  whose colour was never recorded. Known non-matches rank below matches; unknowns
  sit between the two and are labelled unknown.
- **Unknown is transported as `null` with a reason**, never as an omitted field
  or a zero. The client must be able to distinguish "no data" from "zero".
- **Fit carries its explanation.** Every item includes the per-axis band, because
  Wave 4 needs to say "borderline on moisture" without recomputing anything.
- **`/healthz` stays dependency-free** even now that a database exists. That is
  what keeps a broken deploy distinguishable from a broken database.

## Data Flow

`GET /api/v1/plants` → load candidate niches in one query → `score_species` per
candidate → sort → resolve display traits for the page only → serialise.

Traits are resolved for the returned page rather than the whole catalogue:
scoring touches 4,437 species, but only `limit` of them are ever shown.

## Security

The only untrusted input is query parameters, all typed and range-validated by
Pydantic before reaching a query. Every SQL statement is parameterised. The API
is read-only — no endpoint in this feature writes.

## Known Issues

- Search scores all 4,437 candidates on every request — about 40 ms, fine now,
  but it will need a prepared index once beds are scored in bulk.
- The catalogue includes trees. A shady damp bed returns *Tsuga canadensis*
  before the woodland sedges, which is a correct fit and a poor suggestion.
  Growth form should become a default filter in Wave 3, where beds have a size.

## Bugs

(none yet)
