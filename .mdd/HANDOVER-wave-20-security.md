# Handover — Wave 20: web and application security review

Written 2026-09-07 for a fresh session picking up Wave 20. Everything here is
scoped to the security work; the rest of the project's history is in
`.mdd/waves/` and `CLAUDE.md` and is not needed to start.

The wave plan itself is `.mdd/waves/ninanatur-wave-20.md`. Read that first — it
carries the scope. This file carries the ground truth a cold session would
otherwise spend an hour rediscovering, plus the things I noticed while working
nearby and did **not** verify.

---

## 1. What the task is

NinaNatur is a German garden planner, live at `ninanatur.w3rth.de`. Nineteen
waves have added surface and none of it has been reviewed as a whole against the
question *what can somebody do to this that they should not be able to do*.

Wave 20 is that review, and then the fixes it names. The demo-state is a written
report where every finding carries its location in the code and a way to
reproduce it, the findings fixed, tests that attempt the attack, a dependency
audit, and a CI gate so the answer stays true.

**This is an audit of this application, by its owner, on their own
infrastructure.** Nothing in the wave is aimed outward: no scanning, no probing
of hosts this project does not own, no third-party services. If a finding needs
a proof-of-concept, it belongs in `tests/` against the app's own test client.

## 2. Ground rules that are not negotiable

From `CLAUDE.md`, and they have bitten before:

- **Never commit to `main`.** Branch per feature. The merge path is
  `feat/<x>` → `dev-deployment` → `main`, so what goes live is what was looked
  at. After a release `dev-deployment` is reset to `main`.
- `ruff check`, `mypy --strict`, `pytest` clean before every commit.
- No file > 300 lines, no function > 50 lines. Two files were split this week
  for exactly this reason; expect to do it again.
- Tests assert behaviour, not execution. And **tests must not depend on their
  environment** — `tests/conftest.py` switches off every outbound state survey
  suite-wide, and the suite has been verified to pass with sockets forbidden.
  Keep it that way.
- Never commit `data/raw/`, `data/cache/`, `*.sqlite`, `.env`. Only
  `deploy/.env.*.example` is tracked.
- MDD: doc first, then tests, then code.

## 3. How to run it

```bash
.venv/bin/python -m pytest tests/ -q          # 963 tests, ~35 s
.venv/bin/python -m ruff check ninanatur tests
.venv/bin/python -m mypy --strict ninanatur
cd frontend && npx tsc --noEmit && npx vitest run   # 581 tests
```

The API is FastAPI, `ninanatur/web/app.py`. Local run:
`.venv/bin/python -m uvicorn ninanatur.web.app:app --host 127.0.0.1 --port 4000`.
The frontend dev server proxies `/api` and `/healthz` to 4000.

Production is a container rolled by a cron line on the host; CI never SSHes in.
Deployed version shows at `https://ninanatur.w3rth.de/healthz`.

## 4. The attack surface, with pointers

### Authentication and sessions

| | |
|---|---|
| Sessions | `ninanatur/auth/sessions.py` — `secrets.token_urlsafe(32)` |
| Passwords | `ninanatur/auth/passwords.py` — `hashlib.scrypt`, parameters stored in the hash (`scrypt$N$r$p$salt$hash`) so they can be raised without locking anyone out |
| Cookie | `ninanatur/api/accounts.py::_set_cookie` — `httponly=True`, `samesite="lax"`, `secure` follows the scheme the request arrived on, including the proxy header |
| Rate limit | `ninanatur/api/accounts.py::_rate_limit` — in-process dict, buckets for register and login only |
| Tests | `tests/test_accounts.py` is the only security-adjacent test file that exists |

### The share token *is* the access-control model

`ninanatur/garden/store.py` — `secrets.token_urlsafe(32)` per garden. Anyone
holding it can read and edit that garden. This was deliberate and is documented
in `.mdd/docs/08-garden-model.md`; it has never been examined against how the
token travels. The frontend puts it in `window.location.hash`
(`frontend/src/App.tsx`, lines 68, 225, 424) — the one part of a URL browsers do
not send in `Referer`, which is a good property nobody appears to have chosen
deliberately. Confirm it rather than assume it, and check the rest of the path:
server logs, browser history, screenshots, and how a garden is actually shared.

### Input

Pydantic schemas in `ninanatur/api/schemas.py` (654 lines — the largest single
place to review). Bounds already exist in places: latitude `ge=-90, le=90`,
polygons `max_length=500`, heights `gt=0, le=200`, month `ge=3, le=10`. The
question is where they do not, and what happens past them rather than at them.

### Injection

Every query in the project is parameterised and polygon JSON is parsed, never
evaluated. That is a claim in `CLAUDE.md` and the review should **verify** it
rather than restate it. The other direction: the frontend is React with no
`dangerouslySetInnerHTML` in production code (only test assertions mention
`innerHTML`) — but the plan is an SVG built from user-supplied labels and
geometry, and SVG is its own question.

### The outbound half — the part I would look at first

The app fetches from Nominatim, Overpass, eight state WCS services and NRW's
LoD2 store, then parses the answers.

| Where | What it parses | Note |
|---|---|---|
| `ninanatur/ingest/http.py` | all outbound | `requests`, fixed User-Agent, timeout 60 s (300 s streaming), disk cache under `data/cache/` |
| `ninanatur/geo/lod2.py` | CityGML, ~38 MB | `xml.etree.ElementTree.iterparse` — **stdlib, not `defusedxml`** |
| `ninanatur/geo/tiff.py`, `tiff_codec.py` | GeoTIFF | hand-written binary reader: both endiannesses, LZW, predictors, strip/tile offsets |
| `ninanatur/geo/osm.py`, `surroundings.py` | JSON | Nominatim / Overpass |

