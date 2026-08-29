---
id: ninanatur-wave-8
title: "Wave 8: From the map into the garden"
initiative: ninanatur
initiative_version: 10
status: complete
depends_on: ninanatur-wave-7
demo_state: "A user finds their address on a map, outlines the garden, and gets a drawing that already carries the buildings that shade it — with heights it can defend"
created: 2026-08-28
replanned: 2026-08-29
hash: 69ed7adf
---

# Wave 8 — From the map into the garden

## Demo-State

A user finds their address on a map, outlines the garden, and gets a drawing that
already carries the buildings that shade it — with heights it can defend.

## What re-planning measured, and what it changed

The first draft rested on three assumptions. Two were wrong, and both were wrong
in the same direction: they were checked in central Berlin, and gardens are not
in central Berlin.

### Building heights are not in OSM where gardens are

| Area | Buildings | `height` | `building:levels` | neither |
|---|---|---|---|---|
| Kleinmachnow | 2,098 | **0%** | 12% | 88% |
| Berlin-Zehlendorf | 1,505 | **0%** | 22% | 78% |
| Münster-Gievenbeck | 1,309 | **0%** | 25% | 75% |
| Berlin-Mitte *(the first draft's sample)* | 298 | 2% | 66% | 32% |

Zero `height` tags across 4,912 suburban buildings. The planned confidence
ladder had its top two rungs empty exactly where the product is used, and its
"weak, labelled as such" fallback was going to be the normal case.

### OSM has no garden trees

Around one measured plot: 22 buildings within 45 m, and **zero** trees. The
first draft said buildings and trees come from OSM. Buildings do. Trees do not —
and trees are the main thing that shades a garden.

### A 25 m margin is too small

Shadow reach in Berlin at a low sun (15°): a 6 m house casts 22 m, an 8 m house
30 m, a 12 m house 45 m. A margin that only reaches 25 m loses the morning and
evening shade of ordinary houses, which is most of what a garden feels.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | imagery-licence (research) | — | **answered: clears in 8 Bundesländer** | — |
| 1 | map-selection | 31-map-selection | complete | — |
| 2 | object-heights | 32-object-heights | complete | 31 |
| 3 | imagery-objects | 33-imagery-objects | complete (backdrop; recognition deferred) | 0, 31 |

Doc numbers moved up by one: 30 is `30-landing-and-garden-id`. Wave 9's features
move to 34–36 for the same reason.

### 0 — imagery-licence (research, runs first)

**Decided in re-planning: the licence question is answered before anything is
built on imagery, not alongside it.**

What has to be established, per Bundesland: which orthophotos may be used, under
what licence, at what resolution and coverage, and whether the terms permit
derived work in a hosted product. Germany's state surveying offices publish under
Datenlizenz Deutschland with differing terms; the federal WMS refused an
anonymous request.

This is the same rule that kept this project off NaturaDB, and it does not bend
because the data would be convenient.

**Outcome decides feature 3.** If it clears, recognition has a starting point in
the sister project `DinoTraining` — segmentation of roofs and crowns from
orthophotos is what it is built for. If it does not, feature 3 becomes the
fallback below.

### 1 — map-selection (#2.3)

Search an address (Nominatim, verified working today), outline the garden on an
**OSM map**, and convert the selection into a drawing.

The rendered OSM map is the backdrop rather than aerial imagery — decided in
re-planning. It already shows buildings, roads and water, it is open, and it
needs no licence research to start.

**Using it carries obligations**, and they are part of the feature, not
paperwork. The OSMF tile policy requires visible licence attribution, a
`User-Agent` that identifies this application, a valid `Referer` from web pages,
and local caching; it forbids bulk downloading or prefetching tiles, and offers
no SLA. If usage ever outgrows that, the answer is a paid tile provider or our
own — not quietly heavier use of a free service.

One thing that already lines up: the `Referer` header never carries the URL
fragment, and the garden token lives in the fragment. Sending Referer as the
policy requires cannot leak a garden id.

**The margin is 50 m, filtered by reach.** An object is only taken over if its
shadow could reach the garden at all — height ≥ distance × tan 15°. A 12 m house
counts at 45 m, a 2 m fence only at 7. Generous where it matters and quiet
where it does not, which also cuts how many objects the user is shown.

Latitude, orientation and area come from the selection; Wave 3's coordinate entry
becomes the fallback. Latitude is still rounded to 0.1° on the way into storage —
the map knows where the garden is, the database does not need to.

Buildings inside the margin come from OSM via Overpass and land as labelled
objects the user can correct. **Trees do not come from anywhere** and are drawn
by the user, which Wave 7 already supports with kind, height and shading.

### 2 — object-heights (#8, corrected twice)

**Terrain elevation is the wrong data for this.** Open DEMs describe the ground,
and over the twenty metres of a garden the ground barely changes — what shades a
bed is the twelve-metre building next to it. Terrain matters on a real slope, and
then as context rather than as the shading model.

Heights come from objects, in descending confidence:

| Source | Confidence | Reality in a garden suburb |
|---|---|---|
| user-entered (Wave 7 labelling) | authoritative | whatever the user corrects |
| OSM `height` | high | **absent** |
| OSM `building:levels` × storey height | estimated | 12–25% of buildings |
| neighbourhood default | estimated, and asked for | the remaining 75–88% |

**One question per garden, not one per building** — decided in re-planning.
The user answers *"Wie hoch ist die Nachbarbebauung typischerweise?"* once
(detached house ≈ 7 m, terrace ≈ 9 m, apartment block ≈ 14 m), and that fills
every building with no recorded height. Individual buildings stay correctable on
the plan.

The alternative was confirming each one, which in the measured example is 13
confirmations before the first plant suggestion — a wall at the point where
somebody has just arrived.

Every height still carries where it came from, and the UI distinguishes a
measured height from an assumed one. **A shading model that presented an assumed
height as a measured one would be the same lie as a filter that hides what it
dropped.**

### 3 — imagery-objects (#2.4) — blocked on feature 0

Recognise buildings, trees and paths from aerial imagery and place them for the
user to correct.

**No imagery may be used until its licence is established.**

If feature 0 clears it: segmentation via the `DinoTraining` pipeline, and trees
finally arrive automatically.

If it does not: this feature narrows to refining what OSM already gives —
snapping building outlines, splitting terraces — and trees stay user-drawn.

## Risks

- **Trees remain manual for the whole wave** unless feature 0 clears. That is the
  main gap between this wave's demo state and a garden that models its own shade
  well, and it is stated rather than hidden.
- Overpass is a shared free service, as is the tile server. Cache aggressively and
  rate-limit, or be a bad citizen of infrastructure this project depends on.
- The neighbourhood default is one number standing in for 75–88% of the buildings
  around a garden. It is the honest option available, not a good measurement.

## Open Research

- [x] **Feature 0 — answered.** Orthophotos clear under dl-de/by-2-0 or CC-BY-4.0
      in at least eight Bundesländer, each with its own service and required
      credit; there is no federal source (BKG: 403). See 33-imagery-objects.
- [ ] Does a storey height of 3 m hold for German housing, or does the
      neighbourhood answer need its own numbers per building type?

## Definition of done

Entering an address produces a drawing with the garden outlined, neighbouring
buildings placed with heights, every assumed height marked as assumed — and the
bed light values change accordingly.
