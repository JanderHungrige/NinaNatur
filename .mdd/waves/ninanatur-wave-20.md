---
id: ninanatur-wave-20
title: "Wave 20: Nothing here is worse than it looks"
initiative: ninanatur
initiative_version: 24
status: in_progress
depends_on: ninanatur-wave-19
demo_state: "Ein geschriebener Prüfbericht über Web- und Anwendungssicherheit, jede Feststellung mit dem Ort im Code und einem Reproduktionsweg; die Befunde behoben und durch Tests festgehalten, die den Angriff selbst versuchen. Die Abhängigkeiten sind auf bekannte Schwachstellen geprüft, und CI bricht ab, wenn eine neue dazukommt. Die Datenbank hat eine Sicherung, die jede Nacht läuft und deren Rückspielen geprobt ist."
created: 2026-09-07
hash: b8250b0e
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

## Progress

- **2026-09-10 — the binding, ahead of the harness.** Feature 1's port binding
  shipped before feature 0, deliberately: it was live, it needed no account, and
  it was a one-line change with a self-consistency test
  (`test_every_published_port_is_bound_to_the_proxy_interface`) written red
  first. Both stacks now publish on `172.17.0.1` only; verified from outside the
  host and from inside the NPM container. Feature 1 stays open for its other two
  parts — forwarded-header trust and the rate-limit key — and for the host
  firewall, which needs sudo and is the owner's step.
- **2026-09-10 — the same binding on every project on the host.** At the
  owner's request the other stacks behind the same NPM — funding-tender-tracker,
  3dmap, Battlefuel, ctt-report — were rebound to `172.17.0.1` too, and the
  owner moved NPM's admin port 81 to localhost. From outside, no app or admin
  port on the host answers any more; every domain still does.
- **2026-09-10 — feature 2, every number has an edge.** Fourteen attack tests in
  `tests/test_security_input.py`, all red first. Coordinates are bounded to
  ±2 km and refuse NaN and Infinity (a 422, not the 500 NaN used to cause, and
  never stored); outlines and polygons are capped at 500 corners; a map
  selection may not be longer than 1 km, checked before Overpass is asked; the
  light grid refuses a garden it could not compute within four times its budget
  (`GardenTooLarge`, a 422); and any body over 1 MB is a 413 before it is read.
  The plan's ±5 km / 2 km were tightened to ±2 km / 1 km so the import bound and
  the grid bound agree: a 2 km selection would have imported and then been
  refused by the grid. The rate limit for the expensive routes waits for
  feature 1's rate-limit key — keyed as it is today, it would limit everyone
  together.
- **2026-09-10 — feature 1 closed: whom the app believes.** Measured on the
  host, NPM's requests arrive from the Docker network's gateway — 172.27.0.1 for
  production, 172.30.0.1 for the preview — not from 172.17.0.1, where the port
  is published. The plan's `--forwarded-allow-ips=172.17.0.1` would therefore
  have changed nothing. The trust decision now lives in the app
  (`ProxyHeadersMiddleware`, `NINANATUR_TRUSTED_PROXIES`, default
  `127.0.0.1,172.16.0.0/12`) rather than on uvicorn's command line, so the test
  client exercises exactly what the deployment does; uvicorn starts with
  `--no-proxy-headers`. Safe to trust the whole Docker range because the port is
  bound to the bridge only. The rate limit moved from a dict to a SQLite table
  on the volume, keyed on the real visitor, with buckets for `POST /light`,
  `/recompute` and `/from-map` — the last piece of feature 2. `feedback.py` had
  read the **leftmost** `X-Forwarded-For` entry raw, the part anybody writes;
  fixed with it. Ten attack tests, `tests/test_security_proxy.py`.
- **2026-09-10 — feature 3, what the app says about itself.** Measured first:
  the live site sent **no** security header (NPM adds only `Server` and
  `X-Served-By`), and `/openapi.json` and `/api/docs` were public on both
  deployments. `web/security.py` now sets `nosniff`, `DENY`, a referrer policy
  (`strict-origin-when-cross-origin`, not `no-referrer`, because OSM's tile
  policy wants a Referer), COOP, a Permissions-Policy that leaves the clipboard
  alone, and a CSP without `unsafe-inline` — the bundle is one module script and
  one stylesheet. Its `img-src` is read from the orthophoto registry, and names
  `thumb.wikimedia.org` beside `upload.`: the plan named only `upload.`, which
  would have blanked five of the seven photos in the catalogue. HSTS is set by
  the app, only when the trusted proxy reports https. A forged Host is a 400;
  the API description is 404 in production and up on the preview, decided per
  request. Two upstream paths were reproduced and fixed: an unreachable service
  was a bare **500**, and one answering HTML was a **422 carrying the parser's
  message** (`JSONDecodeError` is a `ValueError`); both are now a 502 that names
  nobody, logged in full. Eighteen tests in `tests/test_security_headers.py` —
  the header assertions are one of the three CI gates.
