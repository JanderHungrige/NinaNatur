---
id: 02-web-shell
title: Web Shell, Container Image and Self-Updating Deploy
edition: MDD
depends_on: []
relates: [01-trait-ingest]
source_files:
  - ninanatur/web/app.py
  - ninanatur/web/static/index.html
  - ninanatur/web/static/styles.css
  - ninanatur/web/static/logo.svg
  - Dockerfile
  - .github/workflows/deploy.yml
  - deploy/compose.app.yml
  - deploy/auto-deploy.sh
  - deploy/install-cron.sh
  - deploy/SERVER-SETUP.md
routes:
  - GET /
  - GET /healthz
  - GET /static/{path}
models: []
test_files:
  - tests/test_web.py
data_flow: greenfield
last_synced: 2026-08-27
status: complete
phase: all
mdd_version: 11
tags: [web, fastapi, branding, deployment, ghcr, cron, healthcheck]
path: Platform/Deploy
integration_contracts:
  - function: GET /healthz
    when: any deploy or proxy needs to know the app is alive
    note: must stay dependency-free — it is the only signal that separates a broken deploy from a broken backing service
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects:
  - /opt/3dmap2
  - /opt/battlefuel
  - /opt/funding-tender-tracker
---

# 02 — Web Shell, Container Image and Self-Updating Deploy

## Purpose

Deliver the smallest possible page through the entire deployment chain — build,
registry, cron, proxy, TLS — so the pipeline is proven while there is nothing
complex to confuse a diagnosis. Every later wave ships by pushing to a branch.

## Architecture

```
push main           -> GH Actions (test -> build) -> ghcr.io/janderhungrige/ninanatur:main
push dev-deployment ->                             -> :dev

root cron, offset :15 -> deploy/auto-deploy.sh <env-file>
                      -> docker compose pull + up -d   (no-op unless digest changed)

Nginx Proxy Manager: ninanatur.w3rth.de -> 172.17.0.1:4000
```

CI never SSHes into the host. `172.17.0.1` is the Docker bridge gateway, so the
proxy reaches the published host port without a shared network.

## API Endpoints

| Method | Path | Response |
|---|---|---|
| GET | `/healthz` | `{"status":"ok","service":"ninanatur","version":"0.1.0"}` |
| GET | `/` | the branded page |
| GET | `/static/*` | stylesheet, logo |

## Business Rules

- **`/healthz` touches nothing.** Once Wave 2 adds a database, a health endpoint
  that queried it would make a broken deploy and a broken database look identical.
- **The deploy is pull-based.** The host decides when to update; CI only publishes.
  No CI credentials ever reach the host.
- **Cron runs staggered.** Each project's `auto-deploy.sh` holds its own `flock`,
  which guards only against itself. The offsets (`:00` battlefuel, `:15` NinaNatur,
  `:30` funding-tender-tracker, `:45` 3dmap2) are what keep four deploys from
  pulling from GHCR in the same second.
- **Package discovery is explicit.** `[tool.setuptools.packages.find]` names
  `ninanatur*`; flat-layout auto-discovery aborts on the second top-level
  directory (`deploy/`).

## Security

The app serves static content and one JSON endpoint; it accepts no user input and
holds no credentials. The GHCR package is public, verified by an anonymous
manifest pull, so no registry credentials live on the host either. The container
runs as an unprivileged user (uid 10001).

Host operators are in the `docker` group, which is effectively root-equivalent —
an accepted trade for unattended deploys, documented in `deploy/SERVER-SETUP.md`.

## Known Issues

None outstanding. Docker became available on the dev machine on 2026-08-28 and
the image was verified locally end to end — build, non-root start (uid 10001),
`HEALTHCHECK` reporting `healthy`, and the full stack through `deploy/compose.app.yml`.

## Bugs

Fixed during this wave:

- **Flat-layout package discovery aborted the CI install.** setuptools refused to
  build with both `deploy/` and `ninanatur/` present. Would have passed in Docker
  by accident, since the image copies neither `deploy/` nor the tests.
- **`curl -s` used for health verification.** Prints nothing on a refused
  connection, which is indistinguishable from an empty 200 — the one thing a
  health check must never be ambiguous about.
- **Runbook assumed docker without sudo and a user crontab.** Both wrong for this
  host; corrected to match the three deploys already running on it.
