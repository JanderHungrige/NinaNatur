---
id: ninanatur-wave-18
title: "Wave 18: A place to look before it is live, and a place to look at it from"
initiative: ninanatur
initiative_version: 20
status: planned
depends_on: ninanatur-wave-17
demo_state: "Ein Merge auf dev-deployment erscheint binnen einer Minute unter ninanatur-dev.w3rth.de, mit eigener Datenbank und einem Banner, das unübersehbar Vorschau sagt. Und über einen SSH-Tunnel auf Port 4002 — von außen unerreichbar — steht eine Zentrale: wie viele Konten, wie oft besucht, was gebaut ist und was noch offen. Erst was auf dev in Ordnung ist, geht auf main."
created: 2026-09-04
hash: 2fffd486
---

# Wave 18: A place to look before it is live, and a place to look at it from

## Demo-State

Ein Merge auf `dev-deployment` erscheint binnen einer Minute unter
`ninanatur-dev.w3rth.de`, mit eigener Datenbank und einem Banner, das
unübersehbar Vorschau sagt. Und über einen SSH-Tunnel auf Port 4002 — von außen
unerreichbar — steht eine Zentrale: wie viele Konten, wie oft besucht, was
gebaut ist und was noch offen. Erst was auf dev in Ordnung ist, geht auf `main`.

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
| `compose.app.yml` | **mostly** — parameterised for `APP_PORT`, `IMAGE_TAG`, `NINANATUR_ENV`; needs a bind host and a read-only prod mount for the Zentrale |
| Volume isolation | **done by construction** — `ninanatur-data` is scoped by `COMPOSE_PROJECT_NAME`, so `ninanatur-prod_…` and `ninanatur-dev_…` are two volumes |
| `.env.dev.example` | **done** — project name, port 4001, tag `dev`, token deliberately blank |
| `.github/workflows/deploy.yml` | **done** — triggers on `dev-deployment`, tags the image `:dev` |
| `auto-deploy.sh` | **done** — takes the env-file as its argument |
| `crontab.example` | **written, commented out**, and wrong in one way (below) |
| `dev-deployment` branch | missing |
| `deploy/.env.dev` on the host | missing |
| The second and third stacks actually running | missing |
| `ninanatur-dev.w3rth.de` | **created** — the stack behind it is missing |
| `ninanatur-zentrale.w3rth.de` | **created, and must be deleted** — see feature 6 |
| Anything counting visits | missing — there is no analytics of any kind |
| Anything the Zentrale could show | missing |
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
| 2 | one-cron-three-environments | — | planned | 1 |
| 3 | an-address-of-its-own | — | planned | 1 |
| 4 | you-are-looking-at-the-preview | — | planned | 1 |
| 5 | feedback-knows-where-it-came-from | — | planned | 4 |
| 6 | a-door-with-no-handle-outside | — | planned | 1 |
| 7 | how-often-anybody-came | — | planned | 6 |
| 8 | what-is-built-and-what-is-not | — | planned | 6 |

Three stages:

- **Stage 1 — the stacks run:** 0, 1, 2. Provable by pushing to
  `dev-deployment` and watching 4001 change.
- **Stage 2 — the preview is honest about itself:** 3, 4, 5.
- **Stage 3 — the Zentrale:** 6, 7, 8.

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

`ninanatur-dev.w3rth.de` through Nginx Proxy Manager to `172.17.0.1:4001`, the
same route production already takes. Certificate as for production. **Already
created**; this feature is the compose stack behind it and the note in
`SERVER-SETUP.md`.

The name is a sibling rather than a prefix — `ninanatur-dev.` rather than
`dev.ninanatur.`, so a browser autocompleting the live host cannot land on the
preview by accident.

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

### 6. a-door-with-no-handle-outside

The Zentrale: a third stack, on 4002, **bound to `127.0.0.1` and nowhere else**.

This is the whole security design and it is one word in a compose file. Every
other approach to an admin page — a subdomain with a certificate and a login,
basic auth at the proxy, an allow-list of addresses — leaves something on the
public internet that has to hold. Binding to the loopback interface leaves
nothing there at all. It is reached the way the server is already administered:

```bash
ssh -L 4002:127.0.0.1:4002 <host> -N
```

and then `http://localhost:4002` in a browser. The boundary is the SSH key that
already guards the machine, and anybody holding it could read the database
directly in any case — so a login on top would be guarding a door inside a
locked house.

