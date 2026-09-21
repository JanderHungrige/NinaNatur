---
id: 114-the-ground-around-the-garden
title: The Ground Around the Garden
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [31-map-selection, 59-osm-streets, 96-a-theme-is-a-thing, 106-which-source-said-so, 113-a-plan-that-keeps-up]
relates: [65-the-shade-switch, 68-which-ground-and-whose, 97-draft-sketch-in-svg, 112-drawing-at-any-zoom]
source_files:
  - ninanatur/geo/osm_landcover.py
  - ninanatur/geo/landcover_clip.py
  - ninanatur/geo/landcover_store.py
  - ninanatur/garden/landcover_sync.py
  - ninanatur/api/landcover.py
  - ninanatur/api/geo.py
  - ninanatur/api/light.py
  - ninanatur/garden/credits.py
  - ninanatur/ingest/schema_computed.py
  - frontend/src/canvas/landcover.ts
  - frontend/src/components/LandcoverLayer.tsx
  - frontend/src/components/LandcoverAreas.tsx
  - frontend/src/components/CanvasScene.tsx
  - frontend/src/components/GardenCanvas.tsx
  - frontend/src/components/PlanCredit.tsx
  - frontend/src/garden/useDerived.ts
  - frontend/src/garden/useLandcover.ts
  - ninanatur/api/ratelimit.py
  - frontend/src/garden/useGarden.ts
  - frontend/src/api/client.ts
  - frontend/src/styles.css
  - frontend/src/themes/draft-sketch/theme.css
routes:
  - GET /api/v1/gardens/{token}/landcover
  - POST /api/v1/gardens/from-map
  - POST /api/v1/gardens/{token}/light
models: [garden_landcover]
test_files:
  - tests/test_osm_landcover.py
  - tests/test_landcover_clip.py
  - tests/test_landcover_api.py
  - tests/test_landcover_sync.py
  - tests/test_landcover_background.py
  - tests/test_no_network.py
  - tests/test_security_matrix.py
  - tests/test_plan_stylesheet.py
  - frontend/src/canvas/landcover.test.ts
  - frontend/src/components/LandcoverLayer.test.tsx
  - frontend/src/components/GardenCanvas.memo.test.tsx
  - frontend/src/components/PlanCredit.test.tsx
  - frontend/src/App.landcover.test.tsx
data_flow: greenfield
last_synced: 2026-09-21
status: complete
phase: all
mdd_version: 11
tags: [osm, overpass, landuse, landcover, plan, surroundings, clip, react-memo, attribution, owner-check]
path: Geo/Landcover
integration_contracts:
  - from: 106-which-source-said-so
    function: credits_for(landcover=...)
    when: the plan draws OpenStreetMap's land
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "A garden made before this feature, with no OpenStreetMap streets of its own, gets its surroundings from the stored anchor, which is rounded to four places: up to about 6 m off (placed_by = 'anchor'). With streets the offset is read off them (placed_by = 'streets')."
  - "The areas reach 150 m past the plot. Zoomed out past about 330 m the edge of that box shows as a straight line where the colours stop."
  - "OpenStreetMap maps private plots as 'residential' almost everywhere (measured: the Kleinmachnow plot lies in one landuse=residential polygon). The plot is cut out and keeps its own ground; the neighbours' gardens stay the palest neutral."
  - "Relation assembly is tested on canned answers only. The one live request used `out tags geom`, which leaves relations' members out; the query now says `out geom`, not re-measured live (one request, as agreed)."
  - "The buildings query in `geo/osm.py` still says `out tags geom`, so its multipolygon buildings arrive without members and are skipped — the same finding, outside this feature."
  - "The shade rebuild of a garden that has no surroundings yet costs one Overpass request after its answer, two where the garden has OSM streets (the offset), once per garden and never two at a time. A failure is left alone for six hours; the pause is kept in memory, so a restart forgets it and costs one more attempt. A fetch skipped for want of room records nothing, so a later rebuild asks again."
  - "`frontend/src/api/client.ts` was 602 lines before this feature and is 609 after; the length hook asks for a split of the client, which is not this feature's to make."
sister_projects: []
---

# 114 — The Ground Around the Garden

## What the owner decided (2026-09-21, #10)

