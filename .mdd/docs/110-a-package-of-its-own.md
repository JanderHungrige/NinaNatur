---
id: 110-a-package-of-its-own
title: A Package of Its Own
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: complete
depends_on: [102-which-tiles-and-whose, 103-a-tile-not-a-service, 109-is-it-still-there]
relates: [106-which-source-said-so, 17-terrain-window]
source_files:
  - ninanatur/geo/tiles.py
  - Dockerfile
routes: []
models: []
test_files:
  - tests/test_supply_chain.py
data_flow: reads-existing
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [packaging, pypi, licence, mit, geokachel, reuse, boundary]
path: Geo/Package
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: [https://github.com/JanderHungrige/geokachel]
---

# 110 — A Package of Its Own

## Purpose

Waves 17 to 25 built something with no equivalent on PyPI: one interface to
official German elevation, surface, building and point-cloud data across all
sixteen Bundesländer, with the credit each licence requires attached to every
number. It was sitting inside a garden-planning app.

`packages/geokachel` is that, extracted, MIT, installable.

## The seam

The question was never *whether* the code was separable — the dependency map
said it was. It was **where the app's opinions begin**, and the answer is one
sentence:

> The package stops at a north-up raster in the source's own UTM. Putting that
> on somebody's own axes is theirs.

That is not a technicality. UTM grid north is up to 2.3° off true north in
Germany. A shadow model *must* correct for it; a map-maker must not have the
correction imposed. So `in_garden_frame` and `resample` stay in NinaNatur, and
`tiles.py` keeps exactly the half that rotates — while everything about *where
a tile lives and what comes out of it* moved.

Seventeen modules moved unchanged, plus `addressing.py` cut out of `tiles.py`,
plus `net.py` and `cli.py` written for the package. Forty-five files had their
imports rewritten. The suite went from 1,530 passing to 1,530 passing.

## What was measured, not assumed

- **The coupling was three things**, and all three dissolved: five thin HTTP
  wrappers (already injected everywhere but one call site, now a `Transport` of
  plain callables); an enum; and the frame conversion above.
- **`Roof` does not belong in the package**, though it looked as if it did. It
  is a *shading* abstraction — `ADV_ROOFS` collapses Walmdach and Krüppelwalmdach
  both to `HIP`, and Mansarddach to `GABLE`. That is right for a shadow and
  wrong for a library. What a library should carry is the raw `dachform` key.
- **`state_at` reverse-geocodes against Nominatim.** Fine once per garden behind
  a disk cache; fatal in a library somebody loops over ten thousand plots. So
  `state=` is a required argument and the package ships no geocoder.

## Two packaging bugs the build found

**No `py.typed`.** The classifier said `Typing :: Typed` and the marker was
missing, so `mypy` silently treated every symbol from the package as `Any` —
and the app that had just been refactored onto it lost its types without a
word. Three "returning Any" errors were the only trace.

**A protocol a frozen dataclass cannot satisfy.** `Coverage` declared `state`,
`url` and `coverage` as mutable attributes; the registries are frozen
dataclasses, whose attributes are read-only. Declared as properties, they match.

## Its own repository, and the cost of that

It lived in `packages/` here for about an hour. Then the owner asked the right
question — *wouldn't a separate repo be better for improvements and
collaboration?* — and it moved to
**[JanderHungrige/geokachel](https://github.com/JanderHungrige/geokachel)**,
published as **`geokachel` 0.1.0** on PyPI on 2026-09-21.

Four reasons, and the timing mattered. **The repository URL is baked into the
published metadata**, so moving after a release means a version that exists
only to fix links. A contributor to an elevation library should not have to
clone a React frontend and a plant-trait pipeline, nor should a bug report
about a Sachsen share token land in a garden app's tracker. The package's CI
runs in 27 seconds against this repository's ninety-plus and an image build.
And **Warren Davison's Draft Sketch style is here under a personal permission**
— a stranger forking a monorepo to fix a tile URL would take that with them,
which is a courtesy argument rather than a tidiness one.

**The cost is real and was argued against.** The registry is the thing most
likely to need a fix, and a fix is now four steps rather than one: correct it
in geokachel, tag, let Trusted Publishing release, bump the pin here. What
makes that bearable is that doc 109's check says *when* a fix is needed, and a
release is `git tag && git push`.

So this repository depends on it like any other package, hash-pinned in
`requirements.txt` — the one lock that pins it; CI installs that lock beside the
tools, so it tests exactly what the image ships (doc 85, since 2026-09-22):

```
geokachel==0.1.0 \
    --hash=sha256:1b398592af44147ee96feeca84fcda6937a8f30cde1b4bc2a01e4f422098a7da \
    --hash=sha256:8eb1ed9f5f86d35d2a43f3ee0297588f4465877289e7ac240e831e7e6d330a2f
```

Pinned exactly, not `>=`: a new state should arrive because somebody chose it,
not because a resolver did. The supply-chain test caught `requirements-dev.txt`
missing it on the first run — the drift it exists to catch, and the reason each
package is now pinned in one lock only.

## Published without a token

`release.yml` in the package's repository uses **PyPI Trusted Publishing**:
GitHub mints a short-lived OIDC identity for that exact workflow in that exact
repository, and PyPI trusts it instead of a long-lived secret. There is no
token to leak, rotate or paste into a terminal.

The first attempt failed with `invalid-publisher`, because the pending
publisher had not been created yet — and **nothing was published**, which is
the right way for it to fail. The workflow also refuses a tag that disagrees
with the version in `pyproject.toml`, because a PyPI version can never be
reused, even after deletion.

## The check ships with it

Doc 109's health check is `geokachel check`, so whoever installs the package
gets the means to find out that a state moved — not only this app. It runs
weekly in the package's own `.github/workflows/sources.yml`, and **it does not fail the build**:
it opens an issue, or comments on the open one. A red build nobody can fix by
changing code is a red build everybody learns to scroll past.

## Business Rules

1. **The package stops where the app's frame begins.** North-up, source's own
   UTM, NaN for unknown.
2. **It fetches nothing itself.** Every byte comes through a caller's callable;
   `geokachel.net` is a polite default and says so.
3. **No geocoder.** `state=` is required.
4. **A credit is a required field**, in the publisher's exact words, and the
   NOTICE says the MIT licence does not relicense the data.
5. **The image installs it from PyPI, hash-pinned and exact**, so a new state
   arrives by somebody choosing it.
6. **The scheduled check opens an issue, never a red build.**

## Security

The package is what it always was: addresses built from a template and two
integers, or from a name a state's own list gave, validated against a strict
character set and dropped into *our* folder. Extraction changed no fetch.

`NOTICE` states plainly that the project is not affiliated with any
Landesvermessungsamt, the AdV, the BKG, ESA or Copernicus — and the name was
chosen to avoid implying it. "GeoBasis-DE" is the surveying authorities' own
brand and appears only inside credits they require.

## Known Issues

- **A fix to the registry is now four steps**, not one (above). That is the
  price of the split and it was paid knowingly.
- **Nothing checks the two repositories agree.** This app pins 0.1.0; nothing
  yet notices when geokachel's own health check has gone red and a newer
  release carries the fix.
- **Its history is thin**: three commits, because `git subtree split` only
  sees the hour the directory existed. The reasoning lives in these docs, and
  the package's CONTRIBUTING points back here for it.
- **`pointcloud.py` did not move**, so LAZ reading stays in the app for now. It
  is clean enough to follow whenever the laser is wanted outside a garden.
- The copyright line says `JanderHungrige`, on the owner's instruction — and
  the package's URLs said `werthvoll` until then, which is the git commit
  identity and **not** the GitHub account the repository actually lives under.
  Every link in the published metadata would have pointed at nothing.

## Bugs
