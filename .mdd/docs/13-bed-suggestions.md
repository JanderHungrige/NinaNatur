---
id: 13-bed-suggestions
title: Plant Suggestions for a Bed
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-4
wave_status: complete
depends_on: [12-planting-model, 06-plants-api]
relates: [03-niche-fit, 15-timeline-ui, 23-catalogue-filters, 25-woody-and-birds, 67-sun-plant-in-a-shade-spot]
source_files:
  - ninanatur/api/suggestions.py
  - ninanatur/api/search.py
  - ninanatur/api/filters.py
  - ninanatur/api/schemas_plants.py
  - ninanatur/api/parasites.py
  - ninanatur/fit/rank.py
  - ninanatur/garden/light_state.py
  - frontend/src/components/SuggestionList.tsx
  - frontend/src/components/SuggestionLight.tsx
  - frontend/src/components/SuggestionRow.tsx
  - frontend/src/garden/useComputeShade.ts
routes:
  - GET /api/v1/gardens/{token}/beds/{bed_id}/suggestions
models: []
test_files:
  - tests/test_bed_suggestions.py
  - tests/test_light_suggestions.py
  - tests/test_suggestion_rank.py
  - tests/test_parasites_hidden.py
  - tests/test_light_model_version.py
  - frontend/src/components/SuggestionList.light.test.tsx
  - frontend/src/components/SuggestionRow.test.tsx
  - frontend/src/garden/useComputeShade.test.ts
data_flow: reads-existing
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [suggestions, fit, growth-form, api, gardens, insect-value, parasites, light]
path: API/Suggestions
integration_contracts: []
satisfies_contracts:
  - from: 03-niche-fit
    function: score_species(site, species)
    when: ranking suggestions for a bed
    status: done
    verified_at: "ninanatur/api/search.py:90"
security_read_sites: []
known_issues: []
sister_projects: []
---

# 13 — Plant Suggestions for a Bed

## Purpose

Run the Wave 2 plant search against a bed's own derived site vector, so the user
never types an Ellenberg number.

**This closes a gap that has been open since Wave 2.** The search endpoint exists
and the typed client method exists, and nothing has ever called either. It is the
smallest step to the first genuinely useful moment in the product.

## Endpoint

`GET /api/v1/gardens/{token}/beds/{bed_id}/suggestions`

| Parameter | Default | Notes |
|---|---|---|
| `limit` | 20 | ≤ 100 (the frontend asks for 50, doc 90) |
| `colour` | — | soft, as everywhere |
| `height_min`, `height_max`, `flowering_month`, `growth_form`, `include_unknown` | — | `23-catalogue-filters` |
| `include_trees` | `true` | woody plants in a shortlist of their own since Wave 6 (`25-woody-and-birds`) |
| `include_introduced` | `false` | the product promises native plants (`16-nativeness`) |
| `exclude_planted` | `true` | already in the bed, so not a suggestion |
| `include_light_unsuitable` | `false` | see "The light" below |

The bed's own `ellenberg_l/m/n/r` become the site vector. A bed with no computed
light is still usable — the axes it has are scored, which is the `03-niche-fit`
rule — and the response says so in `light_state`, below. Until 2026-09-21 it
said so only in `site_axes`, which the frontend never read: the list claimed
"gewertet nach den Standortwerten dieses Beetes" for a ranking on soil alone.

## The light (owner review #9, 2026-09-21)

The owner asked whether suggestions follow the sun calculation, since
half-shade plants should not go in full sun. They did rank by it, but a light
mismatch only lowered a species' score, so narrow filters brought shade plants
back up. Three changes that morning, and the same evening a second word —
"nicht nur Sonne sondern auch Schatten … für die Sonnenstunden/Schatten die
best passendste Pflanze" — that made the cut symmetric and the order new (see
"The order" below):

