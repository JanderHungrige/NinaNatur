---
id: ninanatur-wave-28
title: "Wave 28: What colour it flowers"
initiative: ninanatur
initiative_version: 24
status: planned
depends_on: ninanatur-wave-24
demo_state: "Zwölfhundert insektenbestäubte Arten, die bisher „Farbe unbekannt" trugen, haben eine Primär- und, wo es sie gibt, eine Sekundärfarbe — aus offenen Fotos gemessen, von einem lokalen Modell beurteilt, gegen GIFT geprüft und mit drei Belegfotos samt Fotograf und Lizenz belegt. Auf dem Plan tragen die Blütentupfer die Farbe, die Margerite ihr gelbes Zentrum, das Buschwindröschen beide Morphen — und wer widerspricht, steht daneben, nicht darüber."
created: 2026-09-10
hash: bae4b2ae
---

# Wave 28: What colour it flowers

## Demo-State

Zwölfhundert insektenbestäubte Arten, die bisher „Farbe unbekannt" trugen,
haben eine Primär- und, wo es sie gibt, eine Sekundärfarbe — aus offenen Fotos
gemessen, von einem lokalen Modell beurteilt, gegen GIFT geprüft und mit drei
Belegfotos samt Fotograf und Lizenz belegt. Auf dem Plan tragen die
Blütentupfer die Farbe, die Margerite ihr gelbes Zentrum, das Buschwindröschen
beide Morphen — und wer widerspricht, steht daneben, nicht darüber.

*(This wave is not complete until this can be manually demonstrated.)*

Detailed plan, in German, with the verified API calls, the colour metric, the
VLM schema, the aggregation rules, the provenance schema and the budgets:
`.mdd/plans/08-bluetenfarben-datenbank-lokale-ki.md`. Its parent plan for
colour *and* text is `.mdd/plans/02-bluetenfarben-und-textextraktion.md`.

## Why this is a wave

Flower colour is recorded for **590 of 8 939** species (GIFT), and the gap sits
exactly where the product lives: **1 222 insect-pollinated core species have no
colour** — among them Acker-Witwenblume, Margerite, Kornblume, Schafgarbe and
Buschwindröschen (all five checked on 2026-09-07). For them the bloom calendar
and the bloom dots run on "unknown", and the colour filter is a filter over
6.6 % of the catalogue that must never exclude (doc 23's rule, and the reason
for it).

The pictures exist. A random sample of 20 of those 1 222 species, checked on
2026-09-07: **20/20** have ≥ 5 openly licensed (CC0/CC-BY) GBIF occurrence
photos worldwide, **19/20** ≥ 5 from Germany, 14/20 ≥ 3 Commons files with a
structured "depicts" statement, 16/20 resolve to Wikidata straight from their
GBIF key. Supply is not the problem. Selection, measurement, judgement and
provenance are — and each is a feature here.

## What the pipeline is, in one paragraph

An **ingest-time** pipeline, offline, never in the container: up to twelve
licence-clear photos per species from four open sources; a triage that drops
herbarium sheets, illustrations, leaves and fruit; **the flower found and
masked** (Grounding DINO + SAM 2, or Florence-2 as the one-model path for a
small Mac); the mask's colours **measured** in CIELAB and named against the ten
drawable colours; an independent judgement from a **local VLM** (Qwen3-VL)
answering a fixed JSON schema; a third vote from a DINOv2 probe trained on
GIFT; the three votes **aggregated** per species into primary, secondary and
variability with a confidence; **validated** against the 524 GIFT core species
before anything ships; contested species shown to a person on a contact sheet;
and values written **only** through `upsert_trait`, with evidence photos, author
and licence per value.

Three voters with different failure modes are the design: pixels, language and
embeddings each err differently, and disagreement is the signal for a human.

## What is already there

