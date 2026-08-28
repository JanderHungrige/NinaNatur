---
id: 16-nativeness
title: Native or Introduced in Germany
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-5
wave_status: complete
depends_on: [01-trait-ingest]
relates: [13-bed-suggestions, 18-insect-score]
source_files:
  - ninanatur/ingest/sources/nativeness.py
  - ninanatur/api/search.py
  - ninanatur/api/gardens.py
  - ninanatur/api/planning.py
test_files:
  - tests/test_nativeness.py
routes: []
models:
  - trait
data_flow: mixed
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [nativeness, gbif, wcvp, establishment, suggestions]
path: Data/Nativeness
integration_contracts:
  - function: parse_german_establishment(distributions)
    when: deciding whether a species is native to Germany
    note: must handle both response shapes — parsing only the structured one marks every species in the other as unknown, and those include the invasive ones
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 16 — Native or Introduced in Germany

## Purpose

The landing page promises "heimischen Pflanzen" and nothing in the database
backs it. `occurs_de` means *recorded in Germany*, which is equally true of
*Vitis riparia*, a North American grape, and of *Impatiens glandulifera*, an
invasive the product should be steering people away from.

This closes that gap. It is a correctness fix to the product's central claim,
not a scoring nicety.

## The two response shapes

GBIF surfaces WCVP/Euro+Med distributions, and they arrive in two forms.
Verified against real responses before writing any parser:

**Structured** — one row per region:
```
locality: "Germany"        establishmentMeans: "NATIVE"       (Achillea millefolium)
locality: "Germany"        establishmentMeans: "INTRODUCED"   (Tsuga canadensis)
```

**Unstructured** — one row listing every region in a single string, with `[I]`
marking introduced and `establishmentMeans: null`:
```
"... Belgium; Luxembourg; Germany (Brandenburg, Berlin, ...); Switzerland; ..."   (Salix caprea, native)
"... Netherlands [I]; Belgium [I]; Germany [I]; Switzerland [I]; ..."             (Impatiens glandulifera, introduced)
```

**Parsing only the structured shape would mark every species in the second as
unknown** — and the second is where the invasive species live, because they are
the ones with sprawling introduced ranges.

The rule: find the segment naming Germany, then look for `[I]` attached to it.
Region detail in parentheses must not be mistaken for the marker.

## Data Model

No new table. One trait key, so it inherits provenance for free:

`native_de` — `value_text` in `native` / `introduced` / `unknown`,
source `GBIF-WCVP`.

## Business Rules

- **Unknown stays unknown.** A species GBIF has no German entry for is not
  assumed native. It is reported as unknown and shown as such — the same rule
  the whole project runs on.
- **Suggestions default to native**, with introduced available behind a labelled
  toggle. This is not a new product decision; it is the existing promise kept.
  Unknown nativeness is *included* by default, because excluding it would hide
  species for a gap in the data rather than a property of the plant.
- **Ingest is resumable and cached.** One request per species, ~4,400 of them.

## Security

Outbound reads of a public API. Locality strings are untrusted text: parsed, and
written through the same parameterised trait path as everything else.

## Known Issues

- One request per species, ~8,900 of them. Cached, resumable, and one-off, but a
  full refresh is roughly an hour.

## Verified against real responses

Eight species covering both shapes and both answers, checked before the parser
was trusted:

| Species | Expected | Parsed |
|---|---|---|
| Achillea millefolium, Salix caprea, Quercus robur, Primula veris | native | native |
| Vitis riparia, Impatiens glandulifera, Tsuga canadensis, Solidago canadensis | introduced | introduced |

## What the full ingest found

Across the 3,087 species the app can actually suggest:

| | count |
|---|---:|
| native | 1,755 |
| **introduced** | **1,071** |
| unknown | 261 |

**A third of everything the product has been calling "heimisch" is not.** Native
became the default filter, taking a dry sunny bed from 3,734 candidates to 2,549
and dropping *Trifolium striatum* out of the top four.

## Bugs

(none yet)
