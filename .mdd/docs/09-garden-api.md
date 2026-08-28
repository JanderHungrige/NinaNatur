---
id: 09-garden-api
title: Garden API
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-3
wave_status: complete
depends_on: [07-solar-geometry, 08-garden-model]
relates: [06-plants-api, 10-web-client]
source_files:
  - ninanatur/api/gardens.py
  - ninanatur/api/schemas.py
  - ninanatur/web/app.py
routes:
  - POST /api/v1/gardens
  - GET /api/v1/gardens/{token}
  - POST /api/v1/gardens/{token}/beds
  - POST /api/v1/gardens/{token}/obstacles
  - POST /api/v1/gardens/{token}/recompute
  - DELETE /api/v1/gardens/{token}
models:
  - garden
  - bed
  - obstacle
test_files:
  - tests/test_gardens_api.py
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [api, fastapi, gardens, share-token, validation]
path: API/Gardens
integration_contracts: []
satisfies_contracts:
  - from: 08-garden-model
    function: create_garden(conn, ...)
    when: any garden is created through the API
    status: done
    verified_at: "ninanatur/api/gardens.py:82"
  - from: 07-solar-geometry
    function: bed_light_value(location, bed, obstacles)
    when: a garden's obstacles or beds change
    status: done
    verified_at: "ninanatur/garden/store.py:148"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 09 — Garden API

## Purpose

CRUD for garden plans, addressed by share token. Everything Wave 3's canvas needs
and nothing more.

## Addressing

**Gardens are addressed by token, never by id.** The numeric `garden_id` never
appears in a URL. An id is enumerable; the token is the capability, and mixing
the two would give away by incrementing what the token exists to protect.

An unknown token returns **404, not 403** — telling an attacker that a token
exists but is not theirs is exactly the information the token is meant to hide.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/gardens` | create; returns the token once |
| GET | `/api/v1/gardens/{token}` | the whole plan |
| POST | `/api/v1/gardens/{token}/beds` | add a bed |
| POST | `/api/v1/gardens/{token}/obstacles` | add an obstacle, then recompute |
| POST | `/api/v1/gardens/{token}/recompute` | recompute light explicitly |
| DELETE | `/api/v1/gardens/{token}` | delete the plan and everything in it |

## Business Rules

- **Adding an obstacle recomputes light automatically.** Requiring a second call
  would leave a plan showing values that no longer match its own obstacles —
  and that inconsistency would be invisible.
- **Validation failures are 422**, via the same `ValueError` backstop as Wave 2.
  `PolygonError`, `SoilTypeError` and `MoistureError` all subclass `ValueError`,
  so they surface with their reason instead of as a 500.
- **Latitude and longitude are range-checked** before they reach the solar code,
  which would otherwise happily compute a sun path for latitude 500.
- **Unknown is `null` with the field present** — a bed whose light has not been
  computed reports `null`, never `0`.
- **`/healthz` still touches nothing.**

## Security

The share token is the only access control, so it is in the path and never in a
query string — query strings end up in server logs, browser history and referer
headers. Rate limiting is out of scope here and noted as a known gap.

## Known Issues

- **No rate limiting.** The share token is 32 bytes of entropy so brute force is
  not a realistic threat, but garden creation is unauthenticated and unbounded —
  anyone can fill the database. Worth a limiter before this is public.
- Beds and obstacles can be added but not yet edited or deleted individually;
  the canvas will need `PATCH` and `DELETE` on both.

## Bugs

(none yet)