| Piece | State |
|---|---|
| Ten-colour vocabulary, shared by server and plan (`DRAWABLE`, `colours.ts`, a vocabulary test) | done — docs 23, 56, 62 |
| One write path with provenance (`upsert_trait`), sources coexisting by primary key | done — doc 01 |
| `manual` colour ranked last, any published source above it | done — doc 62 |
| Bloom dots per cluster, seeded, bounded; grey out of season | done — doc 56 |
| Wikipedia summaries with attribution, cached on the volume | done — doc 22 |
| Cached, polite outbound HTTP (`ingest/http.py`) | done |
| GBIF taxon keys as `taxon_id` — the bridge to Wikidata (`P846`) | done by construction |
| A machine to run models on | **Apple M1, 16 GB, no torch/mlx/ollama** — measured 2026-09-07 |
| A second ground truth | **open**: BiolFlor (3 659 species, flower colour) via TRY, public datasets CC BY 3.0 with registration — to be settled in feature 0 |

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | which-pictures-and-whose | — | planned | — |
| 1 | twelve-pictures-of-each | — | planned | 0 |
| 2 | where-the-flower-is | — | planned | 1 |
| 3 | what-colour-it-is | — | planned | 2 |
| 4 | a-second-opinion | — | planned | 2 |
| 5 | one-answer-per-species | — | planned | 3, 4 |
| 6 | somebody-looked | — | planned | 5 |
| 7 | written-with-its-pictures | — | planned | 5 |

Three stages:

- **Stage 1 — the pictures:** 0, 1. Sources, licences, the survey, the corpus.
- **Stage 2 — the measurement:** 2, 3, 4, 5. Masks, colours, judgements, one
  answer per species, and the validation gate.
- **Stage 3 — the catalogue and the page:** 6, 7.

Stages 1 and 2 are ingest work and need nothing from Waves 25–27; they can run
as an offline job whenever there is a machine free. The wave sits at 28 because
its *visible* result — bloom dabs carrying a secondary colour, an evidence
panel with photographs — lands on the plan Wave 24 draws.

## What each one is

### 0. which-pictures-and-whose

The registry, as every source here begins: what each source answers, under
which licence, and what it costs to ask.

- **The bridge:** `taxon_id` → Wikidata item via `wdt:P846`, SPARQL in
  `VALUES` blocks of 200; fallback `wbsearchentities` on the canonical name.
- **The four sources** and their licence fields: Commons structured data
  (`haswbstatement:P180=<QID>`), Commons categories, Wikipedia article images
  with captions (`page/media-list`), GBIF occurrence media from Germany with
  `license`, `creator`, `rightsHolder`, `publisher`, `eventDate` per image —
  and the fact that GBIF's licence filter knows only CC0, CC-BY and CC-BY-NC
  (`CC_BY_SA_4_0` is an HTTP 400).
- **The survey** over the target set: counts per species per source and
  licence, the list below the threshold of three usable images. About 17 000
  requests, 0.3 s apart, cached — an hour and a half.
- **BiolFlor settled:** is it a public TRY dataset, under which licence, with
  which colour classes. If it is open, it is ingested first as an ordinary
  `Source` adapter and this pipeline becomes what it should be anyway —
  validation, secondary colour, variability and evidence.
- **Model cards read and cited:** Grounding DINO, SAM 2, Florence-2, CLIP/SigLIP,
  DINOv2 (Apache-2.0 / MIT), Qwen3-VL (Apache-2.0); Gemma only after its
  terms. A dated table in the feature doc.

Tests: the bridge round-trips for the five checked species; NC images are
refused by the licence filter without the explicit switch; every source entry
carries an attribution rule.

### 1. twelve-pictures-of-each

Quotas per species — six GBIF-DE (wild plants at their site, dated, located;
Pl@ntNet and NABU-naturgucker under CC-BY first), four Commons "depicts", two
Wikipedia article images whose caption says *Blüte* or *Blütenstand* — with
licence checked **per image**, unknown or NC refused and logged, SHA-256 and
perceptual hash against duplicates (the same photo often sits on Commons and
at Pl@ntNet), EXIF stripped, 640 px derivatives only, originals discarded.
Then the triage: CLIP/SigLIP zero-shot against *flower / leaves only /
herbarium / illustration / map / seeds or fruit / habitat / bark / insect on a
flower*; captions with *Herbar*, *Illustration*, *Laubblatt*, *Frucht* out;
a GBIF capture month outside the flowering window (±1, wrapping) demoted, not
dropped. Manifests as JSONL, resumable, hash-checked; ≈ 35 000 images, ≈ 6 GB
under `data/raw/images/`, gitignored, never in the image.

