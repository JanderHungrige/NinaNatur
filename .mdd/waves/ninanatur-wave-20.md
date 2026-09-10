---
id: ninanatur-wave-20
title: "Wave 20: Nothing here is worse than it looks"
initiative: ninanatur
initiative_version: 24
status: planned
depends_on: ninanatur-wave-19
demo_state: "Ein geschriebener Prüfbericht über Web- und Anwendungssicherheit, jede Feststellung mit dem Ort im Code und einem Reproduktionsweg; die Befunde behoben und durch Tests festgehalten, die den Angriff selbst versuchen. Die Abhängigkeiten sind auf bekannte Schwachstellen geprüft, und CI bricht ab, wenn eine neue dazukommt. Die Datenbank hat eine Sicherung, die jede Nacht läuft und deren Rückspielen geprobt ist."
created: 2026-09-07
hash: 6081daa2
---

# Wave 20: Nothing here is worse than it looks

## Demo-State

Ein geschriebener Prüfbericht über Web- und Anwendungssicherheit, jede
Feststellung mit dem Ort im Code und einem Reproduktionsweg; die Befunde behoben
und durch Tests festgehalten, die den Angriff selbst versuchen. Die
Abhängigkeiten sind auf bekannte Schwachstellen geprüft, und CI bricht ab, wenn
eine neue dazukommt. Die Datenbank hat eine Sicherung, die jede Nacht läuft und
deren Rückspielen geprobt ist.

*(This wave is not complete until this can be manually demonstrated.)*

*Cut in detail on 2026-09-10, from the review of 2026-09-07. **This file names
the work, not the weaknesses.** The verified finding list — every finding with
its location, its reproduction against the app's own test client, its fix and
its test — lives in `.mdd/plans/01-sicherheit-stabilitaet-optimierung.md`,
which is deliberately gitignored (`.mdd/plans/.gitignore`): the repository is
public, and a public list of unfixed weaknesses in a live site is itself one.
The list moves into the repository as the report (feature 11) once the fixes
have shipped.*

## Why now

Nineteen waves have added surface. There is a public site with accounts and
sessions, a share token that *is* the access-control model, an API that takes
polygons and addresses from anyone who asks, a container that deploys itself
from a cron line every minute, and outbound calls to half a dozen state survey
services. None of that had ever been looked at as a whole with the question
"what can somebody do to this that they should not be able to do".

On 2026-09-07 it was — code, container, CI, deploy chain, the live headers, the
dependency trees, and a set of input probes against the app's own test client.
The baseline held: 963 backend tests green, ruff and mypy clean, 581 frontend
tests, production dependencies with no known vulnerabilities. What the review
found, in kind and count rather than in detail:

| Kind | Found | Of which verified by reproduction |
|---|---|---|
| Security | 8 findings (2 high, 5 medium, 1 low–medium) plus one cross-garden write path that is by design and gets named | 6 |
| Stability | 3 | 2 |
| Optimisation | 5, with measurements | 5 |
| Dependencies and the chain around the code | 3 | 3 |

And what it confirmed as **right**, which goes into the report as strengths and
partly into CI as tests that keep them true: the share-token model and its
generation; 404-never-403; bed, element and planting ids scoped to the token's
garden; scrypt with parameters in the hash and a constant-time compare;
sessions stored as hashes; every query parameterised and polygon JSON parsed,
never evaluated; no HTML injection path in the React tree; the feedback box
stripping tokens and defusing mentions.

**This is an audit of this application, by its owner, on their own
infrastructure.** Nothing in it is aimed outward: no scanning, no probing of
hosts this project does not own, no third-party services. Every
proof-of-concept is a test in `tests/` against the app's own client.

## The three open questions, answered

The plan of 2026-09-07 left three questions; the review decided them, and the
decisions shape the features:

1. **Where the report lives.** Split: the raw finding list stays local until a
   fix ships; the delivered report is `.mdd/docs/85-…` and describes each
   finding only after it is fixed — as *that was so, this is now so, this test
   holds it*.
2. **A finding gets a failing test first**, like a bug: the test that runs the
   attack and is red, then the fix that makes it green. For the optimisations
   it is a measurement rather than an attack, but the same shape.
3. **Three things become CI gates** that keep holding after the wave: the
   dependency audits in both ecosystems, the header assertions, and an
   authorisation matrix over every id-carrying route.

## What changed since the review

