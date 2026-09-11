---
id: 85-nothing-worse-than-it-looks
title: Nothing Here Is Worse Than It Looks
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-20
wave_status: active
depends_on: []
relates: [35-accounts, 62-manual-colours, 84-what-else-is-standing-there]
source_files:
  - ninanatur/web/app.py
  - ninanatur/web/security.py
  - ninanatur/web/logs.py
  - ninanatur/web/delivery.py
  - ninanatur/api/origin.py
  - ninanatur/api/accounts.py
  - ninanatur/api/gardens.py
  - ninanatur/api/schemas.py
  - ninanatur/api/candidate_cache.py
  - ninanatur/auth/sessions.py
  - ninanatur/ops/backup.py
  - ninanatur/garden/light_worker.py
  - ninanatur/garden/measured.py
  - ninanatur/ingest/http.py
  - ninanatur/geo/lod2.py
  - ninanatur/geo/tiff.py
  - ninanatur/geo/tiff_codec.py
  - deploy/compose.app.yml
  - deploy/auto-deploy.sh
  - deploy/backup.sh
  - Dockerfile
  - .github/workflows/deploy.yml
  - .github/workflows/healthz.yml
  - requirements.txt
  - requirements-dev.txt
routes: []
models: [rate_limit, session, catalogue_meta]
test_files:
  - tests/test_security_matrix.py
  - tests/test_security_headers.py
  - tests/test_security_input.py
  - tests/test_security_proxy.py
  - tests/test_no_network.py
  - tests/test_sessions_end.py
  - tests/test_deploy_config.py
  - tests/test_backup.py
  - tests/test_busy_not_broken.py
  - tests/test_busy_slots.py
  - tests/test_light_worker.py
  - tests/test_outbound_budgets.py
  - tests/test_logs.py
  - tests/test_supply_chain.py
  - tests/test_auto_deploy.py
  - tests/test_container_hardening.py
  - tests/test_parsers_refuse.py
  - tests/test_candidate_cache.py
  - tests/test_served_fast.py
  - tests/test_measure_is_bounded.py
data_flow: mixed
last_synced: 2026-09-11
status: complete
phase: all
mdd_version: 11
tags: [security, audit, report, authorization, headers, rate-limit, backup, supply-chain, parsers, sessions, performance]
path: Operations/Security/Report
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - ninanatur/api/gardens.py::require_garden
  - ninanatur/api/gardens.py::require_bed
  - ninanatur/api/planning.py::_owned_planting
  - ninanatur/api/origin.py::same_origin
  - ninanatur/web/app.py::TRUSTED_PROXIES
known_issues:
  - "Hand-entered flower colours are a write to the shared catalogue from any garden's token — by design, and named below, not refused."
  - "The share token is the whole of a garden's access control. A later wave may replace the model; that needs a migration and is not this report's to make."
  - "The tree finder masks every drawn element's box as though it were a building. What the mask should be is a design question (see Found beside the audit)."
---

# Nothing Here Is Worse Than It Looks

The report of Wave 20. On 2026-09-07 NinaNatur was looked at as a whole for the
first time with one question — *what can somebody do to this that they should
not be able to do* — across the code, the container, CI, the deploy chain, the
live headers, the dependency trees, and a set of input probes against the app's
own test client. Wave 20 then fixed what was found, one feature at a time, each
starting from a test that ran the attack and was red.

This file is written last, and names each finding only now that it is fixed:
*that was so, this is now so, this test holds it.* Until today the list lived
outside the repository, because the repository is public and a public list of
unfixed weaknesses in a live site is itself one.

**This was an audit of this application, by its owner, on their own
infrastructure.** Nothing in it was aimed outward — no scanning, no probing of
hosts this project does not own, no third-party services. Every proof of
concept is a test in `tests/`, against the app's own client.

## In numbers