The cache means a hostile answer, once fetched, is replayed on every rerun.

### Deployment

`deploy/auto-deploy.sh` (cron, every minute, `flock`), `deploy/compose.app.yml`,
`deploy/SERVER-SETUP.md`, `.github/workflows/deploy.yml`. The GHCR package is
public. `.env` files live only on the host.

### What the app says about itself

`ninanatur/web/app.py` — and this is the shortest section for a reason: **there
is no security middleware at all.** No CORS policy, no `TrustedHostMiddleware`,
no `HTTPSRedirectMiddleware`, no CSP, no `X-Frame-Options`, no
`X-Content-Type-Options`, no `Referrer-Policy`. Whether that matters depends on
what Nginx Proxy Manager already sets in front of it, which nobody has checked.

## 5. Candidate findings I noticed but did not verify

Stated as suspicions, not as findings. Each needs reproducing before it is
written down as real.

1. **`ElementTree` on a 38 MB external document** (`geo/lod2.py`). Python's
   stdlib parser has entity expansion disabled for external entities since 3.8
   but is not hardened against every amplification shape. Worth establishing
   what it actually does with a hostile document, and whether `defusedxml`
   belongs here.
2. **No security headers** (above). Establish what the proxy sets before
   deciding what the app should.
3. **Rate limiting exists only on register and login**, in an in-process dict —
   so it resets on every container roll (which is every deploy, and deploys are
   a cron line away) and does not exist at all for the garden API, the map
   import, or `POST /light`, which is the most expensive call in the app
   (seconds of CPU, and it triggers outbound survey fetches).
4. **`POST /light` as an amplifier.** One request can cost 5 s of CPU and can
   make the server fetch megabytes from a state survey. It needs no account.
5. **The hand-written GeoTIFF reader** parses attacker-influenceable lengths and
   offsets. It is careful code with real tests, but it has never been fuzzed.
6. **Error bodies and status codes.** `require_garden` gets this right on
   purpose and says so in its docstring: *never 403, because telling a caller
   that a token exists but is not theirs is the one thing the model must not
   do.* The review's job is to confirm the **rest** of the surface follows the
   same rule — bed and obstacle ids, account-owned gardens, the feedback
   endpoints — and that no error body says more than its status does.

## 6. Decide these before planning the features

The wave plan leaves three questions open, and they change the shape of the work:

1. **Where does the report live?** `.mdd/audits/` is gitignored and therefore
   ephemeral; `.mdd/docs/` is permanent and public in the repo. A security
   report that names live weaknesses in a public repository is itself a
   decision — probably: fixes and their tests in the repo, the raw finding list
   somewhere it is not published until the fix ships.
2. **Does a finding get a failing test first**, the way a bug does? It is the
   right discipline and it means writing an exploit before the fix.
3. **How much becomes a CI gate** that keeps holding, rather than a one-off
   reading? Dependency audit is the obvious one; header assertions and an
   authorisation matrix test could be others.

## 7. Out of scope for this wave

- Rewriting the share-token model. If the review says it must change, that is
  its own wave with a migration; this one names it.
- Third-party penetration testing of the host.
- Anything aimed at systems this project does not own.

## 8. State of the repo as you inherit it

- `main` and `dev-deployment` level at the wave re-slot commit; production at
  `V0.19.84` and healthy.
- **Waves 1–19 all complete.** Wave 18's dev environment went live on
  2026-09-07: `ninanatur-dev.w3rth.de` reports `environment: dev` and runs its
  own container on its own volume. There is a second deployed surface now, and
  the review should treat it as one — it is the same image with different
  configuration, and a preview environment that is less careful than production
  is a way into production.
- **Host access works** as of 2026-09-07: `ssh jan@159.195.148.193` with
  `~/.ssh/id_ed25519`. Worth knowing for this wave, because the deployment path
  is in scope — `deploy/auto-deploy.sh`, the cron that rolls containers, and the
  `.env` files that live only on the host can now actually be read rather than
  reasoned about. Both stacks run there: prod on 4000, dev on 4001, separate
  volumes.
- Waves 21 (roof detail), 22 (Zentrale) and 25 (ordering) planned and untouched.
- Two things waiting on somebody with host access: the Wave 18 host steps in
  `deploy/SERVER-SETUP.md`, and deleting the unused subdomain
  `ninanatur-zentrale.w3rth.de`.
- Gardens created before 2026-09-07 hold coordinates rounded to 0.1°. The owner
  has said they may simply be deleted; no migration is owed.

## 9. Where the review stands — 2026-09-10

The review ran on 2026-09-07. Its verified finding list — location,
reproduction against the app's own test client, fix, test — is
`.mdd/plans/01-sicherheit-stabilitaet-optimierung.md`, **gitignored on
purpose** (`.mdd/plans/.gitignore`) and therefore local to the owner's machine:
this repository is public. Section 6's three questions are answered there and
in the wave: the report is written after the fixes as `.mdd/docs/85-…`; every
finding gets a failing test first; the dependency audits, the header assertions
and an authorisation matrix become CI gates.

`.mdd/waves/ninanatur-wave-20.md` is cut in detail with neutral feature names —
twelve features in five stages — and maps to the local list in its section 5.
With host access open, the host-side steps are steps rather than waits; Nginx
Proxy Manager runs as a container and reaches the app through `172.17.0.1`,
which decides how feature 1 binds the ports.
