---
id: 04-trait-resolve
title: Read-Time Trait Resolution with Provenance
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-2
wave_status: complete
depends_on: [01-trait-ingest]
relates: [03-niche-fit, 06-plants-api]
source_files:
  - ninanatur/data/__init__.py
  - ninanatur/data/traits.py
routes: []
models:
  - trait
  - taxon
test_files:
  - tests/test_trait_resolve.py
data_flow: reads-existing
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [traits, provenance, resolution, read-model]
path: Data/Read
integration_contracts:
  - function: resolve_trait(conn, taxon_id, trait_key)
    when: any read of a trait value for display or ranking
    note: returns value AND source — no caller may read the trait table directly, or the API loses its ability to cite
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 04 — Read-Time Trait Resolution with Provenance

## Purpose

Turn "several sources may have written this trait" into one answer that still
knows where it came from. The ingest layer deliberately stores conflicting values
side by side; this is where that is collapsed for display — visibly, not silently.

## Measured before designed

Checked against the database before writing any arbitration logic:

```
trait keys with more than one source for the same taxon: 0
```

EIVE owns the Ellenberg axes and their widths, GIFT owns height, phenology,
colour and form. **There is no conflict to resolve today.** So this feature does
not invent a ranking policy it cannot justify. It provides:

- a priority order that is currently a formality but exists for the third source
- the guarantee that when sources *do* disagree, both remain visible

Building elaborate arbitration now would be designing against an imagined problem
and would very likely be wrong when the real one arrives.

## Data Model

No schema change. Reads `trait`, grouped by `(taxon_id, trait_key)`.

## Business Rules

- **Every resolved value carries its source and licence.** A number the UI cannot
  attribute is a number the UI should not show.
- **Priority is explicit and ordered**, currently `EIVE-1.0` then `GIFT`. When a
  key has one source the order is irrelevant; when it has several the winner is
  deterministic rather than whatever SQLite returned first.
- **Alternatives are returned, not discarded.** A resolved trait reports the
  losing values too, so disagreement can be surfaced instead of hidden.
- **Unknown is a value.** `resolve_trait` returns `None` for an absent trait, and
  callers must render that as unknown — never as zero, never omitted. This is
  what keeps flower colour honest at 12% coverage.
- **Bulk reads exist.** Scoring 4,437 species one query at a time would be
  thousands of round trips; `resolve_traits_for()` loads a whole taxon in one.

## Dependencies

`01-trait-ingest` — the trait table and its provenance columns.

## Security

Read-only. Every query is parameterised; trait keys from callers are validated
against the known set rather than interpolated.

## Known Issues

- GIFT phenology is global, not German. *Achillea millefolium* resolves to a
  flowering start of July, where German floras give June. Wave 4 should treat
  month bounds as approximate, and a German phenology source would be a
  worthwhile later addition.

## Bugs

(none yet)
