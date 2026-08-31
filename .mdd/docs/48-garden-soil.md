---
id: 48-garden-soil
title: Ask the Soil Once, and Let a Bed Differ
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-12
wave_status: complete
depends_on: [47-panel-order]
relates: [12-bed-light, 32-object-heights, 45-relabel-and-skin]
source_files:
  - ninanatur/ingest/schema.py
  - ninanatur/ingest/migrations.py
  - ninanatur/garden/store.py
  - ninanatur/api/gardens.py
  - frontend/src/components/GardenSoil.tsx
  - frontend/src/components/ObjectEditor.tsx
routes: ["/api/v1/gardens/{token}/soil"]
models: [garden, element]
test_files:
  - tests/test_garden_soil.py
  - frontend/src/components/GardenSoil.test.tsx
data_flow: writes-existing
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [soil, moisture, defaults, ellenberg, one-question-per-garden]
path: Garden/Soil
integration_contracts:
  - from: 12-bed-light
    function: site_axes_from_soil
    when: a bed learns its soil, from the garden or its own
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Moisture cannot be read from any soil map; it stays a question."
---

# Ask the soil once, and let a bed differ

## What this is

After a garden is made, the user is asked once what the ground is. Every bed
drawn afterwards starts from that answer, and any bed can be told otherwise —
a raised bed with bought soil, a corner that gets watered.

## Decisions

### One question per garden

The shape Wave 8 settled on for building heights, for the same reason: asking
it of every bed is a wall in front of somebody who has just arrived, and the
answer is the same across most of a garden anyway.

### They stay fields, and they are not decoration

The user's first framing was to put soil and moisture in the free label, "like
the other objects". They are not like the other objects: `site_axes_from_soil`
turns them into three of the four Ellenberg axes the suggestions rank on. A
free label would have left the ranking on light alone, silently. What changed is
where the question is asked and how often — not what is kept.

### The garden's value is a starting point, not a broadcast

Changing it later never reaches back over a bed that already carries its own
answer. Overwriting something somebody set by hand is the kind of helpfulness
nobody asks for twice.

### Null until somebody says

A new garden has no soil. A default here would be a claim about a place nobody
has described, and the interface uses the null to know it still has to ask.

### A link out, not a guess

Most people do not know their soil type. The panel links to the BGR's soil maps
and offers the test that actually works in a garden — squeeze a handful of damp
earth; if it crumbles it is sandy, if it rolls into a sausage it is loam to
clay. Guessing it for them would put a number into the suggestions that nobody
gave.

## What was left out, and why it is written down

**Moisture will not come from a soil map.** A map says what the ground is made
of, not whether this corner is watered or drains into a ditch. Reading the soil
from an open source is research for a later wave; moisture stays a question
whatever that research finds.

## Definition of done

A new garden asks once, a bed drawn afterwards inherits it along with its axes,
a bed told otherwise keeps its own, and a later change to the garden leaves that
bed alone.
