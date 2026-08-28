---
id: ninanatur
title: NinaNatur
status: active
version: 9
hash: ee07e5dd
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

### Bed light — computed from the real sun path

Not three categories, and not an orientation lookup: sun altitude and azimuth for
the garden's location, shadows cast by placed obstacles, sampled across the
growing season.

The mapping from sun hours to Ellenberg L stays a documented convention in one
place — sun hours are physical, Ellenberg L is ecological, and pretending the
conversion is exact would be the kind of invented precision this project avoids
everywhere else.

Location is stored rounded to 0.1° (~11 km): solar angles do not care, and a
garden's exact coordinates are personal.

*Later:* the sister project 3dmap (`/opt/3dmap2`) carries height-profile logic
that could replace hand-placed obstacle heights with real terrain.

### Bloom gaps — insect-weighted by default, visual on request

A checkbox, defaulting to the forage view: a gap is a month when little flowers
*that insects use*, weighted by the counted German partner relations. A month
full of nectarless double-flowered cultivars is then correctly a gap, which only
this weighting can express. Unchecking it falls back to bloom area alone, for
users planning purely for looks.

Measured while planning, and both correcting earlier assumptions: the phenology
data is **month** resolution, so the half-month buckets sketched in the original
Wave 4 outline would have been invented precision; and 132 species have flowering
intervals that wrap the year end, which naive range arithmetic drops silently —
precisely the species covering the hardest part of the year.

### Native means native, and the site has been claiming it without evidence

`occurs_de` means *recorded in Germany*, which is true of *Vitis riparia*, a
North American grape. The landing page promises "heimischen Pflanzen" and nothing
in the database backs it. Wave 5 ingests `establishmentMeans` from GBIF/WCVP and
makes native the default for suggestions — not a new product decision, the
existing promise finally kept.

Insect taxonomy was lost in Wave 2 when the checklist switched to the name facet,
so a bee and a fly are currently indistinguishable. Restored the same way the
plants were: one occurrence facet per clade.

Both were verified obtainable before being planned, not assumed.

### Catalogue — all 3,087 core-complete species

No curated subset. Filtering is by site conditions and design intent only, so
unusual but fitting species stay visible. Commercial availability is a Wave 6
concern, where the shopping list already has to reason about what is stocked —
filtering for it earlier would be guessing.

### Bed fit — per-species niche width, scored not thresholded

EIVE ships a niche width per species per axis (0.48-10.0, median 3.03) alongside
each indicator value. Fit uses that width rather than one fixed tolerance band, so
a generalist like *Urtica dioica* (light niche width 7.91) is treated differently
from a species with a narrow one.

Expressed as a **graded score, not a yes/no**: how centrally the bed sits within
the species' niche. This is what keeps a very wide niche from making a species
match everywhere and dilute every suggestion — it does match widely, but never
outranks a species whose optimum is exactly this bed.

Requires ingesting the `*.nw3` columns, which are in the EIVE file already on disk.

### Source priority — measured, not assumed

Checked against the database: EIVE and GIFT overlap in **zero** trait keys. EIVE
owns the Ellenberg axes, GIFT owns height, phenology, colour and form. There is no
conflict to resolve today. `resolve_trait()` still exists for when a third source
arrives, but it needs no arbitration policy yet.

## Open Product Questions

None blocking. Remaining decisions are recorded in the wave that must answer them:
sun-hour derivation in Wave 3, nursery partners in Wave 6.

## Waves

| Wave | File | Demo-state | Status |
|------|------|------------|--------|
| Wave 1 | waves/ninanatur-wave-1.md | ninanatur.w3rth.de serves a branded NinaNatur page, and a push to main replaces it automatically within a minute | complete |
| Wave 2 | waves/ninanatur-wave-2.md | The API answers "which plants suit these site conditions" from the ingested open data, every value citing its source | complete |
| Wave 3 | waves/ninanatur-wave-3.md | A user draws beds on a garden plan, places obstacles, and each bed gets a computed light value from the real sun path | complete |
| Wave 4 | waves/ninanatur-wave-4.md | A user picks suggested species into a bed and sees the garden's bloom year month by month, with forage gaps marked | complete |
| Wave 5 | waves/ninanatur-wave-5.md | A planting shows an insect score built on counted German relations, and swaps that measurably raise it | planned |
| Wave 6 | waves/ninanatur-wave-6.md | A finished plan turns into a shopping list split across as few nurseries as possible | planned |
