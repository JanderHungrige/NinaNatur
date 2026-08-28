---
id: 10-web-client
title: Typed API Client Generated from OpenAPI
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-3
wave_status: active
depends_on: [09-garden-api]
relates: [11-garden-canvas, 06-plants-api]
source_files:
  - frontend/package.json
  - frontend/tsconfig.json
  - frontend/src/api/types.ts
  - frontend/src/api/client.ts
  - scripts/generate_openapi.py
routes: []
models: []
test_files:
  - frontend/src/api/client.test.ts
data_flow: reads-existing
last_synced: 2026-08-28
status: draft
phase: "1"
mdd_version: 11
tags: [typescript, openapi, client, contract, vite]
path: Frontend/Client
integration_contracts:
  - function: generate types from openapi.json
    when: any API route or schema changes
    note: types are generated, never hand-written — a hand-copied type drifts silently and the drift only shows up at runtime
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 10 — Typed API Client Generated from OpenAPI

## Purpose

One typed contract between frontend and backend, **generated** from FastAPI's
OpenAPI schema rather than written twice.

## Why generated

A hand-written TypeScript interface mirroring a Pydantic model is a second
definition of the same shape. It compiles fine while drifting from the API, and
the drift only surfaces at runtime as `undefined` where a field was renamed. The
generator makes drift a build failure instead.

```
FastAPI app  ->  scripts/generate_openapi.py  ->  frontend/openapi.json
                                                       |
                                    openapi-typescript  ->  src/api/types.ts
```

Regenerating is `npm run generate:api`. CI runs it and fails if the result
differs from what is committed, so a backend change that was not propagated
cannot merge.

## The client

A thin `fetch` wrapper over the generated types. It does three things the raw
`fetch` does not:

- **Throws on non-2xx**, carrying the API's `detail` message. A silently ignored
  422 is how a form ends up looking like it worked.
- **Distinguishes 404 from failure** where the caller cares — an unknown share
  token is a normal outcome, not an exception.
- **Types the response by route**, so a typo in a field name is a compile error.

## Business Rules

- **TypeScript strict, no `any`.** Project rule, and the whole point of generating.
- **The client never invents defaults.** A `null` from the API stays `null`; it
  is not turned into `0` or an empty string on the way in. Wave 2 and 3 both went
  to some trouble to make unknown distinguishable, and coercing it here would
  throw that away at the last step.
- **No secret ever reaches this code.** The share token is user-held, in the URL
  the user already has.

## Known Issues

(none yet)

## Bugs

(none yet)