Tests: the licence filter, the quota logic, the duplicate detection and the
caption rules on fixtures; a budget test that a rerun costs zero downloads.

### 2. where-the-flower-is

Grounding DINO *tiny* with the prompt `flower . blossom . inflorescence .
flower head .` (box 0.30, text 0.25, at most 12 boxes) and SAM 2 *hiera-small*
masks from the boxes — or Florence-2 *large* doing both in one pass on the
16 GB machine. Quality gates per mask: 1–60 % of the frame, score ≥ 0.35,
eroded 2 px, overlapping masks merged, the best five kept by area × score.
A mask contact sheet for fifty species is the first thing a person looks at.

Tests: recorded model outputs on the golden set (thirty small, openly licensed
fixture images); the gates on synthetic masks. No test loads a model or the
network.

### 3. what-colour-it-is

sRGB → CIELAB; pixels weighted by distance from the mask edge, specular
(L\* > 97) and deep shadow (L\* < 8) dropped; k-means (k = 4, fixed seed) with
ΔE2000 merging below 12 and clusters under 6 % dropped; every cluster centre
named by **rules in L\*C\*h** — white, black, brown, yellow, orange, red, pink,
violet, blue, green, with the second-nearest name carried for the boundary
cases (pink/violet, yellow/orange). Per image: primary if the largest share is
≥ 0.45, secondary if a *different* name holds ≥ 0.18 and lies ΔE2000 ≥ 20 away.
The boundaries are **calibrated** on the GIFT species (grid search on macro-F1,
5-fold) — a starting table is in the plan, the calibrated one goes into the doc.

Tests: synthetic discs on green with a highlight and a shadow yield the expected
names; boundary hues yield both names; the golden set matches its recorded
verdicts.

### 4. a-second-opinion

Two more voters. **The VLM:** Qwen3-VL-8B (Q4; 4B if memory forces it) via
Ollama or MLX-VLM, one call per image at 640 px, temperature 0, the answer
**forced into a JSON schema** — flower visible, which part is coloured, colours
with shares in the fixed vocabulary, centre colour, colour cast, likely
cultivar, another species in frame, confidence — with the prompt text and
schema fixed in the plan and versioned in every record. **The probe:** a
DINOv2-small embedding of the flower crop and a logistic regression trained on
the GIFT species, with an out-of-distribution score. Only the four best images
per species go to the VLM (≈ 17 000 calls).

Tests: schema validation and the retry-once rule on recorded answers; the probe
reproduces its recorded probabilities on the golden set.

### 5. one-answer-per-species

Votes weighted — pixel 1.0 × mask quality, VLM 1.0 × confidence × 0.6 if a
colour cast × 0.5 if a likely cultivar, probe 0.5 × probability; an image drops
out when no flower is visible or another species dominates. Per species the
primary is the heaviest colour; confidence = its share × min(1, images/6) ×
(1.0 with two sources, 0.85 with one). Written at ≥ 0.75 with ≥ 3 images;
written and reviewed between 0.50 and 0.75; review only below. **Variable**
when a second colour carries ≥ 35 % of image primaries and lies ΔE2000 ≥ 20
away — both stored, the commoner one primary. A **secondary** colour only when
pixel *and* VLM name the same one in ≥ 50 % of images (the Margerite's yellow
centre, and not the leaf behind it).

**And the gate.** The 524 GIFT core species, stratified, five folds: primary
agreement, macro-F1, top-2, the confusion matrix with pink↔violet,
yellow↔orange and white↔pink stated on their own, voter agreement as a number.
**Thresholds before anything ships:** ≥ 85 % primary agreement, ≥ 92 % top-2,
no class below 70 % recall (black and brown excepted). Thirty disagreements with
GIFT looked at by hand before the pipeline takes the blame — GIFT is an
aggregation and carries its own errors. BiolFlor, if open, is the second check,
and GIFT↔BiolFlor agreement is the yardstick for what "right" can mean at all.

Tests: the aggregation rules as table-driven cases (Margerite: white + yellow
centre; Buschwindröschen: variable white/pink; a species with two images:
review only).