- **Host access is open** since 2026-09-07 (`ssh jan@159.195.148.193`), so the
  host-side steps in this wave are steps, not waits. Both stacks run there —
  prod on 4000, dev on 4001, separate volumes — and **Nginx Proxy Manager runs
  as a container** that reaches the app through the Docker bridge gateway
  `172.17.0.1`. That single fact decides how feature 1 binds the ports.
- The preview's 500 was a typo in NPM's forward host, fixed the same day; the
  lesson (a 500 and "not configured" are distinguishable from outside) is in
  Wave 18's doc. What remains from that finding is that **nobody was alerted**,
  which feature 6 addresses.
- `ninanatur-zentrale.w3rth.de` was deleted, as Wave 22 requires.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | a-test-that-attacks | — | planned | — |
| 1 | behind-the-proxy-only | — | planned | 0 |
| 2 | every-number-has-an-edge | — | planned | 0 |
| 3 | what-the-app-says-about-itself | — | planned | 0 |
| 4 | a-copy-of-everything | — | planned | — |
| 5 | busy-not-broken | — | planned | 2 |
| 6 | what-the-log-knows | — | planned | 3 |
| 7 | locked-and-signed | — | planned | 0 |
| 8 | parsers-that-refuse | — | planned | 2 |
| 9 | sessions-that-end | — | planned | 3 |
| 10 | faster-where-it-is-felt | — | planned | 5 |
| 11 | the-report | — | planned | 1–10 |

Five stages, in the order the local plan sets — what the live site can suffer
without an account first:

- **Stage 0 — the instrument:** 0.
- **Stage 1 — what needs no account:** 1, 2, 3. Each is a short branch and
  ships on its own.
- **Stage 2 — durability and load:** 4, 5, 6.
- **Stage 3 — the chain around the code:** 7, 8, 9.
- **Stage 4 — what was found beside it, and the record:** 10, 11.

## What each one is

### 0. a-test-that-attacks

The security test harness, before any fix: a `tests/test_security_*.py` family
that drives the app's own test client the way an attacker would — oversized and
non-finite inputs, cross-garden ids, forged headers, hostile parser inputs —
and is red today where the local plan says it is. `pytest-socket` makes the
suite's no-network rule structural rather than conventional. The three CI gates
are named here and land as each feature makes them green. Every later feature
starts by turning one of these tests from red to green.

### 1. behind-the-proxy-only

The application answers only to its proxy. Published ports are bound to the
interface Nginx Proxy Manager actually uses — `172.17.0.1:${APP_PORT}:4000`,
verified from inside the NPM container, not `0.0.0.0` — with a host firewall
rule as the second layer, because Docker's published ports bypass a host
firewall unless the binding itself is specific. Uvicorn is told which address
to trust for forwarded headers (`--forwarded-allow-ips`), so the client address
the app sees is the visitor's and not the proxy's — which is what the login and
registration rate limit keys on today, and why it currently limits everyone
together. The limit's counter moves into SQLite so a deploy (every minute,
by cron) does not reset it, and the same mechanism gains buckets for the
expensive, account-less endpoints.

Host steps and their verification are written into `deploy/SERVER-SETUP.md`;
`tests/test_deploy_config.py` asserts the binding form so it cannot regress
silently. Verified from outside: the direct ports stop answering, the domain
keeps answering.

### 2. every-number-has-an-edge

Every numeric input the API takes gets a range, every float refuses `NaN` and
`Infinity` (a 422, never a 500), every list a length, every request body a size
limit, and the two computations that scale with the drawing — the light grid
and the map import's bounding box — get a hard cap that answers 422 *"Garten
zu groß"* rather than running. The reproduction tests from feature 0 turn green
one by one; a convergence of the light grid's cell count against its inputs is
asserted, not assumed.

### 3. what-the-app-says-about-itself

A small middleware in `web/app.py` sets the headers the live site currently
does not carry — content-type sniffing off, framing denied, a referrer policy,
a content-security policy that names exactly the hosts the plan draws from
(tiles, Wikipedia thumbnails, later the evidence photos of Wave 28) — verified
against the running app so nothing breaks, and asserted in CI on `/`, an API
route and an error response. Trusted hosts are named. HSTS is set where TLS
terminates, at the proxy, and recorded as a host step. Error bodies say the
status and a reason, never an upstream byte or a parser message; an upstream
failure is a 502/503, not a 422 that blames the caller. Swagger and the OpenAPI
document go dark in production and stay up on the preview.

