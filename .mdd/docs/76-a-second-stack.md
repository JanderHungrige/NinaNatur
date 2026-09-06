---
id: 76-a-second-stack
title: A Second Stack
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-18
wave_status: active
depends_on: [75-the-branch-that-goes-first]
relates: [75-the-branch-that-goes-first]
source_files:
  - deploy/compose.app.yml
  - deploy/.env.dev.example
  - deploy/SERVER-SETUP.md
routes: []
models: []
test_files:
  - tests/test_deploy_config.py
data_flow: greenfield
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [docker, compose, volumes, isolation, deployment]
path: Ops/Deployment
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The host steps themselves — copying .env.dev and starting the stack — are manual and cannot be done from a development machine."
---

# A Second Stack

Feature 1 of Wave 18. Almost nothing needed writing: `compose.app.yml` was
already parameterised for two environments and `.env.dev.example` was already
complete. What was missing was the proof that they are actually separate, and
the runbook step that makes somebody check.

## Proven, not assumed

Both stacks were started locally from the same image on 2026-09-06:

| | |
|---|---|
| Garden created on stack A | `200` on A |
| Same garden asked for on stack B | **`404`** |
| `docker volume ls` | `ninanatur-prod_ninanatur-data` and `ninanatur-dev_ninanatur-data` |
| Catalogue on both | 4,384 species matching the same filter |

The last row is the interesting one. The two volumes are empty and separate, yet
both stacks answer with a full catalogue — because the catalogue ships in the
image and seeds each empty volume independently, which is the arrangement
CLAUDE.md describes and this is it working. The dev container's log:

```
catalogue synced: {'taxon': 8939, 'trait': 84217, 'partner_summary': 6382, ...}
```

**That is also the fresh-empty-volume check** CLAUDE.md asks to be done by hand —
the state a new deployment starts in, and the one a test double never reproduces.
The dev stack is that state every time it is created, which makes this wave the
first arrangement where the check happens as a matter of course rather than as a
discipline.

## Why the runbook now contains a curl

Because the failure is silent. A shared volume does not error — it means the
preview and the live site are one database, and the first thing anybody notices
is a migration tested against real gardens. So `SERVER-SETUP.md` carries the
three commands that would catch it, to be run once on the host: two volumes in
`docker volume ls`, and a garden made on 4001 that must answer `404` on 4000.
