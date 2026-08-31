---
id: 54-one-way-in
title: One Way In, and a Quiet Second
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-13
wave_status: complete
depends_on: [53-account-in-header]
relates: [31-map-selection, 30-landing-and-garden-id]
source_files:
  - frontend/src/components/Landing.tsx
  - frontend/src/App.tsx
routes: []
models: []
test_files:
  - frontend/src/components/Landing.test.tsx
data_flow: reads-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [landing, choices, resilience]
path: Landing/Ways
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# One way in, and a quiet second

## What this is

Four equal boxes become two: start on the map, or open a garden you already
have. *Ohne Karte anfangen* becomes a fold-out underneath.

## Decisions

### Three equal boxes said three equal choices

There is one way to make a garden, and it is the map. *Garten öffnen* stays
beside it because it is not a way of making one but of coming back to one — a
different question, and the only other thing somebody arrives wanting to do.

### The map-less way stays reachable

Decided with the user over removing it. Nominatim and Overpass are free
community services with no SLA — the tile policy says so in as many words. A bad
afternoon at either one, with no second path, leaves nobody able to start at all.

It is a `<details>`: present, closed, and honest about being the lesser way. The
summary says when to reach for it — *"wenn die Kartensuche gerade nicht
antwortet, oder du die Koordinaten ohnehin kennst"* — rather than leaving
somebody to guess why it is there.

## Definition of done

The landing page shows the map and the open-a-garden box; the map-less form is
one click away and clearly secondary.
