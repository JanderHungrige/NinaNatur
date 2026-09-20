"""Every tile source, one per state and product — Wave 25, doc 102.

The entries themselves, kept apart from `tile_sources.py` because this is a
list that grows with every state probed and that is an interface that does not.
Nothing here is imported directly: `tile_sources` is the way in.

**An entry is a request of ours that was answered**, dated, by
`scripts/probe_tile_sources.py`. A state with nothing gets no entry, and a
licence that forbids this use is a state without an entry.

A **state's** licence, credit and UTM zone are written once, in `TERMS`. They
belong to the state rather than to each of its products, and repeated per
product they drift — Bayern's laser carried a credit one word different from
its ground until they were put in one place.
"""
from __future__ import annotations

from geokachel.tile_grid import TileLookup, TileProduct, TileSource, under
from geokachel.tile_index import from_geojson_links, from_metalink
from geokachel.tile_naming import (
    SH_DOWNLOAD,
    adv_name,
    bayern_dom_name,
    bayern_name,
    bayern_url,
    bb_name,
    bb_url,
    bremen,
    nrw_name,
    saarland,
    sh_block,
    sh_lod2,
    sh_named,
    sn_name,
    sn_url,
    th_name,
    th_url,
)
from geokachel.tile_terms import terms

TILE_SOURCES: tuple[TileSource, ...] = (
    TileSource(
        name="by-dgm1", **terms("BY"), product=TileProduct.DGM1, tile_km=1, fmt="GeoTIFF",
        _url=bayern_url("dgm/dgm1", "tif"), _name=bayern_name,
        vertical_step_m=0.01, probed_bytes=2_558_672,
        # Not on the download host: that path answers 404 (doc 102).
        index_url="https://geodaten.bayern.de/odd/a/dgm/dgm1/meta/metalink/",
        probed_tile=(690, 5334),
    ),
    TileSource(
        name="by-dom20", **terms("BY"), product=TileProduct.DOM, tile_km=1, fmt="GeoTIFF",
        _url=lambda e, n: ("https://download1.bayernwolke.de/a/dom20/DOM/"
                           f"{bayern_dom_name(e, n)}.tif"),
        _name=bayern_dom_name,
        cell_m=0.2, vertical_step_m=0.01, probed_bytes=48_441_449,
        index_url="https://geodaten.bayern.de/odd/a/dom20/meta/DOM/metalink/",
        probed_tile=(690, 5334),
    ),
    TileSource(
        name="by-lod2", **terms("BY"), product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        _url=bayern_url("lod2/citygml", "gml"), _name=bayern_name,
        probed_bytes=161_627_079,
        probed_tile=(690, 5334),
    ),
    TileSource(
        # Not on the download host either: every bayernwolke path for the laser
        # answers 404, and this address came out of the product's own metalink.
        # Classified, unlike NRW's: class 6 buildings, class 20 plants (doc 107).
        name="by-laser", **terms("BY"), product=TileProduct.LAZ, tile_km=1, fmt="LAZ",
        _url=lambda e, n: f"https://geodaten.bayern.de/odd_data/laser/{e}_{n}.laz",
        _name=bayern_name,
        # The state guarantees four per m² since 2012; Munich measures twenty.
        points_per_m2=4.0, probed_bytes=112_064_676,
        index_url="https://geodaten.bayern.de/odd/a/laser/meta/metalink/",
        probed_tile=(690, 5334),
    ),
    TileSource(
        name="nw-lod2", **terms("NW"), product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        _url=lambda e, n: ("https://www.opengeodata.nrw.de/produkte/geobasis/3dg/lod2_gml/"
                           f"lod2_gml/{nrw_name(e, n, 'LoD2', 'NW')}.gml"),
        _name=lambda e, n: nrw_name(e, n, "LoD2", "NW"),
        probed_bytes=20_684_673,
        probed_tile=(347, 5647),
    ),
    TileSource(
        name="nw-laz", **terms("NW"), product=TileProduct.LAZ, tile_km=1, fmt="LAZ",
        _url=lambda e, n: ("https://www.opengeodata.nrw.de/produkte/geobasis/hm/3dm_l_las/"
                           f"3dm_l_las/{nrw_name(e, n, '3dm', 'nw')}.laz"),
        _name=lambda e, n: nrw_name(e, n, "3dm", "nw"),
        points_per_m2=4.0, probed_bytes=34_967_590,
        index_url=("https://www.opengeodata.nrw.de/produkte/geobasis/hm/3dm_l_las/"
                   "3dm_l_las/index.json"),
        probed_tile=(347, 5647),
    ),
    TileSource(
        name="ni-lod2", **terms("NI"), product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        _url=lambda e, n: ("https://lod2.opengeodata.lgln.niedersachsen.de/"
                           f"{adv_name('LoD2', e, n, suffix='ni')}.gml"),
        _name=lambda e, n: adv_name("LoD2", e, n, suffix="ni"),
        probed_bytes=43_632,
        probed_tile=(342, 5824),
    ),

    # ---- The last two. Both publish their ground as XYZ text, which is why
    # they were the last two states with none (doc 103).
    TileSource(
        # The terrain model's name carries the survey year — 2005 in one tile
        # and 2025 in its neighbour — so the state's own list is the only route.
        name="sh-dgm1", **terms("SH"), product=TileProduct.DGM1, tile_km=1, fmt="XYZ",
        lookup=TileLookup(
            index_url=("https://geodaten.schleswig-holstein.de/gaialight-sh/_apps/"
                       "dladownload/single.php?file=DGM1_SH__Massendownload.geojson&id=4"),
            address=sh_named(2), parse=from_geojson_links),
        vertical_step_m=0.01, probed_bytes=27_088_579,
    ),
    TileSource(
        # No year in the name and a fixed one in the query, so this computes.
        name="sh-lod2", **terms("SH"), product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        _url=lambda e, n: (f"{SH_DOWNLOAD}?file={sh_lod2(e, n)}.xml&id=4"
                           f"&live=2024&km={sh_block(e, n)}"),
        _name=sh_lod2, probed_bytes=100_616, probed_tile=(426, 6004),
        index_url=("https://geodaten.schleswig-holstein.de/gaialight-sh/_apps/"
                   "dladownload/single.php?file=LOD2_SH_Massendownload.geojson&id=4"),
    ),
    TileSource(
        name="hb-dgm1", **terms("HB"), product=TileProduct.DGM1, tile_km=1, fmt="XYZ",
        archives=bremen("DGM", "Gitternetz_DGM1_2017_HB_ASCII_XYZ.zip",
                        "Gitternetz_DGM1_2015_BHV_ASCII_XYZ.zip"),
        vertical_step_m=0.001, probed_bytes=1_088_588_635,
    ),
    TileSource(
        name="hb-dom1", **terms("HB"), product=TileProduct.DOM, tile_km=1, fmt="XYZ",
        archives=bremen("DOM", "Gitternetz_DOM1_2017_HB_ASCII_XYZ.zip",
                        "Gitternetz_DOM1_2015_BHV_ASCII_XYZ.zip"),
        cell_m=1.0, vertical_step_m=0.001, probed_bytes=1_236_054_202,
    ),

    # ---- Saarland and Hamburg publish no tile at all, only whole-region
    # archives. A zip keeps its index at the end, so one tile is a range read:
    # 0.38 % of a 559 MB file, measured on 2026-09-20 (doc 103).
    TileSource(
        name="sl-dgm1", **terms("SL"), product=TileProduct.DGM1, tile_km=1, fmt="GeoTIFF",
        archives=saarland("OD_DGM1_2025_tif_LK",
                          "DGM1_tif_{lk}_EPSG-25832_Entstehung-2025.zip"),
        vertical_step_m=0.01, probed_bytes=559_134_521,
    ),
    TileSource(
        name="sl-dom1", **terms("SL"), product=TileProduct.DOM, tile_km=1, fmt="GeoTIFF",
        archives=saarland("OD_DOM1_2025_tif_LK",
                          "DOM1_tif_{lk}_EPSG-25832_Entstehung-2025.zip"),
        cell_m=1.0, vertical_step_m=0.01, probed_bytes=626_952_523,
    ),
    TileSource(
        name="sl-lod2", **terms("SL"), product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        archives=saarland("OD_Geb%C3%A4udemodelle_LoD2_gml_LK", "{lk}_LOD2BWK_gml.zip"),
        probed_bytes=188_200_265,
    ),
    TileSource(
        # A hundred and twenty-four gigabytes across the six districts, and a
        # garden reads about sixty megabytes of it.
        name="sl-laz", **terms("SL"), product=TileProduct.LAZ, tile_km=1, fmt="LAZ",
        archives=saarland("OD_LIDAR_Punktwolke_2025_laz_LK",
                          "LIDAR_laz_{lk}_EPSG-25832_Entstehung-2025.zip"),
        points_per_m2=4.0, probed_bytes=12_544_319_150,
    ),
    TileSource(
        name="hh-dgm1", **terms("HH"), product=TileProduct.DGM1, tile_km=1, fmt="GeoTIFF",
        archives=("https://daten-hamburg.de/opendata/fernerkundung_hoehenmodelle/"
                  "dgm/dgm1_hh_2022-04-30.zip",),
        vertical_step_m=0.01, probed_bytes=1_364_773_543,
    ),
    TileSource(
        name="hh-bdom", **terms("HH"), product=TileProduct.DOM, tile_km=1, fmt="GeoTIFF",
        archives=("https://daten-hamburg.de/opendata/Digitales_Hoehenmodell_bDOM/"
                  "dom1_hh_2022-11-21.zip",),
        cell_m=1.0, vertical_step_m=0.01, probed_bytes=1_344_475_498,
    ),
    TileSource(
        name="hh-lod2", **terms("HH"), product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        archives=("https://daten-hamburg.de/opendata/3d_stadtmodell_lod2/"
                  "LoD2-DE_HH_2026-04-28.zip",),
        probed_bytes=659_524_658,
    ),

    # ---- Rheinland-Pfalz: the rasters carry a flight year, so they are found
    # through the state's metalink; the roofs and the cloud are arithmetic.
    TileSource(
        name="rp-dgm1", **terms("RP"), product=TileProduct.DGM1, tile_km=1, fmt="GeoTIFF",
        lookup=TileLookup(
            index_url="https://geobasis-rlp.de/data/dgm1/current/meta4/dgm1_tif_07.meta4",
            address=under("https://geobasis-rlp.de/data/dgm1/current/tif/"),
            parse=from_metalink),
        vertical_step_m=0.01, probed_bytes=1_502_657,
        index_url="https://geobasis-rlp.de/data/dgm1/current/meta4/dgm1_tif_07.meta4",
    ),
    TileSource(
        name="rp-dom1", **terms("RP"), product=TileProduct.DOM, tile_km=1, fmt="GeoTIFF",
        lookup=TileLookup(
            index_url="https://geobasis-rlp.de/data/dom1/current/meta4/dom1_tif_07.meta4",
            address=under("https://geobasis-rlp.de/data/dom1/current/tif/"),
            parse=from_metalink),
        cell_m=1.0, vertical_step_m=0.01, probed_bytes=2_087_864,
        index_url="https://geobasis-rlp.de/data/dom1/current/meta4/dom1_tif_07.meta4",
    ),
    TileSource(
        name="rp-lod2", **terms("RP"), product=TileProduct.LOD2, tile_km=2, fmt="CityGML",
        _url=lambda e, n: ("https://geobasis-rlp.de/data/geb3dlo/current/gml/"
                           f"{adv_name('LoD2', e, n, km=2, suffix='RP')}.gml"),
        _name=lambda e, n: adv_name("LoD2", e, n, km=2, suffix="RP"),
        probed_bytes=88_216,
        probed_tile=(292, 5548),
    ),
    TileSource(
        # First and last pulse in one file, which is why a tile is 338 MB.
        name="rp-laz", **terms("RP"), product=TileProduct.LAZ, tile_km=1, fmt="LAZ",
        _url=lambda e, n: ("https://geobasis-rlp.de/data/las/current/las/"
                           f"{adv_name('lpolpg', e, n, suffix='rp')}.laz"),
        _name=lambda e, n: adv_name("lpolpg", e, n, suffix="rp"),
        points_per_m2=4.0, probed_bytes=338_759_225,
        probed_tile=(292, 5548),
    ),

    # ---- Thüringen: ground, surface, cloud and roofs, all of them zipped. ----
    TileSource(
        name="th-dgm1", **terms("TH"), product=TileProduct.DGM1, tile_km=1,
        fmt="GeoTIFF", zipped=True,
        _url=th_url("DGM/dgm_2020-2025"), _name=th_name("dgm"),
        vertical_step_m=0.01, probed_bytes=8_944_113,
        index_url="https://geoportal.geoportal-th.de/dienste/atom_th_hoehendaten_dgm",
        probed_tile=(561, 5609),
    ),
    TileSource(
        name="th-dom1", **terms("TH"), product=TileProduct.DOM, tile_km=1,
        fmt="GeoTIFF", zipped=True,
        _url=th_url("DOM/dom_2020-2025"), _name=th_name("dom"),
        cell_m=1.0, vertical_step_m=0.01, probed_bytes=9_183_189,
        probed_tile=(561, 5609),
    ),
    TileSource(
        name="th-las", **terms("TH"), product=TileProduct.LAZ, tile_km=1,
        fmt="LAZ", zipped=True,
        _url=th_url("LAS/las_2020-2025"), _name=th_name("las"),
        points_per_m2=4.0, probed_bytes=114_375_923,
        probed_tile=(561, 5609),
    ),
    TileSource(
        name="th-lod2", **terms("TH"), product=TileProduct.LOD2, tile_km=2,
        fmt="CityGML", zipped=True,
        _url=lambda e, n: ("https://geoportal.geoportal-th.de/3dgebaeude/LoD2/"
                           f"{adv_name('LoD2', e, n, km=2, suffix='TH')}.zip"),
        _name=lambda e, n: adv_name("LoD2", e, n, km=2, suffix="TH"),
        probed_bytes=2_774_164,
        probed_tile=(598, 5696),
    ),

    # ---- Sachsen: the same four, two kilometres at a time. ----
    TileSource(
        name="sn-dgm1", **terms("SN"), product=TileProduct.DGM1, tile_km=2,
        fmt="GeoTIFF", zipped=True,
        _url=sn_url("dgm1", "tiff", "JCcXyifaNdLDnxZ"), _name=sn_name("dgm1", "tiff"),
        vertical_step_m=0.01, probed_bytes=1_091_178,
        # The state's own download index carries two stale share tokens; the
        # viewer's configuration carries the working set. Re-read them there.
        index_url=("https://geoviewer.sachsen.de/mapviewer/resources/apps/"
                   "produktdownload/app.json"),
        probed_tile=(278, 5590),
    ),
    TileSource(
        name="sn-dom1", **terms("SN"), product=TileProduct.DOM, tile_km=2,
        fmt="GeoTIFF", zipped=True,
        _url=sn_url("dom1", "tiff", "S6wwnFwX7882sZm"), _name=sn_name("dom1", "tiff"),
        cell_m=1.0, vertical_step_m=0.01, probed_bytes=1_150_934,
        probed_tile=(278, 5590),
    ),
    TileSource(
        name="sn-lsc", **terms("SN"), product=TileProduct.LAZ, tile_km=2,
        fmt="LAZ", zipped=True,
        _url=sn_url("lsc", "laz", "EpkzyJHScGb5ndd"), _name=sn_name("lsc", "laz"),
        points_per_m2=4.0, probed_bytes=19_782_635,
        probed_tile=(278, 5590),
    ),
    TileSource(
        name="sn-lod2", **terms("SN"), product=TileProduct.LOD2, tile_km=2,
        fmt="CityGML", zipped=True,
        _url=sn_url("lod2", "citygml", "AyJqXpJAZJXomCb"), _name=sn_name("lod2", "citygml"),
        probed_bytes=853,
        probed_tile=(278, 5590),
    ),

    # ---- What four states with a coverage service never had from it. ----
    TileSource(
        name="bb-lod2", **terms("BB"), product=TileProduct.LOD2, tile_km=1,
        fmt="CityGML", zipped=True,
        _url=bb_url("3d_gebaeude/lod2_gml", "lod2"), _name=bb_name("lod2"),
        probed_bytes=137_502,
        probed_tile=(251, 5888),
    ),
    TileSource(
        # Flown over about 44 % of the state, so a tile missing here is a place
        # nobody has flown rather than a portal having a bad day — which the
        # cloud path already reads as "no window" rather than as a failure.
        name="bb-als", **terms("BB"), product=TileProduct.LAZ, tile_km=1,
        fmt="LAZ", zipped=True,
        _url=bb_url("als/laz", "als"), _name=bb_name("als"),
        # Five per m² is the state's floor for current flights; the tile read
        # on 2026-09-20 held 18.4.
        points_per_m2=5.0, probed_bytes=107_481_210,
        probed_tile=(304, 5862),
    ),
    TileSource(
        # Berlin leaves the zone off the archive and writes CityGML as `.xml`.
        name="be-lod2", **terms("BE"), product=TileProduct.LOD2, tile_km=1,
        fmt="CityGML", zipped=True,
        _url=lambda e, n: f"https://gdi.berlin.de/data/a_lod2/atom/LoD2_{e}_{n}.zip",
        _name=lambda e, n: f"LoD2_{e}_{n}", probed_bytes=537_026,
        index_url="https://gdi.berlin.de/data/a_lod2/atom/0.atom",
        probed_tile=(372, 5808),
    ),
    TileSource(
        name="mv-lod2", **terms("MV"), product=TileProduct.LOD2, tile_km=2,
        fmt="CityGML", zipped=True,
        _url=lambda e, n: ("https://www.geodaten-mv.de/dienste/gebaeude_download?index=0"
                           "&dataset=8397b554-5cb9-4274-8be8-c20490d9a6e8"
                           f"&file=lod2_33_{e}_{n}_2_gml.zip"),
        _name=lambda e, n: f"lod2_33_{e}_{n}_2_gml",
        index_url="https://www.geodaten-mv.de/dienste/gebaeude_atom",
        probed_tile=(206, 5920),
    ),

    # ---- Baden-Württemberg: four one-kilometre tiles inside each archive,
    # and a grid that starts on an odd easting.
    TileSource(
        name="bw-lod2", **terms("BW"), product=TileProduct.LOD2, tile_km=2,
        corner_origin=(1, 0), fmt="CityGML", zipped=True,
        _url=lambda e, n: ("https://opengeodata.lgl-bw.de/data/lod2/"
                           f"{adv_name('LoD2', e, n, km=2, suffix='bw')}.zip"),
        _name=lambda e, n: adv_name("LoD2", e, n, km=2, suffix="bw"),
        probed_bytes=7_519_207,
        index_url="https://opengeodata.lgl-bw.de/assets/config/local/odp-products.json",
        probed_tile=(513, 5404),
    ),
    TileSource(
        # Already normalised to the ground — a canopy height model, which is
        # what `canopies_in` wants and what its 5 m surface service cannot give.
        name="bw-ndom1", **terms("BW"), product=TileProduct.DOM, tile_km=2,
        corner_origin=(1, 0), normalised=True, fmt="GeoTIFF", zipped=True,
        _url=lambda e, n: ("https://opengeodata.lgl-bw.de/data/ndom1/"
                           f"{adv_name('ndom1', e, n, km=2, suffix='bw')}.zip"),
        _name=lambda e, n: adv_name("ndom1", e, n, km=2, suffix="bw"),
        cell_m=1.0, vertical_step_m=0.01, probed_bytes=16_393_060,
        probed_tile=(513, 5404),
    ),
)