> For colouring the ground: OSM landcover

Until now everything outside the plot was blank paper. The plan drew the paper,
the grid, the relief when the shade was on, and the elements; streets and
houses came from the map import, and the woods, fields and water between them
were not there at all.

## What OpenStreetMap has around a garden (measured once)

One request for a 20 × 25 m plot at Kleinmachnow, Am Weinberg (52.3962,
13.2322), with the 150 m margin: **3.7 s, 9,415 bytes**, ten elements (nine
ways, one relation). One `landuse=residential` polygon holds the plot; around
it a wood, four car parks, two sports pitches and a commercial estate. Cut to
the box: 9 areas, 9 rings, 76 points, **1,337 bytes** stored. The wood's second
part was a multipolygon relation, and it came back as tags and a bounding box
with no members — the query said `out tags geom`, and at `tags` Overpass leaves
members out. It says `out geom` now.

## The classes

Eight, because the plan is about a garden and its surroundings need to read as
wood, field, water, houses — not as the forty values `landuse` takes.

| Class | OpenStreetMap | Painted as |
|---|---|---|
| grass | landuse grass, meadow, village_green, recreation_ground, cemetery; leisure park, pitch; natural grassland, heath | the theme's `grass` |
| wood | landuse forest; natural wood, scrub | the theme's `foliage` |
| water | natural water; landuse basin, reservoir | the theme's `water` |
| field | landuse farmland, orchard, vineyard | `--wash-field` |
| allotments | landuse allotments; leisure garden | the theme's `planting` |
| residential | landuse residential, farmyard | `--wash-residential`, the palest neutral |
| built | landuse commercial, retail, industrial | the theme's `tarmac` |
| paved | amenity parking | the theme's `tarmac` |

An area with two of these tags is decided by `natural`, then `landuse`, then
`leisure`, then `amenity`: water is water whatever the land around it is called.

## The query and the rings (`geo/osm_landcover.py`)

One Overpass query, built from the table: every way and multipolygon relation
the box touches, and — through `is_in` and `pivot` — every one the garden's
centre lies inside. A box query only finds an area whose outline crosses the
box; the residential quarter that holds the whole box has none there.

A closed way is a ring. A multipolygon's member ways are joined end to end,
whichever way each was drawn, into closed outer and inner rings. **A chain that
cannot be closed is dropped, never drawn**: filled, an open line closes itself
with a straight edge, a wedge across the plan. An answer is capped at 20 MB (a
forest relation arrives whole); a malformed one is no areas, and one Overpass
says it gave up on raises, exactly as the streets do.

## Cut to the plan (`geo/landcover_clip.py`)

Each ring is turned into garden metres and cut to a box 150 m around the plot
with Sutherland–Hodgman against the four half-planes — no polygon library for
a rectangle. Points are rounded to decimetres, repeats dropped, and a piece
under 2 m² — a sliver along the box's edge — is left out. Outer rings run
anticlockwise and holes clockwise, so the page fills with the **nonzero** rule:
two overlapping lawns (a meadow in a park) stay one lawn, where even-odd would
cut their overlap out as a hole.

## Kept per garden, never as elements

`garden_landcover` (computed schema): one row per garden, the areas as JSON,
`placed_by` and `fetched_at`. Elements would stretch the light grid over a
forest's corner and coarsen the shade raster with it (`lightgrid_extent`), and
every meadow would appear in the element list and the plan's count. A row of
`[]` is an answer — nothing mapped — and is not asked for again.

## When it is fetched (`garden/landcover_sync.py`)

Both fetches run **after the answer has gone out**, as background tasks
(`add_later`, `fetch_later`) on a connection of their own, with **one attempt**
and no back-off. They were inside the requests at first, and the review found
"Sonne & Schatten" — the button the owner had just called endless — waiting on
up to two Overpass requests with retries, again on every press while Overpass
failed. The routes' heavy slot is let go when their own work ends
(`scope="function"`), so the waiting holds none. A failure is remembered for six
hours by the garden's share token (an id is reused after a delete, a token
never); a street fetch that fails still keeps the land, placed from the anchor.
With the slot gone, nothing else bounded them, so one garden is fetched once at
a time and at most two rebuild fetches run at once (`MAX_BACKGROUND_FETCHES`): a
press while its garden is being fetched, or with no room, is skipped and records
no failure. A new garden's fetch is never skipped for room — only the import
knows the exact anchor, and the from-map route's own limit bounds how many there
are. A garden whose answer is stored, nothing mapped included, is not scheduled
at all. The tasks carry the token, not the id, and save only if the token still
names the same garden: one deleted while Overpass was asked leaves its land and
its pause to nobody. The log names a garden by `short_hash` of its token, as the
access log does, never by the token's first characters.

