---
generated: 2026-08-28
doc_count: 7
connection_count: 6
overlap_count: 0
---

# Connections

## Path Tree

API/Plants
  └── 06-plants-api  complete
Data/Ingest
  └── 01-trait-ingest  draft
Data/Interactions
  └── 05-insect-checklist-de  complete
Data/Read
  └── 04-trait-resolve  complete
Matching/Fit
  └── 03-niche-fit  complete
Meta/Schema
  └── 00-frontmatter-spec  complete
Platform/Deploy
  └── 02-web-shell  complete

## Dependency Graph

```mermaid
graph TD
    00_frontmatter_spec["00-frontmatter-spec"]:::complete
    01_trait_ingest["01-trait-ingest"]:::draft
    02_web_shell["02-web-shell"]:::complete
    03_niche_fit["03-niche-fit"]:::complete
    01_trait_ingest --> 03_niche_fit
    04_trait_resolve["04-trait-resolve"]:::complete
    01_trait_ingest --> 04_trait_resolve
    05_insect_checklist_de["05-insect-checklist-de"]:::complete
    01_trait_ingest --> 05_insect_checklist_de
    06_plants_api["06-plants-api"]:::complete
    03_niche_fit --> 06_plants_api
    04_trait_resolve --> 06_plants_api
    05_insect_checklist_de --> 06_plants_api
    classDef complete fill:#00e5cc,color:#000
    classDef in_progress fill:#ffaa00,color:#000
    classDef draft fill:#888,color:#fff
    classDef deprecated fill:#555,color:#aaa
```

## Source File Overlap

(none)

## Warnings

(none)