**`ninanatur-zentrale.w3rth.de` must therefore be deleted.** A subdomain
pointing at 4002 removes the single property that makes this page acceptable,
and the page shows every garden.

Three things follow:

- **`compose.app.yml` gains a bind host.** `"${BIND_HOST:-0.0.0.0}:${APP_PORT}:4000"`,
  defaulting to what prod and dev already do, with `BIND_HOST=127.0.0.1` set only
  in `.env.zentrale`. The default has to stay open or production stops answering
  the proxy — a wrong default here is an outage, so the test is a real
  `docker compose config` for all three env files rather than a reading.
- **It reads production, and cannot write to it.** The Zentrale mounts
  `ninanatur-prod_ninanatur-data` as an external volume, **read-only**, at a
  second path. Checked: the database runs in `journal_mode = delete`, not WAL, so
  a read-only open works — WAL would have needed to create a `-shm` file and
  failed. The one edge is a hot journal left by a crash mid-write, which a
  read-only opener cannot roll back; it resolves itself when production recovers.
- **It is the same image.** A separate admin application would be a second thing
  to build, deploy and keep in step. `NINANATUR_ENV=zentrale` turns the routes on,
  and they are refused in every other environment — belt and braces, because the
  routes existing in the production image is the price of one image.

### 7. how-often-anybody-came

There is no analytics of any kind today, and adding some is where a garden app
quietly becomes a surveillance one. So the shape is decided before the code:

**Counters, not records.** One row per day per kind of request, incremented.
No IP addresses, no cookies, no user agents, no per-visitor identifier of any
sort — not hashed, not truncated, not rotated. There is nothing to leak, nothing
to subject-access-request, and nothing to explain in a privacy notice beyond one
sentence.

**Which means unique visitors cannot be reported, and the page says so** rather
than showing a number that is really "requests divided by an assumption". What
can be honestly counted:

| | |
|---|---|
| Requests per day | by kind: landing page, a garden opened, API |
| Gardens created | the number that actually means something |
| Accounts created | per week |
| Feedback | filed, and unfiled because the token was missing |

Crawlers are a large share of any public site's traffic and would flatter every
number here. The counter should separate what it can identify as a bot from what
it cannot, and label the rest honestly as "requests, bots included".

### 8. what-is-built-and-what-is-not

The development overview, and the interesting half is where it comes from.

**The container has neither git nor `.mdd`** — the same constraint that makes the
version a build argument. So this is generated at build time by
`scripts/generate_progress.py` into a JSON that ships in the image, exactly as
`generate_openapi.py` already does for the schema.

**And the to-do list is not a separate list.** It is the `known_issues` the
feature docs already carry, plus the "Deliberately not in this wave" sections,
plus every wave still marked `planned`. A hand-kept roadmap drifts the first time
somebody forgets; this one cannot, because it is assembled from the documents
that the work already updates.

So the missing Bundesländer appear on that page without anybody adding them:
they are in `docs/68-which-ground-and-whose.md` under `known_issues`, written
there when the registry was built.

What it shows:

- **Waves**, complete and planned, each with its demo state — which is already a
  sentence in German saying what the wave delivers.
- **Features** per wave, with their doc.
- **What is open**: every `known_issues` entry across all docs, with the feature
  it belongs to. Currently around thirty, which is itself worth seeing.
- **The seven files over 300 lines**, because that list has been carried in
  conversation for three waves and belongs somewhere it cannot be forgotten.

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
- **What counts as a bot.** User-agent matching is unreliable and the honest
  fallback is to label the total rather than to guess. Worth an hour of looking
  at real logs before choosing, because the number is useless if it silently
  means something else.
- **Whether the Zentrale should be able to act**, or only to look. It reads a
  read-only mount, so acting would mean changing that — and the reason it is
  read-only is that an admin page is the most dangerous thing in a deployment.
  Looking is enough until it is not.

## Deliberately not in this wave

- **Any login on the Zentrale.** The tunnel is the boundary. A password on a
  page that only exists on the loopback interface of a machine you already hold
  a key to is a door inside a locked house — see feature 6.
- **A staging copy of production data.** Dev starts empty and stays empty —
  which is also the state a migration is least tested against, and exactly the
  case CLAUDE.md says to check by hand. That check stays manual.
- **Backing up the volume**, or collecting hand-entered colours out of it. Named
  above, worth doing, not this.
- A third environment. Two is the number that fits one host and one person.
