---
id: ninanatur-release
title: Release NinaNatur — dev-deployment to main
type: ops
platform: github-actions
environments: [staging, production]
deployment_strategy:
  order: sequential
  gate: health_check
  on_gate_failure: stop
  rollback_on_failure: false
regions:
  - slug: preview
    host: ninanatur-dev.w3rth.de
    platform: github-actions
    deploy_order: 1
    role: canary
  - slug: production
    host: ninanatur.w3rth.de
    platform: github-actions
    deploy_order: 2
    role: primary
services:
  - slug: ninanatur
    image: ghcr.io/janderhungrige/ninanatur:main
    port: 4000
    # $HOST is the region's host.
    health_check: "curl -fsS --max-time 10 https://$HOST/healthz | python3 -c 'import json, sys; sys.exit(0 if json.load(sys.stdin)[\"status\"] == \"ok\" else 1)'"
    regions:
      preview:
        image: ghcr.io/janderhungrige/ninanatur:dev
        status: healthy
        last_checked: 2026-09-15
      production:
        image: ghcr.io/janderhungrige/ninanatur:main
        status: healthy
        last_checked: 2026-09-15
status: draft
last_synced: 2026-09-15
mdd_version: 11
tags: [release, deploy, github-actions, ghcr, cron, smoke-test, playwright, production]
known_issues:
  - "A roll restarts the single container: during Wave 23's stage 3 roll (2026-09-14) production answered one poll with 502 before V0.20.182 came up. healthz.yml tries three times a minute apart for the same reason."
  - "CI finishes before the host rolls its image, so no CI job can test the build that just went out. The smoke test is a manual gate against the preview, before the merge (the owner's decision, 2026-09-14)."
  - "The smoke test makes and deletes a garden of its own. Against production it would write to live data, so it is never run there."
  - "After a lockfile change, Dependabot's dynamic update runs carry the same commit as build-and-push (2026-09-14): watch build-and-push by name, not every run on the SHA."
  - "A docs-only merge (.mdd/**, deploy/**, **.md) runs no CI, so dev-deployment's head may have no build-and-push run of its own; step 2 checks that nothing the image is built from changed since the last green run."
---

# Release NinaNatur — dev-deployment to main

## Overview

What goes live is what was looked at. CLAUDE.md's *Which branch goes where* has
every wave stage merged into `dev-deployment` and looked at on the preview first,
and `main` merged from `dev-deployment` — never from a feature branch. This
runbook is that release, step by step:

- the preview's build and its CI
- the workspace's smoke test as the gate
- the merge
- the watch until production serves what the preview served

It follows Wave 23's stage 3 release (2026-09-14, V0.20.182).

## Services & Ports

| Service | Image | Port on the host | Health endpoint |
|---|---|---|---|
| ninanatur, preview | `ghcr.io/janderhungrige/ninanatur:dev` | `172.17.0.1:4001` | `https://ninanatur-dev.w3rth.de/healthz` (`environment: dev`) |
| ninanatur, production | `ghcr.io/janderhungrige/ninanatur:main` | `172.17.0.1:4000` | `https://ninanatur.w3rth.de/healthz` (`environment: prod`) |

One container per stack: FastAPI serving the API and the built frontend.

- Every image is also tagged with its commit SHA.
- On the host, the image a stack ran before is kept as `:<tag>-previous`.
- `/healthz` names the version, `V0.<highest completed wave>.<merges>`, which CI
  derives.

## Environment Targets

- **Preview** (`dev-deployment` → `:dev` → dev stack): the staging environment
  every wave stage is looked at on. Its gardens are test data; the smoke test
  makes and deletes its own there.
- **Production** (`main` → `:main` → prod stack): live gardens on a named volume.
  No step of this runbook writes to it.
- Nginx Proxy Manager terminates TLS for both domains (`deploy/SERVER-SETUP.md`,
  §5).

## Webhooks & Triggers

- **No webhook.** A push to `dev-deployment` or `main` runs
  `.github/workflows/deploy.yml` (*build-and-push*).
  - It runs the tests first: security gates, ruff, mypy, pytest, pip-audit, the
    frontend's npm ci, audit, tsc and vitest, and the API types.
  - Then it builds and pushes the image.
  - A push touching only `.mdd/**`, `deploy/**` or `**.md` runs nothing.