| | At the review, 2026-09-07 | Now |
|---|---|---|
| Backend tests | 963 | 1,232 |
| Frontend tests | 581 | 586 |
| Security findings | 8 (2 high, 5 medium, 1 low–medium) | fixed |
| Stability findings | 3 | fixed |
| Optimisation findings | 5 | fixed, with numbers |
| The chain around the code | 3 | fixed, one decision with the owner |
| CI gates | none | four, each shown to fail on a seeded regression |

## What was found, and what it is now

### What needed no account

**The app answered on the open internet, past the proxy.** Both stacks
published their ports on every interface, so `http://<host>:4000` and `:4001`
reached uvicorn directly — no TLS, no proxy headers, and the preview public by
a second road. The ports are bound to the Docker bridge that Nginx Proxy
Manager uses (`172.17.0.1`), checked from outside the host (the ports do not
answer, the domains do) and from inside the proxy's container. The same binding
went onto every other project behind the same proxy. *Held by*
`tests/test_deploy_config.py::test_every_published_port_is_bound_to_the_proxy_interface`.

**The app believed nobody, so its login limit throttled everybody.** Measured on
the host, the proxy's requests arrive from each Docker network's gateway, not
from the bridge the port is published on; uvicorn trusted only `127.0.0.1`, so
every visitor was the proxy and ten wrong passwords from anyone locked the login
for the whole site. The trust decision now lives in the app
(`ProxyHeadersMiddleware`, `127.0.0.1,172.16.0.0/12`, safe because the port is
bound to the bridge), the limit's counter lives in SQLite so a deploy does not
reset it, and it is keyed on the real visitor. The feedback box had read the
*leftmost* `X-Forwarded-For` entry — the part anybody writes. *Held by*
`tests/test_security_proxy.py` (ten tests).

**Two routes were amplifiers.** Coordinates had no range: an obstacle at
`x=1e9` was accepted and `POST /light` then tried to build a grid of hundreds of
millions of cells (reproduced: it did not return). A map selection could span
the country and send a query across half of it to a public Overpass instance
(reproduced: the query timed out after 41 s). Coordinates are bounded to
±2 km, outlines to 500 corners, a map selection to 1 km — checked before
Overpass is asked — the light grid refuses a garden it could not compute
(`GardenTooLarge`, 422), a body over 1 MB is a 413 before it is read, and the
three expensive routes have per-visitor limits. *Held by*
`tests/test_security_input.py` (fourteen tests).

**`NaN` and `Infinity` were accepted.** `NaN` broke the response and came back
as a 500; `Infinity` was stored and poisoned every shadow computation after it.
Every input model refuses non-finite numbers with a 422, and nothing of the
kind is stored. *Held by* `tests/test_security_input.py`.

**The app said nothing about itself.** No security header at all, and the API
description public on both deployments. It now sends `nosniff`, `DENY`, a
referrer policy, COOP, a Permissions-Policy and a content-security policy
without `unsafe-inline`, whose image sources are read from the same registry
the map uses; HSTS when the trusted proxy reports https; a forged `Host` is a
400; `/openapi.json` and `/api/docs` are 404 in production. An unreachable
upstream was a bare 500 and one answering HTML was a 422 carrying the parser's
message, blaming the caller for somebody else's outage — both are now a 502
that names nobody, logged in full. *Held by* `tests/test_security_headers.py`
(a CI gate).

### Durability and load

**There was no backup.** Now: SQLite's online backup API, an integrity check
before a copy is kept, gzip, rotation (fourteen nightly, five before a
migration), a copy taken before every migration, a nightly copy onto the host
and an off-host copy pulled from there — and a **restore drilled** on both
deployments into a fresh volume, its counts matching live. *Held by*
`tests/test_backup.py`.

**A reader behind a writer got `database is locked`.** Reproduced under the
rollback journal; the serving database is in WAL with an explicit busy timeout.
*Held by* `tests/test_busy_not_broken.py`.

