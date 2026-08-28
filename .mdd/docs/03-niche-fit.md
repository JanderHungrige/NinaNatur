---
id: 03-niche-fit
title: Niche-Width Fit Scoring
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-2
wave_status: complete
depends_on: [01-trait-ingest]
relates: [04-trait-resolve, 06-plants-api]
source_files:
  - ninanatur/fit/__init__.py
  - ninanatur/fit/score.py
  - ninanatur/ingest/sources/eive.py
routes: []
models:
  - trait
test_files:
  - tests/test_fit_score.py
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [fit, ellenberg, niche-width, ranking, eive]
path: Matching/Fit
integration_contracts:
  - function: score_species(site, species)
    when: any ranking or filtering of species against a bed
    note: returns a graded score plus a per-axis explanation — callers must never re-derive fit from raw indicator values
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 03 — Niche-Width Fit Scoring

## Purpose

Decide how well a species fits a bed, using the niche width EIVE ships alongside
each indicator value rather than one tolerance band applied to every species.
This is the function that decides whether suggestions feel considered or random,
so it is built first and on its own.

## Data Model

Five new trait keys, ingested from the `*.nw3` columns of the same EIVE file
already on disk:

`ellenberg_l_nw`, `ellenberg_m_nw`, `ellenberg_n_nw`, `ellenberg_r_nw`,
`ellenberg_t_nw` — all on the same 0–10 scale as the values themselves.

## The score

For one axis, given the bed's target `t`, the species' optimum `v` and its niche
width `w`:

```
z          = |t - v| / (w / 2)        distance in half-niche-widths
axis_score = exp(-0.5 * z²)           1.0 at the optimum, decaying outward
```

Dividing by the width is the whole point: the same absolute distance means
something different for *Urtica dioica* (light niche width 7.91) than for a
species at the 0.48 end of the range.

**Axes combine as a geometric mean, not an arithmetic one.** A species cannot
offset hopeless light with excellent moisture — a plant that needs shade will not
survive full sun because the soil is nice. The geometric mean collapses toward
zero when any single axis is bad, which is the behaviour a gardener would expect
and an arithmetic mean would hide.

### Why this satisfies "generalists must not drown everything"

A species whose optimum sits exactly on the bed scores 1.0 — the maximum. A
generalist some distance away scores strictly less, however wide its niche. So a
wide niche buys breadth (it matches many beds) but never rank (it cannot beat a
species that actually wants these conditions). No cap is needed, and none is
applied.

## Business Rules

- **A missing axis is skipped, not scored zero.** A species without a moisture
  value is scored on the axes it has, and the response says which. Treating
  absent data as a bad match would silently bury every incompletely recorded
  species.
- **A species with no usable axis at all returns `None`, not 0.0.** "Unknown fit"
  and "bad fit" are different answers and must not be rendered the same.
- **Missing niche width falls back to the population median for that axis**, and
  the explanation marks the axis as estimated. Refusing to score would discard
  otherwise usable species.
- **Every score carries a per-axis explanation** — distance in half-widths and a
  band (`optimal` / `suitable` / `borderline` / `unsuitable`). Wave 4 needs to say
  "borderline on moisture", not print a number.

## Dependencies

`01-trait-ingest` — the trait table and the EIVE adapter this extends.

## Security

Pure computation over values already in the database. No external input, no I/O.

## Known Issues

- Niche widths cover 4,384 of the 4,437 candidates; the rest fall back to the
  population median and are flagged `width_estimated` in the explanation.

## Bugs

(none yet)
