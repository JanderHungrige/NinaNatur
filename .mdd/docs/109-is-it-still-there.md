---
id: 109-is-it-still-there
title: Is It Still There
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-25
wave_status: active
depends_on: [102-which-tiles-and-whose, 103-a-tile-not-a-service]
relates: [68-terrain-sources, 80-surface-sources, 106-which-source-said-so]
source_files:
  - ninanatur/geo/health.py
  - scripts/check_sources.py
  - ninanatur/ingest/http.py
routes: []
models: []
test_files:
  - tests/test_health.py
data_flow: reads-existing
last_synced: 2026-09-20
status: complete
phase: all
mdd_version: 11
tags: [health, monitoring, registry, open-data, provenance, cron]
path: Geo/Source health
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 109 — Is It Still There

## Purpose

Forty-nine sources across sixteen state surveying offices, and not one of them
owes us notice before it moves. In the two days this registry took to build,
four of them changed under it:

- **Bayern's laser** is not on the download host at all; every path there is a
  404, and its address had to come out of the product's own metalink.
- **Niedersachsen's LoD2** moved to a flat, dateless layout, and the portal's
  own GeoJSON index still points at the old paths — which now 404.
- **Sachsen's** download index carries two share tokens that no longer work,
  while its viewer's configuration carries the working set.
- **Schleswig-Holstein** answers a stale row with **HTTP 200 and an HTML
  apology**, not a 404.

A registry whose rule is *an entry is a request that was answered* (doc 102)
needs a way to ask again.

## A status code is not an answer

That last one is why this could not be a ping. Every one of Niedersachsen's
dead tiles is listed by a live index; Schleswig-Holstein's apology is a 200.
A checker that read status codes would have called all of it healthy.

So a source passes only when what comes back **is what it claims to be** — a
TIFF that begins `II*`, a CityGML with a root element, a LAZ whose header says
`LASF`, an archive whose directory still holds a square kilometre. Three
verdicts, and the middle one is the useful one:

| | |
|---|---|
| **ok** | it answered, with what it claims to be |
| **changed** | it answered with something else — another format, or a size that is not a new flight over the same ground |
| **gone** | it did not answer |

## Silent is not absent

The first run reported Bayern's laser gone, and it was not. That host serves no
range **and** states no `Content-Length`, so neither looking inside nor
measuring works: the only proof would be downloading a hundred and twelve
megabytes, which is not a weekly check.

So "does this answer" became a different question from "how large is it"
(`http.presence`), and a source that answers without saying is reported
**ok, not sampled** rather than healthy or gone. A check that cannot look
should say it did not look.

## What it asks, and what it costs

Each entry is asked for the one square kilometre the registry recorded it at —
which is why `probed_tile` now sits beside `probed_bytes`, so there is
something to compare like with like. A source found through a list or an
archive needs none: reading the list *is* the check, and whichever tile it
names first will do.

One small request per source, four kilobytes off the front, a second apart.
Forty-nine sources in about two minutes. Sixteen offices publishing at their
own expense are not an API with a quota, and a weekly check that downloads a
gigabyte is a check that gets turned off.

**Baseline, 2026-09-20: 49 of 49.**

## Not a test, on purpose

Doc 102's rule, kept: a suite that needs sixteen state portals to be up fails
on their maintenance window, teaches people to ignore red, and says nothing
about this repository's code. The logic lives in `geo/health.py` and is tested
offline against injected portals — including each of the four failures above —
while the thing that touches the network is a script, run deliberately, whose
exit code is the signal:

```
17 4 * * 1  cd /srv/ninanatur && .venv/bin/python -m scripts.check_sources --quiet \
            || mail -s "NinaNatur: a source moved" you@example.de
```

## Business Rules

1. **A source passes on its bytes, never on its status code.**
2. **Silent is not absent**: a host that answers without saying how much is ok
   and reported as unread.
3. **One small request per source**, with a pause, and never a whole tile.
4. **The check is a script, not a test**, and its exit code is the alarm.
5. **A change is a re-probe, not a patch**: when this goes red the registry and
   its doc are updated from a fresh request, because an entry is a request that
   was answered and that one no longer is.

## Dependencies

Doc 102 for the registry and its rule, doc 103 for the three ways a tile has an
address — all three of which this must know, or a whole class of source goes
unwatched — and `ingest/http.py` for the fetch.

## Security

Every address checked comes from the registry, never from a garden. The checker
writes nothing and reads at most four kilobytes of each source.

## Known Issues

- **Sachsen and Mecklenburg-Vorpommern state no size**, so drift cannot be seen
  there — only presence and format.
- **A whole-tile decode is not exercised.** The check reads a header, so it
  would not catch a state re-encoding its tiles in a way the reader chokes on;
  that is what found the quadratic LZW decoder (doc 103), and it took a real
  square kilometre.
- The orthophoto registry (doc 8) and OSM are not checked yet.

## Bugs
