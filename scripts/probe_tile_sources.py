"""Ask every tile source whether it is really there — Wave 25, feature 0.

Doc 68's rule, a third time: an entry in a registry means *this answered a real
request of ours*, not *a portal says it exists*. The registries for coverage
services were probed service by service; these are files, so they are probed
file by file, with a HEAD where the host allows one and a one-byte range where
it does not. Nothing large is downloaded: the question is whether a tile is
served anonymously, how big it is, and what it says it is.

Run it deliberately, never from the test suite — a test that needs sixteen
state portals to be up is a test that fails on their maintenance window:

    python -m scripts.probe_tile_sources            # every candidate
    python -m scripts.probe_tile_sources bayern     # one, by name

Write the date it was run into the doc, as doc 68 and doc 80 did.
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass

import requests

from ninanatur.ingest.http import REQUEST_DELAY_S, USER_AGENT

#: Generous: these are state surveying offices, not an API with a quota.
POLITE_S = max(REQUEST_DELAY_S, 1.0)
TIMEOUT_S = 30


@dataclass(frozen=True)
class Candidate:
    """One thing to ask for, and why it is being asked."""

    name: str
    url: str
    #: What the entry would be for, if it answers.
    about: str


#: A tile somewhere over each state's own territory, in that state's own
#: scheme. Bayern's numbers are the plan's verified pair (UTM32, km).
CANDIDATES: tuple[Candidate, ...] = (
    Candidate("bayern-dgm1", "https://download1.bayernwolke.de/a/dgm/dgm1/690_5334.tif",
              "DGM1 as a 1 km GeoTIFF, CC-BY-4.0"),
    Candidate("bayern-lod2", "https://download1.bayernwolke.de/a/lod2/citygml/690_5334.gml",
              "LoD2 buildings as CityGML, CC-BY-4.0"),
    # Not on the download host — that path answers 404, which is how the plan's
    # citation was found to be wrong (doc 102).
    Candidate("bayern-index", "https://geodaten.bayern.de/odd/a/dgm/dgm1/meta/metalink/09162000.meta4",
              "the per-municipality index with SHA-256 sums"),
    Candidate("nrw-laz", "https://www.opengeodata.nrw.de/produkte/geobasis/hm/3dm_l_las/3dm_l_las/3dm_32_347_5647_1_nw.laz",
              "the laser point cloud, dl-de/zero-2-0"),
    Candidate("nrw-lod2", "https://www.opengeodata.nrw.de/produkte/geobasis/3dg/lod2_gml/lod2_gml/LoD2_32_347_5647_1_NW.gml",
              "LoD2 buildings in NRW's own tile scheme"),
    Candidate("nrw-laz-index", "https://www.opengeodata.nrw.de/produkte/geobasis/hm/3dm_l_las/3dm_l_las/index.json",
              "the point cloud's tile index"),
    Candidate("copernicus-glo30",
              "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N51_00_E007_00_DEM/"
              "Copernicus_DSM_COG_10_N51_00_E007_00_DEM.tif",
              "a horizon ring for the states with no service"),
    # Both questions feature 0 existed to answer were answered on 2026-09-20,
    # and neither by a status code — the pages are JavaScript and had to be
    # read (doc 102). Kept here so the next probe re-checks them:
    #   LoD2-DE  — exists, "nur fuer Bundesbehoerden", so feature 3 stays
    #              per-state. Search the catalogue for 3D-Gebaeudemodelle.
    #   Niedersachsen — LoD2, bDOM20, DGM1 and DOM1 open, no laser data listed.
    Candidate("bkg-catalogue", "https://gdz.bkg.bund.de/index.php/default/catalogsearch/result/?q=3D-Geb%C3%A4udemodelle",
              "read the result: is LoD2-DE open yet, or still Bundesbehoerden only?"),
    Candidate("niedersachsen-portal", "https://ni-lgln-opengeodata.hub.arcgis.com/pages/opengeodata",
              "read the Geotopographie list: has laser data appeared?"),
)


def ask(url: str) -> str:
    """What this URL answers, in one line. HEAD first; a range if HEAD is not
    allowed, because some stores answer 405 to it and 206 to a range."""
    try:
        head = requests.head(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S,
                             allow_redirects=True)
        if head.status_code < 400:
            return _describe(head.status_code, head.headers)
        ranged = requests.get(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"},
                              timeout=TIMEOUT_S, allow_redirects=True, stream=True)
        ranged.close()
        return _describe(ranged.status_code, ranged.headers, after=f"HEAD {head.status_code}")
    except requests.RequestException as trouble:  # noqa: BLE001 - reported, not raised
        return f"no answer: {type(trouble).__name__}"


def _describe(status: int, headers: object, after: str = "") -> str:
    got = getattr(headers, "get", lambda _k, _d=None: None)
    size = got("Content-Range") or got("Content-Length") or "?"
    kind = got("Content-Type") or "?"
    return f"{status} {size} {kind}" + (f" (after {after})" if after else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("only", nargs="*", help="probe only candidates whose name contains this")
    chosen = parser.parse_args().only
    wanted = [c for c in CANDIDATES
              if not chosen or any(part in c.name for part in chosen)]
    print(f"{len(wanted)} candidates, {POLITE_S:.0f}s apart\n")
    for candidate in wanted:
        print(f"{candidate.name:22s} {ask(candidate.url)}")
        print(f"{'':22s} {candidate.about}")
        print(f"{'':22s} {candidate.url}\n")
        time.sleep(POLITE_S)
    return 0


if __name__ == "__main__":
    sys.exit(main())
