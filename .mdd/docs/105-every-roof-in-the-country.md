---
id: 105-every-roof-in-the-country
title: Every Roof in the Country
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [102-which-tiles-and-whose, 40-lod2-roofs]
relates: [103-a-tile-not-a-service, 93-where-the-roof-came-from, 94-which-way-the-ridge-runs]
source_files:
  - ninanatur/garden/building_sync.py
  - ninanatur/geo/tile_zip.py
  - ninanatur/geo/lod2.py
  - ninanatur/geo/tile_sources.py
routes: []
models: []
test_files:
  - tests/test_lod2_states.py
  - tests/fixtures/lod2_bayern_building.gml
data_flow: mixed
last_synced: 2026-09-20
status: complete
phase: all
mdd_version: 11
tags: [lod2, citygml, roofs, buildings, bayern, survey, open-data]
path: Geo/LoD2 states
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 105 — Every Roof in the Country

## Purpose

A surface model says how tall a building is. Only the official 3D model says
what shape its roof has, where its eaves are and which way its ridge runs —
everything Waves 19 and 21 work out the hard way from an nDOM and OSM storeys.
Doc 40 built that reader for Nordrhein-Westfalen, the only state anybody had
asked. This asks the others.

## The finding: Bayern needed no adapter

The wave planned a dozen adapters, on the reasonable assumption that other
states would differ — CityGML 2.0 namespaces, a different roof coding, parts
where NRW has none. Bayern's tile, read on **2026-09-20**:

```
xmlns:bldg="http://www.opengis.net/citygml/building/1.0"
xmlns:gml="http://www.opengis.net/gml"
<bldg:measuredHeight uom="urn:adv:uom:m">11.715</bldg:measuredHeight>
<bldg:roofType>1000</bldg:roofType>
```

The same CityGML 1.0, the same `bldg:` namespace, `measuredHeight` in metres
and AdV's Dachform keys — which `ADV_ROOFS` already maps. The reader built for
NRW reads a Bavarian building unchanged, and
`tests/fixtures/lod2_bayern_building.gml` is that building, cut out of the tile
the probe fetched, kept so the claim is checked against the state's own file
rather than one this repository wrote to its own expectations.

So feature 3 is not a dozen parsers. It is plumbing, and one raised guard.

## What actually had to change

- **The state is a registry question now.** `_surveyed` used to begin
  `if state != "Nordrhein-Westfalen": return None` and build NRW's URL by hand.
  It asks `lod2_tiles_for(state)` and takes the address from there, so a state
  joins by being probed into doc 102's registry and nothing else.
- **The tile guard was refusing the data.** `MAX_TILE_BYTES` was 150 MB — four
  times Cologne's 38 MB, which was the largest tile anybody had seen. One
  square kilometre of Munich is **161,627,079 B**. A guard that refuses the
  product has stopped guarding anything, so it is twice the largest measured.
- **Bayern's solid references its faces** by `xlink:href` rather than repeating
  their geometry. It reads anyway: the labelled `bldg:boundedBy` surfaces carry
  the polygons, and those are what the reader takes.

## What is deliberately not done

**One tile, the garden's own.** A neighbour across a kilometre line keeps
whatever height it had. The window (doc 103) fetches every tile it touches
because ground at the edge of a garden is the garden's ground; a building fifty
metres away across a tile line is worth less than the 20 to 161 MB of the three
other tiles.

**The tile is never cached.** A few hundred bytes per building is what is kept;
the document is streamed, parsed and dropped (doc 103's rule for CityGML).

## Which states are in

**Eight, as of 2026-09-20** — Bayern and Nordrhein-Westfalen, then
Niedersachsen, Thüringen, Sachsen, Brandenburg, Berlin, Mecklenburg-Vorpommern
and Baden-Württemberg. Every one by request, and every one read by the same
reader: doc 105's finding held for all of them, so feature 3 never did become
a dozen parsers.

Two things had to be true and were. **Niedersachsen's LoD2 turned out to be
computable** — it moved to a flat, dateless layout, and the portal's own
GeoJSON index still points at the old dated paths, which now 404. And the other
six **arrive zipped**, which doc 103 now unwraps; the CityGML inside is
unchanged, except that Berlin calls it `.xml`.

**Baden-Württemberg needed two small things of its own.** Its two-kilometre
archive holds four one-kilometre tiles, so all four are read — a quarter of a
neighbourhood is not a neighbourhood — and its grid starts on an **odd**
easting, so flooring to even numbers asks for a tile that does not exist.

Rheinland-Pfalz's LoD2 is verified and waiting on its ground (doc 102), and
Schleswig-Holstein's is computable and waiting for the same reason. Hessen,
Sachsen-Anhalt, Hamburg, Bremen and Saarland publish no addressable tile.

The federal LoD2-DE would have replaced all of them and does not: it is
restricted to federal authorities (doc 102).

## Business Rules

1. **A state has a building model when the registry says so**, never an `if`
   in the sync.
2. **A measured roof beats an assumed one, and a user's word beats both** —
   unchanged from doc 93's order of truth.
3. **The tile is read and dropped.**
4. **A guard is a bound on what is reasonable, not on what exists**: when the
   data outgrows it, the measurement moves the guard.

## Dependencies

Doc 40 (the CityGML reader), doc 102 (the registry), doc 93 and 94 (what a
measured roof is allowed to change).

## Security

The tile's address comes from the registry's template and two integers, and the
document is refused by size before it is parsed. `defusedxml` reads it, as it
always has.

## Known Issues

- One tile per garden (above): a neighbour across a kilometre line is not
  measured.

## Bugs