### 4. a-copy-of-everything

There is no backup of the volume that holds every garden, account and feedback
report. A nightly `sqlite3 .backup` into `/data/backups/` with rotation, an
off-host copy, a `PRAGMA integrity_check`, and — the part that makes it a
backup rather than a file — a **restore drill** documented and tested against
a temporary database. Startup takes a copy before running migrations, so a
migration that fails halfway leaves something to go back to.

### 5. busy-not-broken

The app must stay answerable while it is busy. SQLite moves to WAL with a
sensible busy timeout, verified against a fresh empty volume; `/healthz`
becomes async so the probe answers even when the thread pool is exhausted; the
expensive endpoints get a concurrency limit that answers 429 rather than
queueing, and the light computation moves to a process pool so it never holds
the request threads. Outbound calls get budgets: no retry on 4xx, shorter
timeouts, a Wikipedia miss cached as a miss (today a species without an
article costs seconds on every open and is never remembered), an Overpass
timeout treated as a failure rather than cached as "no buildings" forever, and
the HTTP cache moved from the container layer to the volume with a size cap.

### 6. what-the-log-knows

The share token is the whole access control, and today it is in every access
log line, because it is in the path. The access log masks that path segment;
logging becomes structured, with a request id and a security channel for
failed logins, rate-limit hits and 5xx; container logs get rotation; and one
external check watches `/healthz` on both stacks so a dead preview is noticed by
a machine rather than by a person a week later.

### 7. locked-and-signed

The chain around the code. A Python lockfile so the image builds what was
tested; `pip-audit` and `npm audit --omit=dev` as CI gates; GitHub Actions
pinned to commits; Dependabot on; branch protection on `main` and
`dev-deployment` so the merge order the project lives by is enforced rather than
remembered; the deploy script pulling by digest, waiting for the health check
and rolling back on failure instead of pruning the only image it could go back
to; and the container hardened — read-only root, dropped capabilities, resource
limits, a `.dockerignore` that cannot ship a stray `.env`.

### 8. parsers-that-refuse

The two hand-written readers of survey answers. CityGML through `defusedxml`
with a size cap; the GeoTIFF reader checking every length and offset against
the buffer before it allocates, fuzzed with a few thousand malformed tiles in a
bounded test, every failure ending as *this garden stays flat* rather than as a
crash — the supported state the model already documents.

### 9. sessions-that-end

`needs_rehash` exists and is never called: it is wired into login, so the
parameters can be raised without locking anyone out. Expired sessions are
deleted rather than kept forever; an origin check backs `SameSite=Lax` on the
account routes; and the unverified e-mail is named as the thing that must be
verified before any password reset is ever built.

### 10. faster-where-it-is-felt

Measured, not felt. The candidate set — 8 939 taxa reloaded on every search,
every suggestion list, every improvement (238–544 ms per call) — is cached in
process on the catalogue's build stamp. The page's eight sequential loads on
opening a garden become one round of parallel ones. Responses compress. Hashed
assets get long cache headers. The landing video stops preloading three
megabytes. Each with a before/after number in the doc.

### 11. the-report

`.mdd/docs/85-nothing-worse-than-it-looks.md`: every finding, now fixed, with
its location, what was reproduced, what changed and which test holds it; the
strengths, with the authorisation-matrix test that keeps them; the one
cross-garden write path (hand-entered colours) named as a decision rather than
a defect; the share-token model named as a model that a later wave may replace
with a migration, not this one. Written last, published only when everything
above has shipped.

## Acceptance

- Every reproduction test from feature 0 is green, and the local finding list
  has no open entry.
- The three CI gates exist and fail on a seeded regression.
- From outside: the domain answers, the direct ports do not, the headers are
  present on `/`, an API route and a 404.
- A restore from last night's backup has been performed on the preview stack.
- The report exists and says what this file could not.

## Effort, roughly

Stage 0 about a day; stage 1 about four days including the host steps; stage 2
about four; stage 3 about four; stage 4 about three. Three and a half weeks,
of which stage 1 is the part that should not wait for the rest.

## Deliberately not in this wave

- Rewriting the share-token model. If the report says it must change, that is
  a wave of its own with a migration; this one names it.
- Anything aimed outward: no scanning, no probing of hosts this project does not
  own, no third-party services.
- A password reset. It needs verified e-mail first, and that is named, not built.
