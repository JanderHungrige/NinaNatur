---
id: ninanatur-wave-18
title: "Wave 18: A place to look before it is live"
initiative: ninanatur
initiative_version: 20
status: planned
depends_on: ninanatur-wave-17
demo_state: "Ein Merge auf dev-deployment erscheint binnen einer Minute unter einer eigenen Adresse auf Port 4001, mit eigener Datenbank und einem Banner, das unübersehbar Vorschau sagt. Erst was dort in Ordnung ist, geht auf main — und main deployt weiter wie bisher, ohne dass sich für die Produktion irgendetwas ändert."
created: 2026-09-04
hash: 250d7ea2
---

# Wave 18: A place to look before it is live

## Demo-State

Ein Merge auf `dev-deployment` erscheint binnen einer Minute unter einer eigenen
Adresse auf Port 4001, mit eigener Datenbank und einem Banner, das unübersehbar
Vorschau sagt. Erst was dort in Ordnung ist, geht auf `main` — und `main`
deployt weiter wie bisher, ohne dass sich für die Produktion irgendetwas ändert.

*(This wave is not complete until this can be manually demonstrated.)*

## Why now

Everything built so far went from a feature branch straight to production. That
has been survivable because the suite is thorough and the deploy takes a minute
— but several things this month were found only by looking at the running site,
and one of them, a colour that never committed, was found *in* production by
writing into it.

Wave 17 makes it worse before it makes it better. It adds outbound calls to
sixteen state services, a projection, a compressed raster format and a cache
keyed by location. Every one of those fails in a way the test suite cannot see,
because the test suite has no network and no volume.

## What is already there, and what is missing

The stub for this wave said "none of it is real". That was too pessimistic, and
being precise about it changes the size of the job. Read on 2026-09-05:

| Piece | State |
|---|---|
| `compose.app.yml` | **done** — parameterised for both, `APP_PORT`, `IMAGE_TAG`, `NINANATUR_ENV` |
| Volume isolation | **done by construction** — `ninanatur-data` is scoped by `COMPOSE_PROJECT_NAME`, so `ninanatur-prod_…` and `ninanatur-dev_…` are two volumes |
| `.env.dev.example` | **done** — project name, port 4001, tag `dev`, token deliberately blank |
| `.github/workflows/deploy.yml` | **done** — triggers on `dev-deployment`, tags the image `:dev` |
| `auto-deploy.sh` | **done** — takes the env-file as its argument |
| `crontab.example` | **written, commented out**, and wrong in one way (below) |
| `dev-deployment` branch | missing |
| `deploy/.env.dev` on the host | missing |
| The second stack actually running | missing |
| A subdomain | missing |
| `NINANATUR_ENV` doing anything | **missing — it is passed in and read by nothing** |

So this is not a build. It is a switch-on, plus one banner, plus two decisions
that were left open and one line of cron that is wrong.

## The cron line is wrong, and not in the way the stub thought

The stub said the lock has to be per environment "or a slow prod pull will
starve dev forever". The lock is deliberately global, and the reason is written
next to it: two overlapping runs racing the same image pull corrupt the
containerd content store. That reasoning is right and stays.

The actual defect is in `crontab.example`: **both lines fire in the same
second.** Both carry `sleep 15`, both then race `flock -n` on one lock, and the
loser exits rather than waiting. Every minute is a coin flip, and nothing
guarantees fairness.

The fix is not a second lock. It is **one cron line that rolls both in order**:

```
* * * * * sleep 15; cd /opt/ninanatur && /usr/bin/env bash deploy/auto-deploy.sh deploy/.env.prod && /usr/bin/env bash deploy/auto-deploy.sh deploy/.env.dev >> /var/log/ninanatur-deploy.log 2>&1
```

One lock holder, both environments rolled, production first, no race at all. And
if the prod roll fails, dev is not rolled either — which is the right order of
concern.

## The catalogue claim was wrong too

The stub worried that "hand-entered colours are shared catalogue rows now, and a
preview writing them means a test entry answers for everybody". Checked: it does
not. The catalogue lives in the volume's SQLite (`NINANATUR_DB=/data/…`), the
volume is scoped per project, so a colour entered on dev stays on dev.

