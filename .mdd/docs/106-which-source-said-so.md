---
id: 106-which-source-said-so
title: Which Source Said So
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [102-which-tiles-and-whose, 104-a-horizon-for-everyone, 105-every-roof-in-the-country]
relates: [93-where-the-roof-came-from, 68-terrain-sources]
source_files:
  - ninanatur/garden/credits.py
  - ninanatur/api/light.py
  - ninanatur/garden/lightgrid.py
  - ninanatur/geo/terrain_store.py
  - ninanatur/geo/tile_sources.py
routes:
  - GET /api/v1/gardens/{token}/sources
models: []
test_files:
  - tests/test_credits.py
data_flow: reads-existing
last_synced: 2026-09-20
status: draft
phase: all
mdd_version: 11
tags: [provenance, licence, attribution, credits, staleness, light-map]
path: Geo/Provenance
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 106 — Which Source Said So

## Purpose

Wave 25 gave a garden more surveys than it has ever had. A Bavarian garden now
stands on ground from a state tile, under a horizon from Copernicus, with roofs
from a state building model: three sources, three licences, one page.

Two things follow, and this feature is both of them.

## A credit is not a caption

CC-BY-4.0 and dl-de/by-2-0 require the named credit. The Copernicus terms
require theirs — DLR, Airbus, ESA. dl-de/zero-2-0 requires nothing and is given
it anyway. **A height shown without its credit is a height used outside its
licence**, and feature 2 created exactly that gap the moment a garden in
Bayern got a horizon: the ring was drawn and nobody was named.

`GET /gardens/{token}/sources` is the list, and it is built from what a garden
*used*, never from what its state could offer:

- **the ground**, from the stored window, which carries its own source, licence,
  attribution and vertical step;
- **the horizon**, from `terrain_horizon.source` — stored since Wave 17 and
  never read until a ring could come from somewhere other than the garden's own
  state;
- **the buildings**, but only where something in this garden actually carries a
  surveyed height. A state publishing LoD2 is not a credit; a measured house is.

One line per licence and attribution: a state that gave both the ground and the
roofs is thanked once, for both, because two identical paragraphs under a plan
is not more correct, only longer.

**No request is made to build the list.** Naming the building model needs a
state, and the stored ground window already says which one measured it — a
reverse geocode on a page load is a request Nominatim does not need to serve
for a caption. That rests on an invariant: every state that publishes LoD2 also
publishes its ground. `tests/test_credits.py` asserts it, so the day a state
publishes buildings and no ground, the test says so and names it — and then the
element needs a `measured_by` of its own rather than an inference.

## One place knows both spellings

The terrain services are registered under *Nordrhein-Westfalen*, the tiles under
*NW*, and OSM says the first. Until this feature each registry answered to one
spelling and returned None for the other, which is a source silently not being
there. `tile_sources.STATES` is now the one table, `key_of` and `name_of` the
two directions, and every lookup goes through them. The invariant test above
found this on its first run, in the state that has both.

## A map that does not know it is out of date

`signature_of` is a hash of everything that changes where the shadows fall, so
that a stale map says it is stale rather than looking right. Until now it held
the garden and nothing about the ground it stands on.

Bayern is why that is not enough. Yesterday a Bavarian garden had no terrain at
all and its light map was computed flat; today its tiles are read. Without the
ground in the signature, that garden would keep its flat map for ever, quietly
— the one failure mode the signature exists to prevent (doc 63's reasoning: a
fact about the inputs, not a list of events somebody has to remember).

So the signature now includes what the ground was measured from and how finely,
and the horizon's own numbers. A better source for the same place is a
different map.

## Business Rules

1. **Every source a garden used is named**, with the credit its licence asks
   for, on the page that shows its numbers.
2. **Never a credit for a source the garden did not touch** — that would be a
   claim about where its numbers came from.
3. **Building the list costs no request.**
4. **A new or better source makes the light map stale**, because the signature
   is about the inputs and the ground is one of them.
5. **One table for the state's two spellings**, and every registry lookup goes
   through it.

## On the page

`SourceCredits` prints the list last in the garden's details, under the things
it is about: what each survey decided, in the gardener's words — *Gelände*,
*Horizont*, *Gebäude*, or *Gelände und Gebäude* where one survey gave two — its
name, how fine it is, and then the credit itself, word for word. Nothing is
drawn for a garden that rests on nothing, which is most of them.

It is fetched with everything else the server derives (`fetchDerived`), because
it costs no request of its own beyond the round trip and a garden that shows
numbers must show their credits at the same time, not a moment later.

## Dependencies

Docs 102–105 for the sources themselves, doc 93 for the order of truth about
heights, doc 63 for why the signature is a fact and not a list.

## Security

The endpoint reads stored rows and the registries; it takes no parameter but
the token and reaches no network. A credit's text comes from the registry, not
from anything a garden carries.

## Known Issues

- The building credit is named from the ground window's state (above). Guarded
  by a test, and the day it fails the answer is `measured_by` on the element.
- The credits are shown in the garden's own details, under everything they are
  about. A bed's or an element's panel does not repeat them — the numbers on
  those panels come from the same surveys, and a credit per panel would be four
  copies of the same paragraph.

## Bugs
