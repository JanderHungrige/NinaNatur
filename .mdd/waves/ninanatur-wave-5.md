---
id: ninanatur-wave-5
title: "Wave 5: The insect score and how to raise it"
initiative: ninanatur
initiative_version: 2
status: planned
depends_on: ninanatur-wave-4
demo_state: "A planting shows an insect score and concrete swaps that measurably raise it"
created: 2026-08-27
hash: 8eef7b14
---

# Wave 5 — The insect score and how to raise it

## Scoring model

Counted, not invented. Per species: the number of dependent wild bee species and
the number of Lepidoptera using it as a larval host, from GloBI intersected with
a German checklist. Weighted by nativeness, penalised for double-flowered
cultivars, which are nectarless.

The multiplier that matters is **continuity**: unbroken forage from March to
October is worth more than ten species that all flower in June. This makes the
score **submodular** — each additional June plant adds less than the first March
plant — which is not a mathematical footnote but the reason a greedy swap search
gets close to optimal cheaply.

## Scope

**In:**
- Score a planting, with the contribution of each species visible
- Swap suggestions: same site fit, higher marginal score, ranked by gain
- Explain each suggestion in one sentence ("adds forage in the April gap")

## Risk

A score is a number users will trust more than it deserves. Every component must
be traceable to counted records, and the UI must be able to answer "why this
number" — otherwise it is decoration.

## Definition of done

A planting shows a score, and accepting a suggested swap visibly raises it for a
reason the user can read.