**A full house queued rather than said so, and a relight held every request.**
The expensive routes share two slots and the one too many is a 429 with
`Retry-After` at once; `/healthz` is async so a busy app does not look dead to
the deploy; the light runs in a process pool, so two relights at once take
19.5 s each instead of 37.8 s and a plain `GET` stays at 22 ms instead of 220 ms
while they run. The month view had computed a grid on every request with no
slot and no limit; it has both. *Held by* `tests/test_busy_slots.py`,
`tests/test_light_worker.py`.

**Outbound calls had no budget.** A 404 was asked three times with back-off; a
species without a Wikipedia article cost three requests on every open and was
never remembered; an Overpass answer that had given up was cached as "no
buildings here" for good. Now only a failure worth repeating is repeated, a
miss is remembered and an outage is not, a given-up answer never reaches the
cache, every call has a connect and a read timeout and a byte cap, and the cache
lives on the volume with a size limit. *Held by* `tests/test_outbound_budgets.py`.

**The log knew the share tokens.** Every access line carried the visitor's full
address and the path — on the garden routes, the token, which is the whole of a
garden's access control. The app writes its own access line with the route
template and an eight-character hash of the token; anything token-shaped is
masked whatever wrote it; addresses are kept to their /24 or /48; each request
has an id; failed logins, refusals and 5xx go to a security channel; the log is
rotated; and a scheduled check watches both deployments from outside, so a dead
preview is noticed by a machine. *Held by* `tests/test_logs.py`.

### The chain around the code

**What was tested was not what shipped.** No lockfile, nothing audited, every
Action and both base images on tags their owners can move, Dependabot off, and a
deploy script that pruned the one image it could have gone back to. Now: hashed
locks installed with `--require-hashes` in the image and in CI; `pip-audit` and
`npm audit --omit=dev` as CI gates; Actions pinned to commits and base images to
digests; Dependabot proposing into the preview branch, its pull requests tested
and never built into an image; a deploy that keeps the image it replaces, waits
for the health check and rolls back; and a container that runs read-only with
every capability dropped and memory, process and CPU limits. *Held by*
`tests/test_supply_chain.py`, `tests/test_auto_deploy.py`,
`tests/test_container_hardening.py`.

**The two hand-written parsers trusted their input.** The building survey's
CityGML went through the standard library's XML parser; a GeoTIFF header could
make the reader allocate width × height before a pixel was read, in the request
thread; the LZW table grew without bound. The tiles go through `defusedxml`
under a size cap, every fetch has a byte cap, and the TIFF reader checks every
offset and length against the file and ends every malformed file as a
`TiffError` — three thousand seeded mutations of real tiles in the test. *Held
by* `tests/test_parsers_refuse.py`.

**Sessions did not end, and a sister site was "the same site".** Expired
sessions were refused but never deleted; raised password-hash parameters would
only ever have reached new accounts; and `SameSite=Lax` lets through requests
from every other project under the same registrable domain — to a browser they
are the same site, and a POST without a body needs no preflight. A login now
rehashes a weaker hash, expired sessions are swept, the cookie ends when the
session does, and every route that acts on a login refuses a request that comes
from another page — checked on the preview through the proxy. The account form
had promised a password reset that does not exist; it now says so, and a test
holds that none appears before e-mail addresses can be verified. *Held by*
`tests/test_sessions_end.py`.

**Stability, checked and kept.** The broad `except` around filing a feedback
report on GitHub stays: the report is stored first, and filing is best effort.
Narrowed, a programming error in the filing would reach the visitor as a 500
after their report was saved — and they would send it again. The traceback is
logged with the report's id.

### Found beside the audit

- **Measuring the buildings took minutes.** Every half-metre sample of every
  drawn building was tested against every one of a survey tile's 2,601
  buildings. A box test first: 19.13 s to 0.04 s on a dense garden, the same
  answers. An accepted tree suggestion had been measured again as a building on
  every recompute; only roofed kinds are measured now. *Held by*
  `tests/test_measure_is_bounded.py`.
