---
id: ninanatur
title: NinaNatur
status: active
version: 1
hash: 5a2485f9
created: 2026-08-27
---

# NinaNatur

## Overview

A garden planner built on openly licensed plant data. The user draws their
garden as a floor plan, defines beds with site conditions and design intent
(colour, height, when it should flower), and NinaNatur suggests native plants
that actually fit. It then simulates the year: what blooms where and when, in
the right colour, with bloom gaps flagged. An insect score rates the planting on
counted plant-animal relations, and suggests swaps that raise it. Finally it
consolidates the shopping list so the user orders from as few nurseries as
possible.

The data foundation is deliberately open (EIVE, GBIF, GIFT, GloBI) rather than
licensed from an existing plant database — see CLAUDE.md for why, and what that
costs in coverage.

**Deployment:** `ninanatur.w3rth.de` → `172.17.0.1:4000`, following the
3dmap/BattleFuel pattern: GitHub Actions builds and pushes to GHCR, the host
polls with a cron-driven `auto-deploy.sh` and rolls the container. CI never
SSHes into the host. TLS and domains are handled by Nginx Proxy Manager.

## Open Product Questions

- [ ] Flower colour is only ~13% covered by the open data (590 of ~4,400 candidates). Close it with Wikidata, a structured determination flora, or hand-curating the ~600 horticulturally relevant species?
- [ ] GloBI interaction records are worldwide. Which German insect checklist do we intersect against so the score reflects a German garden rather than global research effort?
- [ ] Which nurseries do we integrate first, and do we approach them for affiliate/feed access rather than scraping?
- [ ] Do users need accounts? Saving a garden plan implies persistence per user — or is a shareable link enough for v1?
- [ ] Does the deployment need a dev environment alongside prod (3dmap runs :3005 dev / :3006 prod)? Assumed yes, dev on :4001.
- [ ] Is the ~3,100 core-complete species pool the shipping catalogue, or do we curate a smaller, horticulturally vetted subset on top?

## Waves

| Wave | File | Demo-state | Status |
|------|------|------------|--------|
| Wave 1 | waves/ninanatur-wave-1.md | ninanatur.w3rth.de serves a branded NinaNatur page, and a push to main replaces it automatically within a minute | planned |
| Wave 2 | waves/ninanatur-wave-2.md | The API answers "which plants suit these site conditions" from the ingested open data, every value citing its source | planned |
| Wave 3 | waves/ninanatur-wave-3.md | A user draws beds on a garden floor plan, sets each bed's conditions, and the plan persists | planned |
| Wave 4 | waves/ninanatur-wave-4.md | A bed shows fitting species plus a bloom calendar for the year, with gaps marked | planned |
| Wave 5 | waves/ninanatur-wave-5.md | A planting shows an insect score and concrete swaps that measurably raise it | planned |
| Wave 6 | waves/ninanatur-wave-6.md | A finished plan turns into a shopping list split across as few nurseries as possible | planned |