- **At creation from the map**, after the streets, from the **exact** centre of
  the outline — the anchor the streets and houses were placed by. A refusal
  costs the colours, not the garden (`placed_by = 'map'`).
- **After the shade rebuild** (`POST /light`), for a garden that has none yet — made before this feature, or whose first fetch
  failed — under the terrain's `is_precise` guard. The stored anchor is rounded
  to four places, so a fetch from it sits up to about 6 m off the imported
  streets and houses. Where the garden holds OpenStreetMap's streets, the same
  streets are fetched again and every pair of a stored and a fetched point
  within 8 m votes for their difference; the true offset gathers a vote from
  every node, so the most common one (at least three agreeing) is taken and
  the land moved by it (`placed_by = 'streets'`). Otherwise the land stays
  where the stored anchor puts it (`placed_by = 'anchor'`).

Never on a page load. `GET /gardens/{token}/landcover` reads the row: the
areas, and OpenStreetMap's attribution and licence. 404 for a token that names
no garden; an empty list for a garden that has none.

## On the plan

`LandcoverLayer` lies between the grid and the relief, outside the filtered
objects group, so every street and house — elements — is drawn over it. One
path per class, the class with the largest single area first, so it lies
behind: the residential quarter under the park in it, the wood under its pond.
It is painted through the theme's own symbols, so both themes draw it without
theme code, and with two flat washes for what has no symbol, in light, dark and
on Draft Sketch's paper.

- **Context, not content**: `fill-opacity` 0.45 per path (a group's opacity is
  one more offscreen image per frame), no outline, `aria-hidden`, never a
  target, and gone entirely under more contrast or forced colours.
- **The plot is cut out** of every class, so "residential" never tints the
  garden: a clip whose path is a frame round the land with the plot inside it,
  under the even-odd rule. A clip, not a mask: a mask is an offscreen image
  painted again on every frame of a pan.
- **Memoised** on the data, the plot, the theme and the scale in halvings, never
  the view, so a pan never draws it again (doc 113). `GardenCanvas.memo.test`
  counts it through a pan and a wheel.

The page asks for it on opening in a hook of its own (`useLandcover`), outside
the `Promise.all` of `useDerived`: it is decoration, so a slow answer does not
hold up "geladen" and a failed one does not say "Laden fehlgeschlagen" — it is
logged. The server fetches it after answering, so an empty answer is asked
again after 5, 20 and 60 s, and the count starts over once a shade rebuild
lands, which is where an older garden first gets it. It is drawn whether the
shade is on or not.

## The credit

ODbL asks for the credit where the map's data is shown. `credits_for` names
OpenStreetMap when the plan draws its land (`draws_landcover`: a row with areas
in it), and the plan's caption (`drawsOpenStreetMap`, `PlanCredit`) says
*Karte: © OpenStreetMap-Mitwirkende* for it as well — a garden drawn by hand
gets both on its first rebuild (doc 106).

## Business rules

1. The surroundings are OpenStreetMap's, credited wherever they are drawn.
2. They are never elements, and never reach the light model.
3. An area that cannot be closed is not drawn.
4. Nothing is fetched on a page load; creation and the shade rebuild fetch,
   after their answers.
5. A failure costs the colours, never the garden or its light.
6. The plot keeps its own ground: no class tints it.
7. A pan never redraws the layer.

## Security

The endpoint takes the token and nothing else, answers 404 for a token that
names no garden (`test_security_matrix`), and reads one row. The query is built
from the table and a box of floats; nothing a visitor sends reaches it. Tests
never reach Overpass: conftest switches `landcover_sync`'s two fetches off and
gives the background task no connection unless a test hands it its own, and
`test_no_network` fails if a second module starts asking for the land.
