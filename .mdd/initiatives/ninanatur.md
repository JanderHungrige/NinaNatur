---
id: ninanatur
title: NinaNatur
status: active
version: 2
hash: 6b887abf
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

## Decisions

Resolved 2026-08-27, after checking what the data actually allows.

### Flower colour — ship what exists, mark the rest unknown

The 527 species with a colour keep it; everything else gets an explicit
*unknown* placeholder. Colour is therefore a **soft filter** — it may rank and
tint, but must never silently exclude a species whose colour is merely unrecorded,
because that would quietly hide most of the catalogue.

The UI must show "colour unknown" rather than guessing or omitting. An honest gap
is usable; an invented value is not.

Two follow-ups, both deferred and neither blocking Wave 4:
- **Image classification.** GBIF and iNaturalist hold millions of plant photos; a
  flower-region colour classifier would cover all 3,087. The DINOv2/v3 pipeline in
  the DinoTraining project is the obvious starting point. Its own sub-project.
- **BfN request.** FloraWeb is a federal resource and its `robots.txt` blocks the
  species pages, so an extract has to be asked for rather than fetched.

Ruled out by measurement, not assumption: Wikidata carries flower colour for 122
taxa worldwide; BiolFlor now returns only error pages.

### Insect checklist — GBIF, no new source

GloBI relations are worldwide and must be intersected with insects actually
recorded in Germany. That list comes from the same GBIF occurrence facet already
used for the plants (11.6M insect occurrences, `taxonKey=216`), so this needs a
generalisation of existing code rather than a new integration.

### Persistence — shareable link now, accounts later

Each plan gets an unguessable URL. No login, no password handling, no user data
to protect, no auth wave before the product has proven anyone wants it.

**The consequence that must not be forgotten:** the plan table carries a nullable
`owner_id` from the first migration. Adding it later means migrating live plans;
adding it now costs one column that stays empty until accounts exist.

### Catalogue — all 3,087 core-complete species

No curated subset. Filtering is by site conditions and design intent only, so
unusual but fitting species stay visible. Commercial availability is a Wave 6
concern, where the shopping list already has to reason about what is stocked —
filtering for it earlier would be guessing.

## Open Product Questions

- [ ] Which nurseries to approach for Wave 6, and on what terms. Deliberately
      deferred — deciding now binds us to assumptions that will have changed by
      then. The constraint is fixed regardless: feeds by agreement, not scraping.
- [ ] Wave 2 must settle source priority when EIVE and GIFT disagree on the same
      axis, and how wide a tolerance band around a bed's values still counts as
      "fits". That single number decides how generous every suggestion feels.
- [ ] Wave 3 must settle whether light is computed from orientation and obstacle
      geometry, or simply picked by the user as sunny/partial/shade.

## Waves

| Wave | File | Demo-state | Status |
|------|------|------------|--------|
| Wave 1 | waves/ninanatur-wave-1.md | ninanatur.w3rth.de serves a branded NinaNatur page, and a push to main replaces it automatically within a minute | complete |
| Wave 2 | waves/ninanatur-wave-2.md | The API answers "which plants suit these site conditions" from the ingested open data, every value citing its source | planned |
| Wave 3 | waves/ninanatur-wave-3.md | A user draws beds on a garden floor plan, sets each bed's conditions, and the plan persists | planned |
| Wave 4 | waves/ninanatur-wave-4.md | A bed shows fitting species plus a bloom calendar for the year, with gaps marked | planned |
| Wave 5 | waves/ninanatur-wave-5.md | A planting shows an insect score and concrete swaps that measurably raise it | planned |
| Wave 6 | waves/ninanatur-wave-6.md | A finished plan turns into a shopping list split across as few nurseries as possible | planned |
