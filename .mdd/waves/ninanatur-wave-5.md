---
id: ninanatur-wave-5
title: "Wave 5: What the planting is worth to insects"
initiative: ninanatur
initiative_version: 8
status: planned
depends_on: ninanatur-wave-4
demo_state: "A planting shows an insect score built on counted German relations, and suggested swaps that measurably raise it — each explained in a sentence"
created: 2026-08-27
hash: d9df1140
---

# Wave 5 — What the planting is worth to insects

## Demo-State

A planting shows an insect score built on counted German relations, and suggested
swaps that measurably raise it — each explained in a sentence.

## What planning found

The original outline promised weighting by nativeness and by wild-bee counts.
**Neither is in the database**, and the first is worse than a missing feature:

- `occurs_de` means *recorded here*, not *native here*. It is true of
  *Vitis riparia*, a North American grape. The landing page says "heimischen
  Pflanzen" and nothing backs that claim.
- Partner taxonomy was lost when the insect checklist switched to the name facet
  in Wave 2 — `insect_de` has names and occurrence counts, no family or order. A
  bee and a fly are indistinguishable.

Both are obtainable, verified before planning rather than assumed:

| Need | Source | Checked |
|---|---|---|
| native / introduced in Germany | GBIF species distributions (WCVP) | *Achillea millefolium* → NATIVE, *Tsuga canadensis* → INTRODUCED |
| bees, butterflies, hoverflies in Germany | the same occurrence facet used for plants, per clade | Lepidoptera `797`, Syrphidae `6920` resolve exactly |

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | nativeness | .mdd/docs/16-nativeness.md | complete | — |
| 2 | insect-groups | .mdd/docs/17-insect-groups.md | complete | — |
| 3 | insect-score | .mdd/docs/18-insect-score.md | complete | 16, 17 |
| 4 | swap-suggestions | .mdd/docs/19-swap-suggestions.md | complete | 18 |
| 5 | score-ui | 20-score-ui | planned | 19 |

### 1 — nativeness

Ingest `establishmentMeans` per species for Germany. **Two shapes must both be
parsed**, checked against real responses:

- structured — `locality: "Germany"`, `establishmentMeans: "NATIVE"`
- unstructured — one long locality string listing every region, with `[I]`
  marking introduced: *Vitis riparia* appears as `Germany [I]` inside a wall of
  text, with `establishmentMeans: None`

Parsing only the first shape would silently mark every species in the second as
unknown — and those include the invasive ones the product most needs to name.

**Consequence beyond the score:** suggestions default to native species. That is
not a new product decision, it is the site's existing promise finally being kept.
A toggle exposes the rest, labelled.

Unknown nativeness stays unknown and is shown as such — the rule this project
runs on everywhere else.

### 2 — insect-groups

German bees, butterflies and hoverflies, each from one occurrence facet per clade
— the same generalisation of `fetch_german_species_keys` already used twice.
Partner names are then classified by set membership, needing no per-insect
lookup.

Restores what Wave 2 dropped, and turns "1,055 partners" into "40 wild bee
species, 12 butterflies" — a statement a gardener can act on.

### 3 — insect-score

Per planting: counted German partners by group, weighted by nativeness.

**The multiplier that matters is continuity.** Unbroken forage from March to
October is worth more than ten species that all flower in June. That makes the
score **submodular** — each additional June plant adds less than the first March
plant — which is not a footnote but the reason a greedy swap search gets close to
optimal cheaply.

Every component must be traceable to counted records. A score a user cannot
interrogate is decoration, and this one will be trusted more than it deserves.

### 4 — swap-suggestions

For each candidate swap: same bed fit, higher marginal score, ranked by gain.
Each carries one sentence of why — "adds forage in the April gap" — because the
number alone does not tell anyone what to do.

Submodularity is what makes the greedy search defensible; the doc must state that
rather than leave it as an accident of implementation.

### 5 — score-ui

The score with its components visible, the swaps actionable, and the same
accessibility rules as the timeline: everything a colour conveys is also text,
and the empty state teaches.

## Risks

- **A score invites false precision.** It rests on GloBI's research coverage,
  which is uneven — *Salix caprea* leads with 1,055 partners partly because
  willows are well studied. The UI must say what the number is, and is not.
- Nativeness for ~4,400 species is one API call each. Cacheable and one-off, but
  it is an hour of ingest.
- The catalogue grows again; check the shipped size stays reasonable.

## Open Research

None blocking. Both data gaps were verified obtainable before this plan was
written.

## Definition of done

Against the running app: a planting shows its score with components, accepting a
suggested swap raises it visibly, and every number can be traced to counted
records.