### 6. somebody-looked

A static HTML contact sheet per contested species: the images with their masks
tinted, the three votes per image, the aggregate, GIFT and BiolFlor beside it;
keys `1–0` set the colour, `s` secondary, `v` variable, `x` unusable, `n` next.
Decisions land in `reviews.jsonl` with reviewer and time. About 150 species an
hour; with a fifth contested that is two to three hours for the first stage.
A human confirmation sets `confidence = 1.0` and `reviewed_by`; a human
contradiction writes the person, not the machine, and both stay readable in
the evidence.

### 7. written-with-its-pictures

`upsert_trait` for `flower_colour` (primary), `flower_colour_secondary` and
`flower_colour_variability`, `source="ninanatur-cv-1"`, the licence string
naming the image licences and the evidence table, the confidence from feature
5; `KNOWN_TRAIT_KEYS` extended; `SOURCE_PRIORITY` becomes
`("EIVE-1.0", "GIFT", "ninanatur-cv-1")` with `manual` still last (doc 62's
rule — a decision the owner can reverse, see below). Two small tables ship in
the catalogue — `colour_verdict` and `colour_evidence` with up to three photos
per species (≈ 2.6 MB, measured before merging) — while `image_asset` and
`colour_observation` stay ingest-time like `interaction`.

On the page: *„Blütenfarbe: rosa — aus 8 Fotos ermittelt, Konfidenz 0,82.
Sekundär: gelb (Zentrum)."* with three evidence thumbnails **linked, not
copied** (as `species_info` links Wikipedia), each with author, licence and the
file page; the bloom dabs paint the primary, both colours in proportion for a
variable species, the secondary as a small core; `ColourNote` shows what the
machine said before the gardener disagrees; the CSP allows exactly the evidence
hosts. Verified against a **fresh empty volume**, because that is the state a
new deployment starts in (`CLAUDE.md`).

## Budgets

| | On the M1 (16 GB) | On a rented GPU |
|---|---|---|
| Survey requests | ≈ 17 000, ~1.5 h, cached | same |
| Images | ≤ 12 per species, ≈ 35 000, ≈ 6 GB derivatives | same |
| Triage | 20 min | 1 min |
| Locate + mask | 8–20 h — two nights | 30 min |
| VLM (4 best images per species) | 15–35 h — three nights | 30–60 min |
| Human review | ~20 % contested → 2–3 h per stage | same |
| Catalogue growth | ≈ 2.6 MB | same |

Both are realistic; the GPU costs a few euros and sends only public images.

## What the model will not know

- **The wild type from a cultivar** with certainty. GBIF-DE photos first, the
  VLM's cultivar flag, Commons file names with `'…'` or *cv.* excluded — and
  the review for the rest.
- **Pink from violet** at the boundary — calibrated, second-named, decided by
  the VLM, reviewed when still unsure, and reported as a confusion rather than
  hidden.
- **Tiny flowers** (Galium, small Myosotis): masks under 1 % drop the image and
  the species goes to review with a close-up note.
- **Wind-pollinated grasses and sedges**: green or brown, low value, last stage
  if at all.
- **Colour under a colour cast**: flagged by the VLM, down-weighted, averaged
  across images; never corrected by a global white balance, which would recolour
  the very flower it is meant to measure.

## Open Research

- BiolFlor's licence and colour classes — decides the order of features 0–3.
- The density of usable images per species below which the pipeline should
  say "insufficient" rather than guess: three is the starting rule.
- Whether the vocabulary needs *purple* or *cream* — a change to the plan's
  drawing layer, the filters and the frontend, so a decision, not a side effect.
- Machine or rented GPU for the nights.

## Deliberately not in this wave

- Overwriting GIFT. Sources never overwrite each other here; the pipeline's
  value sits beside GIFT's, and `resolve_trait` shows the disagreement.
- Any NC-licensed image as evidence, and any image without a licence at all.
- Text extraction from Wikipedia (plan 02, part B) — its own feature set, and
  a fourth voter for a later stage.
- Anything about flower size, inflorescence type or phenology from the same
  images — noted as possible, not planned.