- **Unsuitable light is refused, either way.** A species whose L band is
  *unsuitable* (more than 1.5 niche half-widths away, `03-niche-fit`) is left
  out — too bright for it or too dark. The morning's version cut only too
  bright (a shade plant in full sun scorches; a sun plant in shade merely
  flowers less), but ranked down, sun plants still filled a shade bed's list
  whenever filters narrowed it, and a shade bed deserves its best fit as much
  as a sunny one. *Borderline* stays, and the order prices it. A species with
  no L value stays, whatever `include_unknown` says: a gap in the data is not a
  mismatch. The cut is counted under the filter-report key `light` (`excluded`:
  left out; `unknown`: kept without an L value), and the list says "N Arten,
  denen das Licht hier nicht passt, sind ausgeblendet".
  `include_light_unsuitable=true` — the name kept, the meaning widened to both
  directions — shows them, ranked last; FilterControls offers it as "auch Arten
  zeigen, denen das Licht hier nicht passt". The planting improvements
  (`19-swap-suggestions`) apply the same cut; the catalogue search, `GET
  /plants`, does not.
- **The woody shortlist takes only what the light suits,** the same cut, and
  since the evening the same order as the main list (room left out, doc 25). It
  once gave a full-sun bed, a semi-shade bed and a bed with no light the same
  eight willows.
- **`light_state`: `missing`, `stale` or `current`.** Missing: the bed has no
  light value — drawn after the last press of the button, since nothing
  computes light on a write (`lighting.py`). Stale: the stored sun map's
  signature no longer matches the garden's — the comparison the map's own
  `stale` flag makes (`api/light.py::_read` calls the same
  `light_state.current_signature`, so the map and the list cannot disagree).
  Also stale when there is no stored map to say what the value was computed
  from. Measured on 2026-09-21 at about 4 ms per request
  (a real 200 × 200 terrain window, 40 houses, 20 beds of 10 plantings),
  nearly all of it decoding the terrain window. A cheaper timestamp test was
  not available: `garden.updated_at` is not touched when an element moves.
  The list replaces "gewertet nach den Standortwerten" with the reason and a
  „Schatten berechnen“ button — the sun panel's rebuild, which re-reads the
  garden, then the list re-read once that rebuild has landed (it counts its
  landings; a refresh meanwhile or a failed rebuild does not count). Light is **not** computed
  inside the suggestion request: that costs seconds on a big garden.

The signature counts only the plantings that shade (`lightview.shading_taxa`:
species whose recorded height reaches `canopy.MIN_SHADING_HEIGHT_M`, the plants
the light model turns into crowns), so a perennial planted from the list leaves
the list and the map current, and a shrub makes both stale.

