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

    # ---- 2026-09-20, the second round: the states doc 102 left as gaps. ----
    # Read out of each state's own catalogue or directory index. A name that
    # carries a flight year or a delivery folder is *not* computable and is
    # marked so: for those the index is the entry, not the tile.
    Candidate("rp-lod2", "https://geobasis-rlp.de/data/geb3dlo/current/gml/LoD2_32_292_5548_2_RP.gml",
              "RP LoD2, 2 km, computable — listed in the state's own directory index"),
    Candidate("rp-laz", "https://geobasis-rlp.de/data/las/current/las/lpolpg_32_292_5548_1_rp.laz",
              "RP point cloud, 1 km, computable, about 4 points/m²"),
    Candidate("rp-dgm1", "https://geobasis-rlp.de/data/dgm1/current/tif/dgm1_32_419_5490_1_rp_2022.tif",
              "RP DGM1 — the name carries the flight year, so the metalink is the route"),
    Candidate("rp-dgm1-index", "https://geobasis-rlp.de/data/dgm1/current/meta4/dgm1_tif_07.meta4",
              "RP's metalink4 for the ground: every tile with its size and sha-256"),
    Candidate("rp-dom1-index", "https://geobasis-rlp.de/data/dom1/current/meta4/dom1_tif_07.meta4",
              "the same for the surface model, which is where the trees are"),

    Candidate("ni-lod2", "https://lod2.opengeodata.lgln.niedersachsen.de/LoD2_32_342_5824_1_ni.gml",
              "NI LoD2, 1 km, plain GML and no date in the name"),

    Candidate("bw-lod2", "https://opengeodata.lgl-bw.de/data/lod2/LoD2_32_513_5404_2_bw.zip",
              "BW LoD2, 2 km, zipped — the buildings its 5 m surface model cannot give"),
    Candidate("bw-ndom1", "https://opengeodata.lgl-bw.de/data/ndom1/ndom1_32_513_5404_2_bw.zip",
              "BW nDOM1: a 1 m canopy height model, already normalised to the ground"),
    Candidate("bw-catalogue", "https://opengeodata.lgl-bw.de/assets/config/local/odp-products.json",
              "BW's product catalogue — which products are live, and each one's name pattern"),

    Candidate("mv-lod2", "https://www.geodaten-mv.de/dienste/gebaeude_download"
                         "?index=0&dataset=8397b554-5cb9-4274-8be8-c20490d9a6e8"
                         "&file=lod2_33_206_5920_2_gml.zip",
              "MV LoD2, 2 km, zipped, behind a servlet with a fixed dataset id"),

    # Bayern's laser is on the catalogue host, not the download host: every
    # `download1.bayernwolke.de` path for it answers 404. Taken from the
    # product's own metalink, whose size and sha-256 the fetched file matched.
    Candidate("by-laser", "https://geodaten.bayern.de/odd_data/laser/690_5334.laz",
              "BY point cloud, 1 km — and unlike NRW's, classified into buildings and plants"),
    Candidate("by-laser-index",
              "https://geodaten.bayern.de/odd/a/laser/meta/metalink/09162000.meta4",
              "the per-municipality metalink for the laser, with a sha-256 per tile"),
    # Asked, and the answer is no: the file holds a position, the ground height
    # and the tree's height, and nothing else — no crown base, no species, no
    # crown width. The point cloud gives the crown base this could not.
    Candidate("by-einzelbaeume", "https://geodaten.bayern.de/odd/m/3/pdf/einzelbaeume_datenformat.pdf",
              "read the attribute list: has Einzelbäume gained a crown base or a species?"),

    # Thüringen names every tile from the grid — 16,945 of them checked against
    # the pattern with no exception — and wraps each in a zip.
    Candidate("th-dgm1", "https://geoportal.geoportal-th.de/hoehendaten/DGM/dgm_2020-2025/"
                         "dgm1_32_561_5609_1_th_2020-2025.zip",
              "TH ground, 1 km, zipped GeoTIFF beside an .xyz and a .meta"),
    Candidate("th-dom1", "https://geoportal.geoportal-th.de/hoehendaten/DOM/dom_2020-2025/"
                         "dom1_32_561_5609_1_th_2020-2025.zip",
              "TH surface, the same grid — the trees of Thüringen"),
    Candidate("th-las", "https://geoportal.geoportal-th.de/hoehendaten/LAS/las_2020-2025/"
                        "las_32_561_5609_1_th_2020-2025.zip",
              "TH point cloud, about 4 points/m², zipped LAZ"),
    Candidate("th-lod2", "https://geoportal.geoportal-th.de/3dgebaeude/LoD2/LoD2_32_598_5696_2_TH.zip",
              "TH LoD2, 2 km, zipped CityGML"),

    # Sachsen's filename is the grid too; what is not computable is the share
    # token, one per product and the same for every tile of it. HEAD answers
    # 401 here and a range answers 200, which is why the probe asks twice.
    Candidate("sn-dgm1", "https://geocloud.landesvermessung.sachsen.de/public.php/dav/files/"
                         "JCcXyifaNdLDnxZ/dgm1_33278_5590_2_sn_tiff.zip",
              "SN ground, 2 km, zipped GeoTIFF, zone glued to the easting"),
    Candidate("sn-dom1", "https://geocloud.landesvermessung.sachsen.de/public.php/dav/files/"
                         "S6wwnFwX7882sZm/dom1_33278_5590_2_sn_tiff.zip",
              "SN surface, the same grid"),
    Candidate("sn-lsc", "https://geocloud.landesvermessung.sachsen.de/public.php/dav/files/"
                        "EpkzyJHScGb5ndd/lsc_33278_5590_2_sn_laz.zip",
              "SN point cloud, at least 4 points/m², zipped LAZ"),
    Candidate("sn-lod2", "https://geocloud.landesvermessung.sachsen.de/public.php/dav/files/"
                         "AyJqXpJAZJXomCb/lod2_33278_5590_2_sn_citygml.zip",
              "SN LoD2, 2 km, zipped CityGML"),
    Candidate("sn-tokens", "https://geoviewer.sachsen.de/mapviewer/resources/apps/"
                           "produktdownload/app.json",
              "where Sachsen's share tokens are current — its own index has two stale ones"),

    # Saarland's licence was doc 102's open question and is answered: the
    # download is dl-de/by-2-0. What it has no route for is one tile — the
    # share holds six per-Landkreis archives and nothing smaller.
    Candidate("sl-dgm1-zip", "https://www.shop.lvgl.saarland.de/cloud/public.php/dav/files/"
                             "NK8ndP55qAqGEZD/OD_DGM1_2025_tif_LK/"
                             "DGM1_tif_NK_EPSG-25832_Entstehung-2025.zip",
              "SL ground: one Landkreis at a time, 559 MB, ranges allowed"),
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
