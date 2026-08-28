---
id: ninanatur-wave-4
title: "Wave 4: Plantings and the bloom year"
initiative: ninanatur
initiative_version: 6
status: planned
depends_on: ninanatur-wave-3
demo_state: "A user picks suggested species into a bed and sees the garden's bloom year month by month, with forage gaps marked and explained"
created: 2026-08-27
hash: d32d8f4f
---

# Wave 4 — Plantings and the bloom year

## Demo-State

A user picks suggested species into a bed and sees the garden's bloom year month
by month, with forage gaps marked and explained.

*(Not complete until this can be demonstrated against the running app.)*

## The gap found while planning

Beds carry their site conditions but **nothing links a bed to the species planted
in it**. There is no `planting` table, so there is literally no data a timeline
could be drawn from. That is the first feature, not an afterthought.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | planting-model | .mdd/docs/12-planting-model.md | complete | — |
| 2 | bed-suggestions | 13-bed-suggestions | planned | 12 |
| 3 | bloom-timeline | 14-bloom-timeline | planned | 12 |
| 4 | timeline-ui | 15-timeline-ui | planned | 13, 14 |

### 1 — planting-model

`planting`: a bed, a taxon, a quantity, and when it was added. Plus API to add
and remove. This is what turns a bed from a patch of ground into a plan.

Deleting a bed removes its plantings; deleting a garden removes everything, by
the same cascade Wave 3 established.

### 2 — bed-suggestions

`GET /api/v1/gardens/{token}/beds/{bed_id}/suggestions` — the Wave 2 plant search
run against a bed's own derived site vector, so the user never types a number.

**This wires the connection that has been missing since Wave 2.** The search
endpoint exists, the typed client method exists, and nothing calls either. It is
the smallest step to the first genuinely useful moment in the product.

Growth form becomes a default filter here: a shady damp bed currently returns
*Tsuga canadensis*, a hemlock tree, ahead of the woodland sedges. Correct fit,
useless suggestion — noted in `06-plants-api` and fixed here, where beds have a
size to judge against.

### 3 — bloom-timeline

Twelve months per bed and per garden. **Months, not half-months** — measured, not
assumed: GIFT stores integer month bounds, so half-month buckets would be the
same invented precision this project refuses everywhere else.

**Wrapping intervals must be handled explicitly.** 132 species have a start month
after their end month (November to February and similar). Naive `range(start, end)`
yields an empty set for exactly the species that cover the hardest part of the year.

Two weightings over one computation:

| Mode | A month counts as covered when | Default |
|---|---|---|
| **Forage** | enough is flowering *that insects use*, weighted by the counted German partner relations from Wave 2 | ✅ |
| **Visual** | enough is flowering at all, by area | |

The user switches with a checkbox. Forage is the default because it is the point
of the product; a month full of nectarless double-flowered cultivars is correctly
a gap, and only the forage weighting can say so.

A gap is a run of consecutive months below the threshold within March–October.
The winter trough is not a finding.

### 4 — timeline-ui

The twelve-month view, gaps marked, the mode checkbox, and per-bed detail. Each
gap states its own reason in a sentence — "nothing flowers for insects between
mid-March and April" is the output that makes the feature worth having.

Same rules as every layer: unknown is unknown, colour tints where known and shows
neutral-with-a-label where not.

## Risks

- **A timeline of an empty garden is the first thing a new user sees.** The empty
  state has to teach rather than show twelve empty bars.
- **The forage threshold is a judgement call**, like the sun-hour mapping before
  it. It belongs in one documented constant with its reasoning, not scattered.
- Suggestions are computed over 4,437 candidates per request. Fine for one bed;
  worth measuring before a whole garden is scored at once.

## Open Research

None blocking. Gap definition settled: insect-weighted by default, visual when
the user unchecks it.

## Definition of done

Against the running app: add suggested species to a bed, see the garden's twelve
months fill in, watch a gap appear and disappear as species are added, and switch
between forage and visual weighting to see the difference.
