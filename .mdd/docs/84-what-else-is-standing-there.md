---
id: 84-what-else-is-standing-there
title: What Else Is Standing There
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-19
wave_status: active
depends_on: [80-which-models-and-whose, 81-a-house-with-a-measured-height]
relates: [66-a-tree-is-not-a-wall]
source_files:
  - ninanatur/geo/canopy.py
  - ninanatur/garden/canopies_found.py
  - ninanatur/api/canopies.py
  - ninanatur/garden/building_sync.py
  - frontend/src/components/CanopyBox.tsx
routes:
  - GET /api/v1/gardens/{token}/canopies
  - POST /api/v1/gardens/{token}/canopies/{suggestion_id}
  - DELETE /api/v1/gardens/{token}/canopies/{suggestion_id}
models: [canopy_suggestion]
test_files:
  - tests/test_canopy.py
  - tests/test_canopies_api.py
  - frontend/src/components/CanopyBox.test.tsx
data_flow: mixed
last_synced: 2026-09-06
status: complete
phase: all
mdd_version: 11
tags: [canopy, trees, suggestions, ndom, segmentation]
path: Map/Buildings
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "No species, and none is available: a found tree falls to the canopy model's broadleaf-in-leaf default."
  - "Only states with a fine surface model can find trees at all — Baden-Württemberg's 5 m is refused, and the five states with no service find nothing."
  - "Like everything in this wave, it looks at the garden's rounded location. See tests/test_anchor_precision.py."
---

# What Else Is Standing There

Feature 4 of Wave 19. The single most common thing that shades a German garden
is a large tree, and until now one existed in this model only if somebody drew
it. A neighbour's beech is exactly the thing a person forgets, because it is not
theirs.

## Proposed, never added

A crown, a hedge, a marquee and a badly-mapped building all read as "tall, and
not ground" to a laser. So the surface model proposes and the gardener decides —
the same standing as Wave 16's misplacement warning, and for the same reason.

In the interface, **refusing is exactly as easy as accepting**. A list where the
"no" is the harder click is a list that gets accepted by exhaustion.

And a refusal is remembered rather than deleted: the next recomputation finds
the same tree again, and re-proposing something somebody rejected is how a
suggestion becomes a nuisance. A suggestion has no identity, so a fresh find is
matched to an old one by position — within three metres, because a crown's
centroid moves when its edge cells change, and they change with the season the
flight was made in.

## Four rules, and three of them came from being wrong

Over a Cologne suburb the first version proposed **46 trees**, several of them
nonsense. What the rules are, and what each one is for:

| | | Why |
|---|---|---|
| At least **3 m** tall | | Below that it is a hedge, a car or a washing line — and it shades almost nothing at the angles this model counts |
| At most **45 m** | | The tallest broadleaf in Germany. Above it, a building the footprints missed |
| **6–300 m²** | | A 4 m² blob is a shrub; beyond 300 it is a row or a copse, and one trunk position for a fifty-metre blob is a fiction |
| Crown wider than **height ÷ 8** | new | A twenty-metre thing 1.4 m across is a chimney, a mast, or the corner of a building the mask did not cover. Measured — exactly those appeared |
| **Within 50 m** | new | The obstacle model's own reach. Confirming 46 suggestions one at a time is not a feature |
| **2 m clear of a building** | | A roof and the tree beside it touch in a surface model. Without a margin every building grows a small tree along its northern edge |

With those, the same suburb yields **three** suggestions near the garden, and a
200 m window with 42 buildings yields five — 25.2 m down to 6.5 m, all plausible.

## Blobs, four-connected

Two crowns touching at a single corner are two trees. Joining them would put one
trunk between them, which is where neither tree is.

## Twelve times faster by accident

The building mask recomputed each footprint's bounding box **once per cell** —
twelve million polygon scans over a 400 × 400 window, 3.6 s. Computing the grown
boxes once takes it to 0.3 s. The same answer; it was simply written in the loop.

## What it cannot know

**The species.** No elevation product carries one, and the canopy model wants it
— a crown's transmission depends on whether it drops its leaves. A tree found
here falls to the existing default, broadleaf in leaf, and the box says so in as
many words rather than leaving somebody to assume it was identified.
