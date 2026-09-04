---
id: 62-manual-colours
title: Hand-Entered Colours in the Shared Catalogue
edition: MDD
initiative: ninanatur
depends_on: []
relates: [61-planting-clusters]
source_files:
  - ninanatur/garden/observations.py
  - ninanatur/data/traits.py
  - ninanatur/api/candidates.py
  - ninanatur/ingest/migrations.py
routes:
  - PUT /api/v1/gardens/{token}/colours/{taxon_id}
models: [trait]
test_files:
  - tests/test_manual_colours.py
  - tests/test_observed_colour.py
data_flow: writes-existing
last_synced: 2026-09-04
status: complete
phase: all
mdd_version: 11
tags: [traits, provenance, colour, catalogue, migration]
path: Data/Colour
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Two gardeners who disagree about a species overwrite each other: the catalogue holds one manual value per species, last write wins."
---

# Hand-entered colours in the shared catalogue

## What this is

A colour somebody types into the info panel is written to `trait` with
`source='manual'`. It answers for every garden on the server, and any published
source outranks it.

## This reverses an earlier decision

The first version put these in `observed_colour` on the volume, one row per
garden, deliberately outside `trait` — for two reasons that were correct as far
as they went: a catalogue row would be overwritten by the next deployment, and
it would change every other garden's suggestions.

The gardener asked for the opposite, plainly. So the question became whether the
two objections actually hold.

**The deployment objection does not.** The catalogue sync is
`INSERT OR REPLACE`, which matches on the primary key, and `trait`'s key
includes `source`. A `manual` row has no counterpart in the shipped image, so
nothing replaces it. `test_a_deployment_does_not_wipe_it` runs a real
`sync_catalogue` and asserts the row is still there afterwards, because that is
the fact the whole design rests on.

**The other one holds, and is the point.** One person's entry answers for
everybody. That is what "general database" means. It is a test rather than a
footnote: `test_it_reaches_every_plan`, and the reversed
`test_a_colour_one_gardener_entered_answers_for_everybody`.

## Decisions

### `manual` ranks last, and not by being unknown

`SOURCE_PRIORITY` lists known sources best-first and puts unknown ones after
them. Appending `manual` to that tuple would have given it rank 2 while the next
source somebody adds lands at 3 — a hand entry would then outrank a real dataset
purely because it was named earlier. `source_rank` places it after everything
instead, so **every** published source beats it, including ones that do not
exist yet.

Losing does not delete it. Sources never overwrite each other in this database;
the manual value stays as an alternative, and the info panel says so: "eine
Quelle sagt inzwischen blau, und die gilt."

### The bulk loader had to learn about sources

`load_candidates` reads every trait row for the whole German flora in one query
and built its `extras` dict by letting the **last row win**. That was harmless
only because EIVE and GIFT overlap in zero trait keys, so nothing was ever
arbitrated.

Hand entries are the first time two sources claim the same key for the same
species. Without this, the suggestion list would have shown whichever row SQLite
happened to return last — a bug that appears and disappears with the query plan.
It now mirrors `traits._resolve_group`, and the two agreeing is the thing to
watch if either changes.

### The provenance rule applies to a person too

Written through `upsert_trait`, which raises without a source and a licence. The
licence is `user-contributed`, which is **not** an open-data licence and must
not pretend to be one — nobody asked the gardener to license their observation.
Saying so is what lets an export that has to respect licences filter on exactly
that string. Confidence is 0.4: one person looking at one plant.

### The old notes were carried over, once

`move_observed_colours` copies `observed_colour` into `trait` and marks itself
done in `catalogue_meta`. Run twice it would resurrect a note somebody has since
taken back — which is the whole reason for the marker.

Two gardens that noted different colours for one species cannot both win; the
later note is kept, the same rule a gardener's own second answer follows.

The table stays, empty. Dropping it would take the only copy of those notes with
it if the move ever has to be re-examined.
