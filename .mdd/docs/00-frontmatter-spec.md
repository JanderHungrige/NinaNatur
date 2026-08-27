---
id: 00-frontmatter-spec
title: Frontmatter Schema - Canonical Field Reference for All MDD Docs
edition: MDD
depends_on: []
relates: []
source_files: []
routes: []
models: []
test_files: []
data_flow: greenfield
last_synced: 2026-08-27
status: complete
phase: all
mdd_version: 11
tags: [schema, frontmatter, spec]
path: Meta/Schema
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# Frontmatter Schema Reference

Every `.mdd/docs/*.md` feature doc must start with the YAML frontmatter block
defined here. Doc-generating phases must read this file before writing any
frontmatter.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique doc ID matching the filename slug (e.g. `01-trait-ingest`) |
| `title` | string | Human-readable feature name |
| `edition` | `MDD` or `Both` | Which MDD edition this applies to |
| `depends_on` | string[] | IDs of feature docs this depends on (build order) |
| `relates` | string[] | IDs of docs that co-change with this one (symmetric hint) |
| `source_files` | string[] | Source files this doc describes |
| `routes` | string[] | API routes exposed by this feature |
| `models` | string[] | Database tables used or defined by this feature |
| `test_files` | string[] | Test files covering this feature |
| `data_flow` | string | `greenfield`, `reads-existing`, `writes-existing`, `mixed` |
| `last_synced` | date | ISO date when doc was last synced with source code |
| `status` | string | `draft`, `in_progress`, `complete`, `deprecated` |
| `phase` | string | Build phase: `1`, `2`, `3`, or `all` |
| `mdd_version` | integer | MDD version when doc was last updated |
| `tags` | string[] | Domain concepts, technology, feature names |
| `path` | string | Slash-delimited breadcrumb (e.g. `Data/Ingest`) |
| `integration_contracts` | object[] | Contracts this doc consumes from other features |
| `satisfies_contracts` | object[] | Contracts this doc fulfills for other features |
| `security_read_sites` | string[] | Code locations where security-sensitive reads occur |
| `known_issues` | string[] | Known bugs or gaps (append-only) |

## satisfies_contracts Schema

```yaml
satisfies_contracts:
  - from: <feature-id>
    function: <function or endpoint name>
    when: <condition or trigger>
    status: pending   # or: done
    verified_at: ""   # or: "file:line" when status is done
```