- **2026-09-10 — feature 4, a copy of everything.** Until today there was no
  backup of the 27 gardens, 3 accounts and 7 feedback reports in production.
  `ninanatur/ops/backup.py` takes a copy with SQLite's online backup API (the
  container has no `sqlite3` CLI, and a file copy of a live database is not a
  backup), checks it with `integrity_check` before it is kept, gzips it and
  rotates it — 14 nightly copies and 5 pre-migration copies, each rotation
  blind to the other label. Startup copies an existing database into
  `/data/backups` before `init_schema`; a fresh volume gets nothing, and a failed
  copy is logged and does not stop the site. `deploy/backup.sh` takes the copy
  off the volume onto the host (30 kept), from jan's crontab at 03:17. Restore
  refuses to overwrite without `--replace`. **Drilled on both deployments:** the
  host copy restored into a fresh volume, a throwaway container started on it,
  and its counts matched live (prod 27/3, dev 3/1). Twelve tests in
  `tests/test_backup.py`, including consistency under an open write
  transaction. The **off-host** copy, the owner's choice: a launchd agent on the
  owner's Mac pulls the host copies with rsync daily at 09:30 — pulled, so the
  server holds no key to the Mac — checks the newest with `gzip -t` and keeps
  90 per deployment (`deploy/mac/`). First pull verified for prod and dev.
- **2026-09-10 — feature 5, part 1: readers are answered while a writer
  writes.** Reproduced first: under the default rollback journal a reader
  behind a writer holding the lock got `database is locked`; under WAL it reads
  the last committed state at once. Startup now puts the serving database in
  WAL (`enable_wal`, after the pre-migration copy and the migrations), and every
  connection sets an explicit 5 s busy timeout and `synchronous=NORMAL`.
  `connect()` itself changes no file's journal, so the catalogue in the image
  and the ingest files stay as they are. The online backup takes a commit that
  is still in `-wal` — tested, because a file copy would miss it. Verified on a
  fresh volume, on the preview and in production (both in WAL, counts intact,
  nightly backup run under WAL). Five tests, `tests/test_busy_not_broken.py`.
  Still open in feature 5: async `/healthz`, a concurrency limit with 429, the
  light computation in a process pool, and the outbound budgets.
- **2026-09-10 — feature 5, part 2: a full house says so.** The three expensive
  routes share two slots, one per core on the host (uvicorn runs one process,
  so the cap is the app's, not a worker's). The one too many gets a 429 with
  `Retry-After: 10` at once instead of queueing in the thread pool, and is not
  counted against the visitor's own limit — the slot is a dependency, taken
  before the handler's rate-limit check. A slot is given back however the
  computation ends. Measured on the preview: four `/light` calls 0.2 s apart on
  a garden that had to fetch its terrain — two ran (10.7 s), two were refused
  in 3 ms. `/healthz` is async, so the Docker healthcheck (4 s timeout) no
  longer waits behind a full thread pool. `api/gardens.py` was already 365
  lines on main; the bed and obstacle routes moved to `api/elements.py`, the
  helpers stayed where their importers find them. Eight tests,
  `tests/test_busy_slots.py`. Still open in feature 5: the light computation in
  a process pool, and the outbound budgets.
- **2026-09-11 — feature 5, part 3: every outbound call has a budget.** Three
  findings, each reproduced against the old code before the fix: a 404 was
  asked **three** times with 1+2+4 s of back-off; a species without a Wikipedia
  article cost three requests on **every** open and was never stored (the
  failure path returned before the miss was written, and English was never
  asked); and Overpass's "runtime error" answer — HTTP 200, no elements — was
  cached as "no buildings here" for good. Now only a network failure, a timeout
  or a 5xx is retried; a Wikipedia 404 means *no article*, so English is asked
  and the miss is remembered for its 14 days, while an outage is not; an
  Overpass answer that gave up raises before it can reach the cache, whichever
  fetch brought it; every call has a connect and a read timeout, and Wikipedia
  gets seconds rather than a minute. The HTTP cache moved from the container
  layer onto the volume (`NINANATUR_CACHE_DIR=/data/cache`) with a 500 MB cap
  that forgets the oldest first — on the preview it filled from a map import
  and survived a restart, where production's had been empty since its last
  roll. `species_info`'s swallowed exception is logged now (plan item S2).
  Streets moved to `geo/osm_streets.py` to keep `osm.py` under 300 lines.
  Twelve tests, `tests/test_outbound_budgets.py`. Still open in feature 5: the
  light computation in a process pool.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | a-test-that-attacks | — | planned | — |
| 1 | behind-the-proxy-only | — | complete | 0 |
| 2 | every-number-has-an-edge | — | complete | 0 |
| 3 | what-the-app-says-about-itself | — | complete | 0 |
| 4 | a-copy-of-everything | — | complete (off-host copy: owner) | — |
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
