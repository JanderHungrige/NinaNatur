---
id: ninanatur-wave-20
title: "Wave 20: A place to look at it from"
initiative: ninanatur
initiative_version: 20
status: planned
depends_on: ninanatur-wave-18
demo_state: "Über einen SSH-Tunnel auf Port 4002 — von außen unerreichbar — steht eine Zentrale: wie viele Konten und Gärten es gibt, wie oft die Seite besucht wurde, was gebaut ist und was noch offen steht. Sie liest die Produktionsdatenbank und kann nicht hineinschreiben."
created: 2026-09-06
hash: 5463b867
---

# Wave 20: A place to look at it from

## Demo-State

Über einen SSH-Tunnel auf Port 4002 — von außen unerreichbar — steht eine
Zentrale: wie viele Konten und Gärten es gibt, wie oft die Seite besucht wurde,
was gebaut ist und was noch offen steht. Sie liest die Produktionsdatenbank und
kann nicht hineinschreiben.

*(This wave is not complete until this can be manually demonstrated.)*

## Why it is its own wave

Planned as the second half of Wave 18 and split out on 2026-09-06, because it
is a different job. Wave 18 is a deployment change: a branch, a stack, a cron
line, a banner. This is an application — three pages, a counting mechanism that
touches every request, and a build-time pipeline — and bolting it onto a wave
about compose files would have made both harder to finish.

It still depends on Wave 18, because the Zentrale is the third stack and Wave 18
is what makes a second one exist.

**One thing needs doing before then and does not wait for the wave:**
`ninanatur-zentrale.w3rth.de` was created in advance and should be **deleted**.
A subdomain pointing at 4002 removes the single property that makes this page
acceptable — see feature 0.

## What is already there

Almost nothing, which is unusual for this project and worth stating plainly.

| Piece | State |
|---|---|
| Accounts, sessions, scrypt password hashing | **done** — Wave 9 |
| `NINANATUR_ENV` | passed into the container, read by nothing until Wave 18 |
| `compose.app.yml` | needs a bind host and a second, read-only volume |
| Any counting of visits | **missing — there is no analytics of any kind** |
| Anything that knows what has been built | missing; `.mdd/` knows, the container does not |

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | a-door-with-no-handle-outside | — | planned | — |
| 1 | how-often-anybody-came | — | planned | 0 |
| 2 | what-is-built-and-what-is-not | — | planned | 0 |

One stage. Feature 0 is the stack and the security design; 1 and 2 are what it
shows, and either could ship without the other.

## What each one is

### 0. a-door-with-no-handle-outside

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

### 1. how-often-anybody-came

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

### 2. what-is-built-and-what-is-not

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

- **What counts as a bot.** User-agent matching is unreliable and the honest
  fallback is to label the total rather than to guess. Worth an hour of looking
  at real logs before choosing, because a number that silently means something
  else is worse than no number.
- **Whether the Zentrale should be able to act**, or only to look. It reads a
  read-only mount, so acting would mean changing that — and the reason it is
  read-only is that an admin page is the most dangerous thing in a deployment.
  Looking is enough until it is not.
- **Whether counting belongs in the app at all.** Nginx already writes an access
  log, and parsing it would put nothing in the application's hot path. Against
  that: the log does not know a request opened a *garden* rather than a page,
  which is the number worth having.

## Deliberately not in this wave

- **Any login on the Zentrale.** The tunnel is the boundary. A password on a
  page that exists only on the loopback interface of a machine you already hold
  a key to is a door inside a locked house.
- **Editing anything.** The mount is read-only and that is the feature.
- **Per-visitor anything.** No identifier, hashed or otherwise — see feature 1
  for why, and for what that costs.