- **The same work was done on every request.** The plant catalogue is held
  between requests, keyed on its build and on every hand edit; answers are
  compressed; hashed assets are cached for a year and the page asked about every
  time; opening a garden asks for its six answers at once — 455 ms instead of
  1,318 ms. *Held by* `tests/test_candidate_cache.py`, `tests/test_served_fast.py`,
  `frontend/src/derived.test.ts`.
- **A guard that checked nothing.** The walker meant to hold that every route
  acting on a login checks where the request came from looped over
  `app.routes`, which since FastAPI 0.141 holds included routers as opaque
  entries: it met three routes, none a write, and passed. The protection held —
  the origin tests call the real routes — but the proof did not reach them. It
  now walks the routes the way the API document does and says what it checked.
- **The tree finder** masks every drawn element as though it were a building,
  the garden outline and every street included. Masking by what stands only was
  tried and measured, and lost a garden's tallest crown, because the street
  boxes had been cutting a row of trees into proposable pieces. A design
  question, left open.

## What the review confirmed as right — and what keeps it right

- **The share token** is `secrets.token_urlsafe(32)`; a garden's numeric id
  never appears in a URL.
- **404, never 403.** An unknown garden and somebody else's garden get the same
  answer; a 403 would confirm that a token exists.
- **Every id is scoped to the token's garden.** *Held by the authorization
  matrix* (`tests/test_security_matrix.py`, a CI gate): each route that takes
  the id of a bed, an element, a planting or a tree suggestion refuses one from
  another garden with a 404 and leaves both gardens unchanged; the same call
  with the garden's own id is answered; each of the twenty-seven routes that
  take a token refuses one that names no garden; and a route added later fails
  the test until somebody has decided what kind of id it takes.
- **Passwords** are scrypt with the parameters in the hash and a constant-time
  comparison — and a login now moves an old hash to the current parameters.
- **Sessions** are stored as hashes of the token, never the token.
- **Every query is parameterised**, and polygon JSON is parsed, never evaluated.
- **No HTML injection path** in the React tree; text from Wikipedia is rendered
  as text.
- **The feedback box** keeps tokens and gardens out of the issue and defuses
  mentions.
- **No test reaches the network**, now by construction: `pytest-socket` refuses
  every socket but a Unix one for the whole suite.

## Decisions, named rather than fixed

- **Hand-entered colours are shared.** `PUT /{token}/colours/{taxon_id}` writes a
  `manual` trait row into the catalogue every garden reads — the one write that
  reaches beyond the garden that made it. Asked for, limited to ten drawable
  colours, outranked by every published source, and, if more than one colour
  per species is ever allowed, the place to look first.
- **The share-token model.** A token is the whole of a garden's access control:
  whoever has the link has the garden. That is what makes sharing a plan one
  link, and it is the model a later wave may replace — with a migration, not in
  passing.

## The gates

CI runs four gates, first and by name, and each was shown to fail on a seeded
regression before it was trusted:

| Gate | Holds | Seeded regression | Result |
|---|---|---|---|
| Authorization matrix | ids and tokens, every route | `require_bed` stops checking whose bed it is | red on the three routes that use it |
| Security headers | every answer, errors included | `X-Frame-Options` dropped | six tests red |
| Origin walker | every route that acts on a login | claim loses its origin check | red |
| No network | the whole suite | the socket rule switched off | red |

Beside them, the dependency audits: `pip-audit` on what the image ships and
`npm audit --omit=dev` on what a browser downloads — given a Jinja pinned at
2.10, `pip-audit` names its advisories and exits 1.

## Still with the owner

Named in the wave's own record already, and repeated here so the report is
whole: branch protection on `main` and the preview branch, a host firewall as a
second layer behind the bridge-only binding, and a host-wide default for
container log rotation, which restarts every project on the host.
