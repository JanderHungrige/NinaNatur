---
id: 22-species-info
title: What This Plant Actually Is
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-6
wave_status: complete
depends_on: [21-german-names]
relates: [23-catalogue-filters]
source_files:
  - ninanatur/data/species_info.py
  - ninanatur/ingest/db.py
  - ninanatur/api/plants.py
  - ninanatur/api/schemas.py
  - frontend/src/components/SpeciesInfo.tsx
  - frontend/src/components/SuggestionList.tsx
  - frontend/src/App.tsx
routes:
  - GET /api/v1/plants/{taxon_id}/info
models:
  - species_info
test_files:
  - tests/test_species_info.py
  - frontend/src/components/SpeciesInfo.test.tsx
data_flow: mixed
last_synced: 2026-08-28
status: complete
phase: all
mdd_version: 11
tags: [wikipedia, cache, attribution, licensing, info]
path: Data/Info
integration_contracts:
  - function: species_info(conn, taxon_id, ...)
    when: showing a description or photo for a species
    note: every response carries its licence and a link back — CC-BY-SA is not optional, and a cached copy does not become ours
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 22 — What This Plant Actually Is

## Purpose

A ranked list of binomials tells a gardener nothing about what the plant looks
like or where it grows. This adds a description and a photograph.

## API, not a crawler — and the answer to the question that was asked

Verified before planning: `de.wikipedia.org/api/rest_v1/page/summary/{title}`
returns a summary and a thumbnail, and **redirects the scientific name to the
German article** — `Achillea millefolium` resolves to *Gemeine Schafgarbe*. There
is no reason to scrape anything.

**Fetched on demand and cached on the volume**, which was the open question:

- A live fetch on every view adds latency and an external dependency to a page
  that currently has neither, and breaks when Wikipedia rate-limits.
- Baking summaries into the shipped catalogue makes them stale on the image's
  release cycle and re-inflates something just trimmed to 13 MB.
- The cache is *derived, per-deployment and refreshable* — the same shape as a
  garden, not the same shape as the catalogue. It belongs on the volume.

## Licensing

Wikipedia text is **CC-BY-SA 4.0**. Attribution and a link back to the article
are required, not decorative. Every response carries both, and the UI is not
permitted to show the extract without them. **A cached copy does not become
ours.**

## Data Model

**species_info** — on the volume, never in the catalogue
`taxon_id INTEGER PK, title TEXT, extract TEXT, thumbnail_url TEXT,
 page_url TEXT, language TEXT, found INTEGER NOT NULL, fetched_at TEXT NOT NULL`

## Business Rules

- **A miss is cached too, but expires sooner.** Remembering "no article" forever
  would freeze a gap that Wikipedia may close next week; re-asking on every view
  would hammer a free service for a known-absent page.
- **German first, English as a fallback**, and the response says which it
  returned. A German user shown an English summary should know why.
- **A failed fetch is not an error for the caller.** The panel degrades to the
  data we already have; a plant list must not break because an external service
  is down.
- **The extract is text, and is rendered as text.** Nothing from Wikipedia is
  interpreted as markup.

## Security

Untrusted third-party content. Titles are URL-encoded on the way out; the
response is stored parameterised and rendered as plain text, never as HTML. The
thumbnail is referenced by URL rather than proxied, so no remote bytes are
executed or stored.

## Known Issues

- The article is fetched per view rather than prefetched for the visible list,
  so the first open of each species waits on Wikipedia. Acceptable while the
  panel is opt-in; revisit if info moves inline into the list.

## Bugs

Both were found by clicking the button in the running app. Both suites were
green at the time, and neither bug is visible from the test doubles — the same
shape as every other live-run finding in this project.

### The panel requested Wikipedia in an infinite loop

`SpeciesInfo` took its fetcher as an injected prop with an inline default,
`load = (id) => defaultClient.speciesInfo(id)`, and listed `load` in the
effect's dependency array. An inline default is a **fresh closure on every
render**, so the effect cancelled and refired itself on its own state updates:
~100 requests in milliseconds against a free external service, while the panel
sat on "Wird geladen…" forever. The heading showed the resolved German title,
which is what made it look like a rendering bug rather than a request storm.

Fixed by hoisting the default to module scope, where it has a stable identity.

**Why the tests could not see it:** every test injected `load`, and an injected
prop is defined once in a test, so it is stable by construction. The default
path — the only one production uses — was never exercised. The regression test
renders without `load`; because the client binds `globalThis.fetch` in its
constructor at import time, the stub has to be installed before the module
loads (`vi.resetModules()` + dynamic import), which is the same import-time
binding this component's own comment warns about.

### The panel named two species at once

Clicking a second plant reuses the component instance, so `info` survived the
switch. Until the new article arrived, the heading showed the previous species'
title while the subtitle already showed the new one. Brief on a fast connection,
seconds on a slow one, and simply wrong. Fixed by clearing `info` when the
effect refires.
