---
id: 63-neighbours-from-the-plot
title: The Neighbours a Garden Actually Has
edition: MDD
initiative: ninanatur
depends_on: []
relates: []
source_files:
  - ninanatur/geo/surroundings.py
  - ninanatur/geo/osm.py
  - ninanatur/geo/projection.py
  - ninanatur/api/geo.py
routes:
  - POST /api/v1/gardens/from-map
models: [element]
test_files:
  - tests/test_surroundings_reach.py
  - tests/test_osm.py
  - tests/test_map_selection.py
data_flow: reads-existing
last_synced: 2026-09-04
status: complete
phase: all
mdd_version: 11
tags: [osm, overpass, shading, geometry, surroundings]
path: Map/Surroundings
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "A building is still drawn as a square of equal footprint area rather than its real outline, though the outline is now fetched and could be used."
---

# The neighbours a garden actually has

## What went wrong

Reported with three screenshots: a farmyard with four or five buildings plainly
drawn on OpenStreetMap and visible on the aerial photo arrived in the plan as
**one** small square.

Not a gap in OSM. Everything was in the data; the pipeline threw it away in
three places, and all three had the same shape — **measuring from a point where
a garden is a plot**.

## What it was

### The box was drawn around the centroid

`bounding_box(anchor, MARGIN_M)` put a 50 m box around the middle of the
outline. On a 60 m deep plot that reaches 20 m past the hedge, not 50. The
neighbours were never fetched at all, so no filter downstream had a chance to
keep them.

Measured against live Overpass data for a village plot: **32 buildings fetched
with the old box, 63 with the new one.**

### The keep-filter used the building's centre

A building was kept only if its *centre* lay inside that box. A long barn whose
wall is five metres from the boundary has its centre forty metres further off.
The code right below already knew better — "distance to the nearest part of the
building, not to its centre" — and the box above it did the opposite.

### Distance was measured to the centroid too

The reach filter asked whether a shadow could travel from the building to the
middle of the garden. It should ask whether it reaches the garden at all, which
is the nearest point of the outline. On a 60 m plot those differ by 30 m —
enough to decide it either way for an ordinary house.

**In the plan: 6 buildings before, 31 after.**

## Two more, found while fixing it

### Only ways were asked for

`way["building"]` and not `relation["building"]`. A building drawn as a
multipolygon — a courtyard, a farm range, anything with a hole — is a relation
and was dropped without a word.

Honestly: at the sample location this changed **nothing**, 63 either way. It is
a correctness fix that costs nothing, not the cause of what was reported, and
saying otherwise would be claiming a result that was not measured.

### Every building was the same size

`out tags center` returns one point and no extent, so `_radius_of` fell back to
a flat 5 m for every building. That is why the one house that did survive was
drawn as a small square next to a large barn — and it fed the reach filter a
wrong distance too, since the near wall of a big building is much closer than
`centre − 5 m`.

`out tags geom` returns the node list. The payload is larger; the disk cache
means a rerun costs nothing, which is the rule this project already works to.
The drawn squares now range from 9.9 m to 22.5 m at the sample instead of all
being 8.9 m.

A test asserting the old choice — "a centre is all the shading model needs" —
was reversed rather than deleted. It was a reasonable belief and it was wrong.

## What did not change

The reach filter still bounds the result: a 2 m shed at 60 m is still dropped,
and the margin still ends at 50 m from the boundary. Widening a box without
that would put every shed in the village on the plan.
