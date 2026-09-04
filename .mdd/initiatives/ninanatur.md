---
id: ninanatur
title: NinaNatur
status: active
version: 20
hash: e81fb14b
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

### Species information comes from an API and is cached, not crawled

Asked and answered while planning Wave 6. Wikipedia's REST API returns a summary
and a thumbnail and redirects the scientific name to the German article
(*Achillea millefolium* → *Gemeine Schafgarbe*). It is CC-BY-SA 4.0, so
attribution and a link back are required.

Fetched on demand and cached **on the volume**, not baked into the shipped
catalogue: a live fetch per view adds latency and a dependency to a page that has
neither, and storing summaries would go stale and re-inflate an image just
trimmed to 10 MB. Same lifecycle split as gardens, for the same reason.

### Heights come from objects, not from terrain

Open elevation data describes the ground. Over the twenty metres of a garden the
ground barely changes — what shades a bed is the twelve-metre building beside it.
Heights are therefore sourced from user input, then OSM `height`, then
`building:levels`, then a type default, each carrying its confidence.

Measured before deciding: of six central Berlin buildings, one carried `height`,
two `building:levels`, three neither. A model that trusted OSM heights would
silently under-shade half the gardens in the country.

### Aerial imagery is blocked until its licence is established

OSM is open data; aerial imagery generally is not. German state orthophotos exist
under Datenlizenz Deutschland with terms varying by Bundesland, and the federal
WMS refused an anonymous request. No imagery is used until that is settled — the
same rule that kept this project off NaturaDB, and it does not bend because the
data would be convenient.

## Waves

| Wave | File | Demo-state | Status |
|------|------|------------|--------|
| Wave 1 | waves/ninanatur-wave-1.md | ninanatur.w3rth.de serves a branded page, and a push to main replaces it automatically | complete |
| Wave 2 | waves/ninanatur-wave-2.md | The API answers "which plants suit these site conditions", every value citing its source | complete |
| Wave 3 | waves/ninanatur-wave-3.md | Beds get a computed light value from the real sun path | complete |
| Wave 4 | waves/ninanatur-wave-4.md | The bloom year, month by month, with forage gaps marked | complete |
| Wave 5 | waves/ninanatur-wave-5.md | An insect score on counted German relations, and swaps that raise it | complete |
| Wave 6 | waves/ninanatur-wave-6.md | A catalogue you can browse: German names, photos, filters, month-click | complete |
| Wave 7 | waves/ninanatur-wave-7.md | The garden drawn rather than typed, labelled by clicking, playing through the year | complete |
| Wave 8 | waves/ninanatur-wave-8.md | An address becomes a drawing carrying the surroundings that shade it | complete |
| Wave 9 | waves/ninanatur-wave-9.md | What is visible from where you stand, and accounts without a required email | complete |
| Wave 10 | waves/ninanatur-wave-10.md | The garden drawn as a garden, with shadows that have a shape | complete |
| Wave 11 | waves/ninanatur-wave-11.md | Draw first, say what it is afterwards — shapes, vertices, and a skin that follows the label | complete |
| Wave 12 | waves/ninanatur-wave-12.md | The plan gets out of its own way — tools on top, drawing that works on the first click, and every element findable | complete |
| Wave 13 | waves/ninanatur-wave-13.md | A front door that looks like one — sign-in top right, one way in, and a page that breathes | complete |
| Wave 14 | waves/ninanatur-wave-14.md | A plan that looks painted, not plotted — bloom as dots, deletable elements, and the street outside | complete |
| Wave 15 | waves/ninanatur-wave-15.md | What is in the bed, and getting it out again | complete |
| Wave 16 | waves/ninanatur-wave-16.md | The shade switch: sun and shade hours as a map over the garden | planned |
| Wave 20 | waves/ninanatur-wave-20.md | A finished plan split across as few nurseries as possible | planned |
