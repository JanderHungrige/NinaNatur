---
id: ninanatur-wave-1
title: "Wave 1: Branded shell, online and self-updating"
initiative: ninanatur
initiative_version: 2
status: complete
depends_on: ""
demo_state: "ninanatur.w3rth.de serves a branded NinaNatur page, and a push to main replaces it automatically within a minute"
created: 2026-08-27
hash: edc6d384
---

# Wave 1 — Branded shell, online and self-updating

## Why this first

The deployment path is the part most likely to surprise us, and the part every
later wave depends on. Getting a trivial page through the whole chain — build,
registry, cron, proxy, TLS — proves the pipeline while there is nothing complex
to confuse the diagnosis. Every wave after this one ships by pushing to a branch.

## Scope

**In:**
- NinaNatur name and logo (an NN mark), rendered by a minimal app
- Dockerfile producing a small production image
- GitHub Actions workflow: build on push, push to GHCR, no SSH into the host
- `deploy/` — compose file, env-file templates, `auto-deploy.sh`, crontab example
- Host setup documentation for `ninanatur.w3rth.de` → `172.17.0.1:4000`
- A health endpoint the cron and the proxy can both check

**Out:** plant data, API, garden plan, anything from the ingest layer. This wave
deliberately ships a page with no product logic in it.

## Deployment shape

Mirrors 3dmap and BattleFuel so the host runs one familiar pattern:

```
push to main            -> GH Actions -> ghcr.io/janderhungrige/ninanatur:main
push to dev-deployment  -> GH Actions -> ghcr.io/janderhungrige/ninanatur:dev

host cron (every minute) -> deploy/auto-deploy.sh <env-file>
                         -> docker compose pull + up -d (no-op unless digest changed)

Nginx Proxy Manager: ninanatur.w3rth.de -> 172.17.0.1:4000  (prod)
                     dev host           -> 172.17.0.1:4001  (dev)
```

`172.17.0.1` is the Docker bridge gateway, so the proxy container reaches the
app published on the host's port rather than needing a shared network.

## Blocks

| Block | End-state | Verify |
|---|---|---|
| 1 — App shell | A minimal app serves the branded page and `/healthz` locally | `curl localhost:4000/healthz` returns 200 |
| 2 — Logo | An NN mark renders as inline SVG, correct in light and dark | visual check at both themes |
| 3 — Dockerfile | `docker build` produces a running image | `docker run -p 4000:4000` serves the page |
| 4 — CI | Push builds and pushes to GHCR under both tags | the run is green and the package appears |
| 5 — Deploy files | compose, env templates, auto-deploy.sh, crontab | `auto-deploy.sh` is idempotent on an unchanged digest |
| 6 — Host + proxy | The domain resolves over TLS to the container | `curl https://ninanatur.w3rth.de/healthz` |

Blocks 1–5 are ours. Block 6 needs host access — it produces a runbook the
operator follows, not code.

## Risks

- **GHCR visibility.** A private package needs the host logged in to GHCR once.
  The runbook must say so, or the cron fails silently every minute.
- **Cron overlap.** Two runs racing the same pull corrupt the containerd content
  store — 3dmap solved this with a global `flock`; carry that over rather than
  rediscovering it.
- **Port collision on 4000.** Confirm nothing else on the host publishes it.

## Definition of done

A commit pushed to `main` is live at `https://ninanatur.w3rth.de` within roughly
a minute, with no manual step on the host.
