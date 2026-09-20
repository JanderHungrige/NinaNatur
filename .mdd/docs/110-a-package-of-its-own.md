---
id: 110-a-package-of-its-own
title: A Package of Its Own
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [102-which-tiles-and-whose, 103-a-tile-not-a-service, 109-is-it-still-there]
relates: [106-which-source-said-so, 17-terrain-window]
source_files:
  - packages/geokachel/pyproject.toml
  - packages/geokachel/geokachel/__init__.py
  - packages/geokachel/geokachel/addressing.py
  - packages/geokachel/geokachel/net.py
  - packages/geokachel/geokachel/cli.py
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
sister_projects: []
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

## The registry stays one commit away

The strongest argument against extracting this was that the registry is both
the only thing worth packaging and the thing that churns most — a state moves a
file and a fix becomes publish-then-bump instead of edit-then-deploy.

That is answered by **not depending on PyPI**. The package lives in this
repository and the image installs it from the same commit:

```dockerfile
COPY packages ./packages
RUN pip install --prefix=/install --require-hashes -r requirements.txt \
 && pip install --prefix=/install --no-deps ./packages/geokachel \
 && pip install --prefix=/install --no-deps .
```

`--no-deps` because numpy, defusedxml and requests are already in the
hash-locked lock. Publishing to PyPI is an occasional act, not a dependency.

## The check ships with it

Doc 109's health check is `geokachel check`, so whoever installs the package
gets the means to find out that a state moved — not only this app. It runs
weekly in `.github/workflows/sources.yml`, and **it does not fail the build**:
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
5. **The image installs it from this commit**, so a registry fix stays one
   commit.
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

- **Not published to PyPI yet.** The wheel builds, installs into a clean
  environment and works there; the release is the owner's to make.
- **The package's tests live in the repository's `tests/`**, not beside it.
  They exercise it fully and run in CI; a standalone repository would want them
  moved.
- **`pointcloud.py` did not move**, so LAZ reading stays in the app for now. It
  is clean enough to follow whenever the laser is wanted outside a garden.
- The copyright line says `werthvoll`, the owner's public git identity, because
  guessing a legal name into a licence is worse than asking.

## Bugs