- **The host polls.** Root's crontab runs `deploy/roll-all.sh` every minute
  (NinaNatur's slot is :15), production first. `deploy/auto-deploy.sh` then:
  - pulls the tag and keeps the running image as `:<tag>-previous`
  - gives the new container 150 s to report healthy
  - rolls back one that does not, and remembers it in `deploy/.state/<env>.bad`
  - logs every roll by digest in `deploy/.state/deploy.log`
- **From outside**, `.github/workflows/healthz.yml` asks both stacks at :07 and
  :37 past the hour.
- **The gate** is run by hand: `npm run test:e2e` in `frontend/` (Playwright
  1.63.0 with Chromium; `npx playwright install chromium` once per machine).

## Credentials & API Keys

| Credential | Env var or login | Where stored |
|---|---|---|
| Push to the repository | git credentials | the releasing machine |
| Read CI runs | `gh auth login`, or `GH_TOKEN` | the releasing machine |
| Push images to GHCR | `GITHUB_TOKEN` | provided to each Actions run |
| Pull images on the host | none for the public package; `docker login ghcr.io` if it turns private | the host's docker config |
| Stack settings | `deploy/.env.prod`, `deploy/.env.dev` | the host only, never committed |
| The smoke test's garden token | made per run, never stored | the test's own process |

**Never include actual values — env var names only.**

## MCP Servers

(none)

## Deployment Procedure

Run from the repository root, in one shell session: step 6 sets `BEFORE`, and
step 9 reads it. Commands that change directory run in a subshell.

```bash
# Step 1 (dev-deployment carries the release, and main has nothing it lacks)
# Action:
git fetch origin && git log --oneline --first-parent origin/main..origin/dev-deployment
# Verify:
test -n "$(git rev-list origin/main..origin/dev-deployment)" && test -z "$(git rev-list origin/dev-deployment..origin/main)"
```

Every merge on that list has been looked at on the preview. One that has not is
not part of this release.

```bash
# Step 2 (the preview's build passed CI, and nothing it is built from changed since)
# Action:
gh run list --branch dev-deployment --workflow build-and-push --limit 5
# Verify:
sha=$(gh run list --branch dev-deployment --workflow build-and-push --limit 1 --json headSha,conclusion --jq '.[] | select(.conclusion == "success") | .headSha') \
  && test -n "$sha" \
  && git diff --quiet "$sha" origin/dev-deployment -- . ':(exclude).mdd' ':(exclude)deploy' ':(exclude,glob)**/*.md'
```

```bash
# Step 3 (the preview is up)
# Action:
curl -i --max-time 10 https://ninanatur-dev.w3rth.de/healthz
# Verify:
curl -fsS --max-time 10 https://ninanatur-dev.w3rth.de/healthz | python3 -c 'import json, sys; h = json.load(sys.stdin); sys.exit(0 if h["status"] == "ok" and h["environment"] == "dev" else 1)'
```

```bash
# Step 4 (gate: the workspace's smoke test on the preview)
# Action and verify: exits 0 when both windows pass
(cd frontend && env -u SMOKE_BASE_URL npm run test:e2e)
```

The test runs at 1280×720 and 375×812 on a garden of its own. It chooses the bed,
plants a species and finds its patch on the plan. At every step the page must
not scroll or grow taller than the window, and the plan must keep 40 % of the
window's height. The test deletes its garden at the end (204). A failure here
stops the release.

```bash
# Step 5 (the plan file was never committed)
# Action:
git log --all --oneline -- '.mdd/plans/01-*'
# Verify:
test -z "$(git log --all --oneline -- '.mdd/plans/01-*')"
```

```bash
# Step 6 (merge dev-deployment into main)
# Action:
BEFORE=$(curl -fsS --max-time 10 https://ninanatur.w3rth.de/healthz | python3 -c 'import json, sys; print(json.load(sys.stdin)["version"])')
git checkout main && git merge --ff-only origin/main \
  && git merge --no-ff origin/dev-deployment -m "Merge from dev-deployment: <what the release carries>" \
  && git push origin main
# Verify:
git fetch origin && test "$(git rev-parse origin/main)" = "$(git rev-parse main)" && git merge-base --is-ancestor origin/dev-deployment origin/main
```

```bash
# Step 7 (dev-deployment back to main)
# Action:
git checkout dev-deployment && git merge --ff-only main && git push origin dev-deployment
# Verify:
git fetch origin && test "$(git rev-parse origin/dev-deployment)" = "$(git rev-parse origin/main)"
```

```bash
# Step 8 (CI on main passed for the release merge; the run appears a few seconds after the push)
# Action:
gh run watch "$(gh run list --branch main --workflow build-and-push --limit 5 --json headSha,databaseId --jq ".[] | select(.headSha == \"$(git rev-parse origin/main)\") | .databaseId" | head -1)"
# Verify:
gh run list --branch main --workflow build-and-push --limit 5 --json headSha,conclusion --jq ".[] | select(.headSha == \"$(git rev-parse origin/main)\") | .conclusion" | grep -qx success
```

```bash
# Step 9 (production serves what the preview served, as a newer version)
# Action: wait for the host's tick, plus up to 150 s of health wait
assets() { curl -fsS --max-time 10 "https://$1/" | grep -o 'index-[A-Za-z0-9_-]*\.\(css\|js\)' | sort; }
version() { curl -fsS --max-time 10 "https://$1/healthz" | python3 -c 'import json, sys; h = json.load(sys.stdin); print(h["version"] if h["status"] == "ok" else "")'; }
for i in $(seq 20); do [ "$(version ninanatur.w3rth.de)" != "$BEFORE" ] && break; sleep 30; done
# Verify:
test -n "$(version ninanatur.w3rth.de)" && test "$(version ninanatur.w3rth.de)" != "$BEFORE" && test "$(assets ninanatur.w3rth.de)" = "$(assets ninanatur-dev.w3rth.de)"
```

A 502 during the roll is the container restarting, not an outage.

```bash
# Step 10 (record the release)
# Action: a progress entry in the wave file naming the version, the merge and the
# assets production serves; commit it on the wave's branch, and merge that branch
# into dev-deployment (docs only, so CI runs nothing).
# Verify (on the wave's branch, after pushing):
git fetch origin && git merge-base --is-ancestor HEAD origin/dev-deployment
```

## Rollback Plan

**A build that does not start healthy** needs no manual rollback. Within its
150 s, `deploy/auto-deploy.sh`:

- rolls the stack back to `:main-previous`
- writes the image id to `deploy/.state/prod.bad`, so the next tick does not roll
  it forward again
- logs both

To see what happened, on the host in `/opt/ninanatur`:

```bash
tail deploy/.state/deploy.log
docker image ls ghcr.io/janderhungrige/ninanatur
docker compose --env-file deploy/.env.prod -f deploy/compose.app.yml logs --tail=50 app
```

Fix forward on a feature branch and release again through this runbook. Remove
the mark with `sudo rm deploy/.state/prod.bad` only when that same build should
be tried again.

**A build that runs but is wrong** (healthy, with a feature broken): revert the
release merge on `main`, so that CI builds a `:main` image without it.

```bash
git fetch origin && git checkout main && git merge --ff-only origin/main
# The last release merge on main — set RELEASE_MERGE to another one's SHA if that is the one to take back.
RELEASE_MERGE=$(git log --first-parent --merges -1 --format=%H --grep '^Merge from dev-deployment' origin/main)
git show --no-patch --oneline "$RELEASE_MERGE"
git revert -m 1 --no-edit "$RELEASE_MERGE"
git push origin main
```

After the revert:

1. Run step 7, so the preview stops showing what was taken back.
2. Run steps 8 and 9 for the revert. Production then serves the assets of the
   build before the release, and so does the preview.
3. The release's commits stay in the history. To release them again later,
   revert the revert on the feature branch that fixes them. Otherwise git treats
   them as already merged.

**Data survives both kinds of rollback.**

- Gardens live on the named volume and stay through any roll.
- The catalogue ships in the image and syncs to its own build stamp at startup.
  It upserts rows and deletes none, so a rollback does not take a garden with it
  (CLAUDE.md, *Catalogue vs. user data*).
- A release that changed the database schema needs its own check before rolling
  back past it: whether the previous image can read what the new one wrote.