**The real gap is the other way round, and it is worth naming while we are
here.** Manual colours exist only on a volume. They are not in the image, not in
the repository, and nothing collects them back. A rebuilt host loses every
colour a user ever contributed. That is not this wave — but it is now written
down instead of being discovered.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | the-branch-that-goes-first | — | planned | — |
| 1 | a-second-stack | — | planned | 0 |
| 2 | one-cron-two-environments | — | planned | 1 |
| 3 | an-address-of-its-own | — | planned | 1 |
| 4 | you-are-looking-at-the-preview | — | planned | 1 |
| 5 | feedback-knows-where-it-came-from | — | planned | 4 |

Two stages:

- **Stage 1 — it runs:** 0, 1, 2. Provable by pushing to `dev-deployment` and
  watching 4001 change.
- **Stage 2 — it is honest about itself:** 3, 4, 5.

## What each one is

### 0. the-branch-that-goes-first

`dev-deployment` is created from `main` and becomes the first stop for a wave:
feature branch → `dev-deployment` → look at it → `main`.

The workflow already triggers on it. What has to be decided and written down is
the *flow*, because a branch nobody uses is worse than none:

- A wave stage merges into `dev-deployment` first.
- `main` is merged **from** `dev-deployment`, not from the feature branch, so
  what goes live is what was looked at.
- `dev-deployment` is reset to `main` after each release, so it never drifts
  into a third history nobody deploys.

This is documented in `deploy/SERVER-SETUP.md` alongside everything else about
the host, because that is where somebody will look at three in the morning.

### 1. a-second-stack

`deploy/.env.dev` on the host from the committed example, then:

```bash
docker compose --env-file deploy/.env.dev -f deploy/compose.app.yml up -d
```

**The volume isolation is proven, not assumed.** `docker volume ls` shows two
volumes; a garden created on 4001 does not exist on 4000; and — the check that
actually matters — the dev stack comes up against a **fresh empty volume**, which
is the state CLAUDE.md names as the one a test double never reproduces and the
one that found the missing schema-at-startup. Wave 17's migrations will meet an
empty volume here first.

### 2. one-cron-two-environments

`crontab.example` corrected to the single chained line above, and
`install-cron.sh` updated to install it. The comment explaining the global lock
stays; the comment about `:15` gains the sentence that both environments share
that slot deliberately.

### 3. an-address-of-its-own

A subdomain through Nginx Proxy Manager to `172.17.0.1:4001`, the same route
production already takes. Certificate as for production.

The name should not be guessable as a typo of the live one — `dev.` in front of
the production host is exactly the kind of thing somebody's browser autocompletes
into at the wrong moment. Decide the name in this feature and write it in
`SERVER-SETUP.md`.

### 4. you-are-looking-at-the-preview

The two pages are identical. A preview that looks exactly like the live site is
how somebody plants a garden on the wrong one and loses it.

`NINANATUR_ENV` is already passed into the container and read by nothing.
`/healthz` gains it, and the frontend reads it there — **not** compiled in, for
the same reason the version badge is not: only the server knows which build is
running, and a baked-in value keeps claiming the old one after a partial
rollout.

A band across the top, not a discreet corner label: it has to survive being
ignored. It says which environment this is and that gardens here are not kept.

### 5. feedback-knows-where-it-came-from

The feedback box files GitHub issues. From a preview, every test of the button
would be a real issue in the tracker.

**Decided default: `.env.dev` leaves `NINANATUR_GITHUB_TOKEN` empty**, which is
already what the example does and is already a supported state — the report is
stored on the volume and `feedback.issue_url IS NULL` is the list of what was
not filed. So the box can be exercised on dev without touching the tracker.

The escape hatch, for when the filing path itself is what needs testing: an env
var naming the label to apply, so an issue from a preview is visibly from one.
Not a second repository — that is a second thing to keep in step.

## Open Research

- **What the version badge says on dev.** The version is `V0.<wave>.<merges on
  this branch>`, and `dev-deployment` will have a different merge count from
  `main` — usually one ahead. That is arguably correct and definitely
  confusing. Options: leave it, or let the environment banner carry the
  distinction and leave the number alone. Decide before feature 4 ships, because
  the two are the same line of the header.
- **Whether the cron should roll dev at all**, or whether a preview is better
  rolled by hand. Automatic is more useful and one more thing to go wrong at
  three in the morning. The chained cron line makes the automatic version safe
  enough that this is now a preference rather than a risk.

## Deliberately not in this wave

- **A staging copy of production data.** Dev starts empty and stays empty —
  which is also the state a migration is least tested against, and exactly the
  case CLAUDE.md says to check by hand. That check stays manual.
- **Backing up the volume**, or collecting hand-entered colours out of it. Named
  above, worth doing, not this.
- A third environment. Two is the number that fits one host and one person.
