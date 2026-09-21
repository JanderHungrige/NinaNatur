---
id: 50-polygon-closing
title: An Overlap at the Start Is a Closure
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-12
wave_status: complete
depends_on: [43-shape-tools]
relates: [40-freehand-shapes, 49-drawing-focus]
source_files:
  - frontend/src/canvas/usePolygonDraft.ts
  - frontend/src/canvas/freehand.ts
routes: []
models: []
test_files:
  - frontend/src/canvas/usePolygonDraft.test.ts
data_flow: reads-existing
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [polygon, closing, geometry]
path: Canvas/Polygon
integration_contracts:
  - from: 40-freehand-shapes
    function: closeIfNear
    when: a drawn outline comes back to where it started
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# An overlap at the start is a closure

## The bug, reproduced before it was fixed

| Outline | self-intersects | result |
|---|---|---|
| 3 corners, nearly closed | no | closed |
| 4 corners, nearly closed | no | closed |
| 4 corners, **slightly past the start** | **yes** | *"Der Umriss überschneidet sich selbst"* |

The complaint was exact: it is the overlap, not the corner count. Going a little
past the first corner makes the closing edge cross the first one, and the check
that exists to catch a bow tie caught a closure instead.

## Decisions

### Close before checking

`closeIfNear` runs first and the three complaints follow. The order of those
complaints is unchanged — most specific first, so a bow tie is not told it needs
three corners — but closing is not a complaint, it is what the hand did.

### The same rule freehand already had

Freehand has closed a nearly-closed stroke since Wave 10, by dropping the
trailing corner rather than appending the first: a polygon is closed by being
one, and a near-duplicate first corner is a zero-length edge for everything
downstream to trip over. The two drawing paths now close the same way, from the
same function.

### Within twelve pixels (was: one grid square)

*Changed 2026-09-21 (doc 112).* The distance was the grid spacing, on the
grounds that corners snapped to it anyway. With snapped corners that dropped a
real one: a last corner exactly a square from the first counted as a closure, and
a 3 × 1 m bed was saved as a triangle. Now it is twelve screen pixels in metres —
the same reach freehand's closing uses — with a 5 cm floor where freehand keeps
50 cm (`useFreehandStroke`): a clicked corner is placed exactly, and 50 cm would
drop a small bed's real last corner when zoomed in, while a hand-drawn loop needs
the looser floor to close at all. "Near enough" still means the same on screen
at every zoom.

### Never below three corners

`closeIfNear` already refuses to drop a corner that would leave two. A triangle
whose last corner lands near its first stays a triangle.

## Definition of done

A four-cornered outline whose last corner overlaps the first closes; a bow tie
is still refused as crossing itself.