**The bed's light is on EIVE's scale since the evening** (doc 07, "Sun hours to
Ellenberg L"): straight lines between anchors at 0 / 1.5 / 2.5 / 4 / 6 / 8 h →
2.5 / 3.75 / 5.0 / 6.25 / 7.5 / 9.0, each the old classic rung carried through
EIVE's rescale (L − 1) × 1.25. The staircase it replaced (3–8) squeezed every
bed towards the middle: full sun read as classic 7.4, deep shade as 3.4, so
both cuts sat in the wrong place. The signature carries `LIGHT_MODEL`, so every
stored map and every bed list read *stale* once and offer the button; a bed
keeps its old value until it is pressed. What is left for the owner: a bed's
light is still the mean over its cells, which a bed half in sun and half in
shade does not have anywhere.

## The order (owner, 2026-09-21)

"Die vorgeschlagenen Pflanzen sollten nach besten Wachstumsbedingungen +
Insektenwert gerankt werden." Until then the list was ordered by fit alone and
ignored insect value; the woody shortlist by partners alone and ignored fit.
Both now follow one rule (`fit/rank.py`):

    rank = growing × (1 + 0.1 × insect)

- **growing** is `score_species`'s fit — the geometric mean over L, M, N, R,
  each axis against the species' niche width, an unknown axis at the neutral
  middle — with an axis inside the *optimal* band counted as perfect. Inside it
  EIVE cannot tell two species apart (a niche position is a consensus of
  several national systems), so ordering 0.99 above 0.93 would be ordering
  noise. `growing` is 1.0 exactly when every axis is optimal — the badge's word.
- **insect** is the German insect partner count on a log scale, 0 for none and
  1 for the catalogue's most visited plant (*Salix caprea*, 1,055): the tenth
  partner means more than the thousandth.
- **Why 0.1.** Among plants optimal everywhere the insects alone decide, whatever
  the weight. The weight only says how far below that a plant rich in insects
  may climb, and 0.1 puts the limit on a band edge: with one axis `z`
  half-widths off, growing = exp(−(z² − 0.25)/8), and with the top partner count
  it passes an all-optimal plant with none only while z < 1.006 — the end of
  *suitable*. **A plant whose light or soil is borderline never outranks one
  optimal everywhere, however many insects it feeds.** Against an all-optimal
  plant with the median count (67 partners, insect 0.60) it takes the top count
  and z < 0.74. The plain fit breaks ties.

Every list takes this order: the main list (after the colour/unknown grouping
it always had), the woody shortlist (room left out, doc 25), the improvements'
candidate pool (doc 19) and the catalogue search (doc 06). Each row shows its
"N Insektenarten" (`insect_partners` on `PlantSummary`), and the header says
"Oben steht, was hier am besten wächst; bei gleich guter Eignung entscheidet
der Insektenwert." Partner totals load once with the cached candidate set; the
ranking over the whole catalogue went from 42 to 43 ms.

**Measured on the real catalogue** (read-only, loam and fresh, 6 m², default
filters), the first five of the herbaceous list, before → after:

| Bed | Before (fit only, old table, too-bright cut) | After |
|---|---|---|
| Full sun, 10 h (L 8.0 → 9.0) | *Eryngium alpinum* 75, *Petasites spurius* 1, *Hordeum secalinum* 52, *Periploca graeca* 3, *Bellis perennis* 471 | *Trifolium fragiferum* 394, *Bellis perennis* 471, *Tanacetum vulgare* 497, *Tussilago farfara* 235, *Cirsium arvense* 890 |
| Half shade, 3 h (L 5.0 → 5.42) | *Neottia ovata* 4, *Knautia dipsacifolia* 125, *Viola biflora* 67, *Cerastium sylvaticum* 0, *Knautia drymeia* 0 | *Vicia sativa* 580, *Trifolium dubium* 495, *Potentilla reptans* 349, *Crepis biennis* 435, *Lathyrus pratensis* 299 |
| Deep shade, 1 h (L 3.0 → 3.33) | *Carex sylvatica* 147, *Viola biflora* 67, *Polystichum aculeatum* 5, *Brachypodium sylvaticum* 168, *Ranunculus cassubicus* 196 | *Epilobium montanum* 202, *Ranunculus cassubicus* 196, *Brachypodium sylvaticum* 168, *Euphorbia amygdaloides* 157, *Carex sylvatica* 147 |

(numbers: German insect partners). The deep-shade list's first fifteen are
woodland herbs at L 2.3–4.4, all optimal on light, but for *Rubus saxatilis*
(5.06, a generalist wide enough to be optimal there too); the half-shade
list's first fifteen carry 232–580 partners where the old one's carried 0–288;
*Lathraea squamaria*, twelfth in deep shade before, is gone (below). The
symmetric cut leaves 2,182 / 1,721 / 777 herbaceous species where the old one
left 2,352 / 2,536 / 2,548.

## Plants nobody can grow (owner, 2026-09-21)

*Lathraea squamaria* — no chlorophyll, living on hazel roots — was offered for
a sunny bed in March, and twelfth for a deep-shade one. `api/parasites.py`
names what lives on a host or a fungus, since the catalogue records no
parasitism: the holoparasites *Orobanche*, *Phelipanche*, *Lathraea*,
*Cuscuta*; the mycoheterotrophs *Monotropa*/*Hypopitys*, *Epipogium*,
*Corallorhiza*, *Limodorum* and, of the mixed genus *Neottia*, only *N.
nidus-avis* (also carried as "Neottia nidus") — *N. ovata* and *N. cordata*
are green; and the mistletoes *Viscum* and *Loranthus*. The green root
hemiparasites stay: *Rhinanthus*, *Melampyrum*, *Euphrasia*, *Odontites*,
*Pedicularis*, *Thesium* are sown, *Rhinanthus* into meadows on purpose.
`filters.excluded_outright` drops them for every caller — bed suggestions,
improvements, `GET /plants` — not as a filter, so not counted and with no
opt-out. Names were checked against the shipped catalogue.

## Growth form (the Wave 4 rule, since inverted)

A shady damp bed currently returns *Tsuga canadensis* — a hemlock tree — ahead of
the woodland sedges. Correct fit, useless suggestion. Noted as a known issue in
`06-plants-api` and fixed here, where a bed has a size to judge against.

Wave 4 excluded trees and shrubs unless `include_trees=true`. Wave 6 inverted
it: the catalogue's best forage plants are woody, so they are in by default,
in a shortlist of their own beside the main list (`25-woody-and-birds`), and
`include_trees=false` removes them.

Species whose growth form is unrecorded are **kept**. Absent data is not a
property of the plant — the same rule that keeps flower colour a soft filter.

## Business Rules

- **Already-planted species are excluded by default.** Suggesting what is already
  in the bed wastes the list; `exclude_planted=false` is there for comparison.
- **The bed must belong to the token's garden**, or 404. A bed id is not a
  capability.
- **Every suggestion carries its fit explanation**, so the UI can say *why*
  without recomputing.

## Known Issues

- **Climbers slip through.** Growth form only marks `tree` and `shrub`, so
  *Vitis riparia* — a liana — still appears for a shady damp bed. GIFT carries a
  separate `Climber_1` trait that is not ingested; adding it would close this.
- The bed's own area was not used, until Wave 6: the room check (`space`) now
  ranks each plant against it (`23-catalogue-filters`).
- ~~**The light cut sits on an unsettled scale.**~~ *The scale is settled
  (2026-09-21):* the hours→L mapping is on EIVE's 0–10 scale, on lines (doc
  07). **Still open:** a bed's light is the mean over its cells, which decides
  what is unsuitable for a bed half in sun and half in shade; and the model
  counts direct sun only, so an open north bed reads darker than it is (doc
  64, planned Wave 26).
- **Salt and coast plants rank high on loam in full sun.** *Plantago
  maritima*, *Tripolium pannonicum*, *Artemisia maritima* sit in the full-sun
  top fifteen: EIVE has no salt axis, and on L, M, N and R they fit. The old
  order had the same kind of guest (*Cochlearia officinalis*, *Eryngium
  alpinum*). A salinity indicator would need a source.
- ~~**Planting a perennial makes the light "stale".**~~ *Fixed the same day,
  after the merge:* the signature hashes only the plantings that shade
  (`lightview.shading_taxa`, the plants `canopy.shades` makes crowns of), so a
  Salbei planted from the list leaves the map and the list current. A shrub
  still makes them stale (`tests/test_light_signature_plantings.py`). Every
  stored map had to turn stale once anyway for doc 64's new grid, so this cost
  no extra recompute.
- ~~**Two copies of "the current signature".**~~ *Fixed the same day:*
  `api/light.py::_read` calls `light_state.current_signature`. `api/light.py`
  was split to get under the length limit (its response shapes are now in
  `api/schemas_light.py`).

## Bugs

- **2026-09-21 — "Gehölze ausblenden" never reached the server.** Wave 6 made
  `include_trees` default to true, and the client went on sending only `true`,
  so switching woody plants off changed the header's sentence and not the list.
  The client now sends `include_trees=false`.
