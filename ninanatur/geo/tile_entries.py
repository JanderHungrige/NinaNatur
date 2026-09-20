"""Every tile source, one per state and product — Wave 25, doc 102.

The entries themselves, kept apart from `tile_sources.py` because this is a
list that grows with every state probed and that is an interface that does not.
Nothing here is imported directly: `tile_sources` is the way in.

**An entry is a request of ours that was answered**, dated, by
`scripts/probe_tile_sources.py`. A state with nothing gets no entry, and a
licence that forbids this use is a state without an entry.
"""
from __future__ import annotations

from collections.abc import Callable

from ninanatur.geo.tile_grid import TileProduct, TileSource


def _bayern(product: str, extension: str) -> Callable[[int, int], str]:
    return lambda e, n: f"https://download1.bayernwolke.de/a/{product}/{e}_{n}.{extension}"


#: Bayern: the tile is simply the two kilometre numbers.
def _bayern_name(east_km: int, north_km: int) -> str:
    return f"{east_km}_{north_km}"


#: What most states write, and what AdV's own tile scheme looks like: a product
#: prefix, the UTM zone as its own field, the two kilometre numbers of the
#: south-west corner, how many kilometres across, and the state. Nordrhein-
#: Westfalen, Rheinland-Pfalz, Niedersachsen and Thüringen all use it; the
#: disagreements are capitalisation and the sheet size, not the shape.
def _adv_name(prefix: str, east_km: int, north_km: int, *, zone: int = 32,
              km: int = 1, suffix: str) -> str:
    return f"{prefix}_{zone}_{east_km}_{north_km}_{km}_{suffix}"


def _nrw_name(east_km: int, north_km: int, prefix: str, suffix: str) -> str:
    return _adv_name(prefix, east_km, north_km, suffix=suffix)


#: Thüringen: the AdV name with the survey period on the end, and the whole
#: thing zipped. Every one of its 16,945 tiles matches this.
def _th(product: str, folder: str, extension: str = "zip") -> Callable[[int, int], str]:
    return lambda e, n: (f"https://geoportal.geoportal-th.de/hoehendaten/{folder}/"
                         f"{_adv_name(product, e, n, suffix='th_2020-2025')}.{extension}")


#: Sachsen glues the zone to the easting, works in two-kilometre tiles, and
#: hands every product out of a share whose token is fixed per product.
def _sn_name(product: str, kind: str) -> Callable[[int, int], str]:
    return lambda e, n: f"{product}_33{e}_{n}_2_sn_{kind}"


def _sn(product: str, kind: str, token: str) -> Callable[[int, int], str]:
    return lambda e, n: ("https://geocloud.landesvermessung.sachsen.de/public.php/dav/files/"
                         f"{token}/{_sn_name(product, kind)(e, n)}.zip")


#: Brandenburg: the zone glued to the easting and a hyphen before the northing.
def _bb_name(product: str) -> Callable[[int, int], str]:
    return lambda e, n: f"{product}_33{e}-{n}"


#: Bayern writes the zone in front of the easting and the product behind:
#: `32690_5334_20_DOM.tif` is UTM32, 690 km east, 5 334 km north, 20 cm, surface.
def _bayern_dom_name(east_km: int, north_km: int) -> str:
    return f"32{east_km}_{north_km}_20_DOM"


TILE_SOURCES: tuple[TileSource, ...] = (
    TileSource(
        name="by-dgm1", state="BY", epsg=25832, product=TileProduct.DGM1, tile_km=1, fmt="GeoTIFF",
        licence="CC-BY-4.0",
        attribution="Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de",
        _url=_bayern("dgm/dgm1", "tif"), _name=_bayern_name,
        vertical_step_m=0.01, probed_bytes=2_558_672,
        # Not on the download host: that path answers 404 (doc 102).
        index_url="https://geodaten.bayern.de/odd/a/dgm/dgm1/meta/metalink/",
    ),
    TileSource(
        name="by-dom20", state="BY", epsg=25832, product=TileProduct.DOM, tile_km=1,
        fmt="GeoTIFF", licence="CC-BY-4.0",
        attribution="Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de",
        _url=lambda e, n: ("https://download1.bayernwolke.de/a/dom20/DOM/"
                           f"{_bayern_dom_name(e, n)}.tif"),
        _name=_bayern_dom_name,
        cell_m=0.2, vertical_step_m=0.01, probed_bytes=48_441_449,
        index_url="https://geodaten.bayern.de/odd/a/dom20/meta/DOM/metalink/",
    ),
    TileSource(
        name="by-lod2", state="BY", epsg=25832, product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        licence="CC-BY-4.0",
        attribution="Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de",
        _url=_bayern("lod2/citygml", "gml"), _name=_bayern_name,
        probed_bytes=161_627_079,
    ),
    TileSource(
        name="by-laser", state="BY", epsg=25832, product=TileProduct.LAZ, tile_km=1, fmt="LAZ",
        licence="CC-BY-4.0",
        attribution="Bayerische Vermessungsverwaltung – www.geodaten.bayern.de",
        # Not on the download host: every bayernwolke path for the laser is a
        # 404, and this address comes out of the product's own metalink.
        _url=lambda e, n: f"https://geodaten.bayern.de/odd_data/laser/{e}_{n}.laz",
        _name=_bayern_name,
        # The state guarantees four per m² since 2012; Munich measures twenty.
        points_per_m2=4.0, probed_bytes=112_064_676,
        index_url="https://geodaten.bayern.de/odd/a/laser/meta/metalink/",
    ),
    TileSource(
        name="nw-lod2", state="NW", epsg=25832, product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        licence="dl-de/zero-2-0",
        attribution="Land NRW (2026), Datenlizenz Deutschland – Zero – Version 2.0",
        _url=lambda e, n: ("https://www.opengeodata.nrw.de/produkte/geobasis/3dg/lod2_gml/"
                           f"lod2_gml/{_nrw_name(e, n, 'LoD2', 'NW')}.gml"),
        _name=lambda e, n: _nrw_name(e, n, "LoD2", "NW"),
        probed_bytes=20_684_673,
    ),
    TileSource(
        name="nw-laz", state="NW", epsg=25832, product=TileProduct.LAZ, tile_km=1, fmt="LAZ",
        licence="dl-de/zero-2-0",
        attribution="Land NRW (2026), Datenlizenz Deutschland – Zero – Version 2.0",
        _url=lambda e, n: ("https://www.opengeodata.nrw.de/produkte/geobasis/hm/3dm_l_las/"
                           f"3dm_l_las/{_nrw_name(e, n, '3dm', 'nw')}.laz"),
        _name=lambda e, n: _nrw_name(e, n, "3dm", "nw"),
        points_per_m2=4.0, probed_bytes=34_967_590,
        index_url=("https://www.opengeodata.nrw.de/produkte/geobasis/hm/3dm_l_las/"
                   "3dm_l_las/index.json"),
    ),
    # Rheinland-Pfalz is verified and waiting, not missing: its LoD2 and its
    # point cloud both answered on 2026-09-20 (doc 102). They join when its
    # ground does — a state that publishes buildings and no ground has no way
    # to name the survey that measured them (`test_credits`), and a garden with
    # roofs on flat ground is worse than one that waits.
    TileSource(
        name="ni-lod2", state="NI", epsg=25832, product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        licence="CC-BY-4.0",
        attribution="© GeoBasis-DE/LGLN (2026)",
        _url=lambda e, n: ("https://lod2.opengeodata.lgln.niedersachsen.de/"
                           f"{_adv_name('LoD2', e, n, suffix='ni')}.gml"),
        _name=lambda e, n: _adv_name("LoD2", e, n, suffix="ni"),
        probed_bytes=43_632,
    ),

    # ---- Thüringen: ground, surface and roofs, all of them zipped. ----
    TileSource(
        name="th-dgm1", state="TH", epsg=25832, product=TileProduct.DGM1, tile_km=1,
        fmt="GeoTIFF", zipped=True, licence="dl-de/by-2-0",
        attribution="© GDI-Th (2026), Datenlizenz Deutschland – Namensnennung – Version 2.0",
        _url=_th("dgm1", "DGM/dgm_2020-2025"),
        _name=lambda e, n: _adv_name("dgm1", e, n, suffix="th_2020-2025"),
        vertical_step_m=0.01, probed_bytes=8_944_113,
        index_url="https://geoportal.geoportal-th.de/dienste/atom_th_hoehendaten_dgm",
    ),
    TileSource(
        name="th-dom1", state="TH", epsg=25832, product=TileProduct.DOM, tile_km=1,
        fmt="GeoTIFF", zipped=True, licence="dl-de/by-2-0",
        attribution="© GDI-Th (2026), Datenlizenz Deutschland – Namensnennung – Version 2.0",
        _url=_th("dom1", "DOM/dom_2020-2025"),
        _name=lambda e, n: _adv_name("dom1", e, n, suffix="th_2020-2025"),
        cell_m=1.0, vertical_step_m=0.01, probed_bytes=9_183_189,
    ),
    TileSource(
        name="th-lod2", state="TH", epsg=25832, product=TileProduct.LOD2, tile_km=2,
        fmt="CityGML", zipped=True, licence="dl-de/by-2-0",
        attribution="© GDI-Th (2026), Datenlizenz Deutschland – Namensnennung – Version 2.0",
        _url=lambda e, n: ("https://geoportal.geoportal-th.de/3dgebaeude/LoD2/"
                           f"{_adv_name('LoD2', e, n, km=2, suffix='TH')}.zip"),
        _name=lambda e, n: _adv_name("LoD2", e, n, km=2, suffix="TH"),
        probed_bytes=2_774_164,
    ),

    # ---- Sachsen: the same four products, two kilometres at a time. ----
    TileSource(
        name="sn-dgm1", state="SN", epsg=25833, product=TileProduct.DGM1, tile_km=2,
        fmt="GeoTIFF", zipped=True, licence="dl-de/by-2-0",
        attribution="Quelle: GeoSN, dl-de/by-2-0",
        _url=_sn("dgm1", "tiff", "JCcXyifaNdLDnxZ"), _name=_sn_name("dgm1", "tiff"),
        vertical_step_m=0.01, probed_bytes=1_091_178,
        # The state's own download index carries two stale tokens; the viewer's
        # configuration carries the working ones. This is where to re-read them.
        index_url=("https://geoviewer.sachsen.de/mapviewer/resources/apps/"
                   "produktdownload/app.json"),
    ),
    TileSource(
        name="sn-dom1", state="SN", epsg=25833, product=TileProduct.DOM, tile_km=2,
        fmt="GeoTIFF", zipped=True, licence="dl-de/by-2-0",
        attribution="Quelle: GeoSN, dl-de/by-2-0",
        _url=_sn("dom1", "tiff", "S6wwnFwX7882sZm"), _name=_sn_name("dom1", "tiff"),
        cell_m=1.0, vertical_step_m=0.01, probed_bytes=1_150_934,
    ),
    TileSource(
        name="sn-lod2", state="SN", epsg=25833, product=TileProduct.LOD2, tile_km=2,
        fmt="CityGML", zipped=True, licence="dl-de/by-2-0",
        attribution="Quelle: GeoSN, dl-de/by-2-0",
        _url=_sn("lod2", "citygml", "AyJqXpJAZJXomCb"), _name=_sn_name("lod2", "citygml"),
        probed_bytes=853,
    ),

    # ---- Roofs for four states that already had their ground from a service. ----
    TileSource(
        name="bb-lod2", state="BB", epsg=25833, product=TileProduct.LOD2, tile_km=1,
        fmt="CityGML", zipped=True, licence="dl-de/by-2-0",
        attribution="© GeoBasis-DE/LGB, dl-de/by-2-0",
        _url=lambda e, n: ("https://data.geobasis-bb.de/geobasis/daten/3d_gebaeude/"
                           f"lod2_gml/{_bb_name('lod2')(e, n)}.zip"),
        _name=_bb_name("lod2"), probed_bytes=137_502,
    ),
    TileSource(
        name="be-lod2", state="BE", epsg=25833, product=TileProduct.LOD2, tile_km=1,
        fmt="CityGML", zipped=True, licence="dl-de/zero-2-0",
        attribution=("Geoportal Berlin / 3D-Gebäudemodelle LoD2, "
                     "Datenlizenz Deutschland – Zero – Version 2.0"),
        # Berlin leaves the zone off the archive and writes CityGML as `.xml`.
        _url=lambda e, n: f"https://gdi.berlin.de/data/a_lod2/atom/LoD2_{e}_{n}.zip",
        _name=lambda e, n: f"LoD2_{e}_{n}", probed_bytes=537_026,
        index_url="https://gdi.berlin.de/data/a_lod2/atom/0.atom",
    ),
    TileSource(
        name="mv-lod2", state="MV", epsg=25833, product=TileProduct.LOD2, tile_km=2,
        fmt="CityGML", zipped=True, licence="CC-BY-4.0",
        attribution="© GeoBasis-DE/M-V (2026)",
        _url=lambda e, n: ("https://www.geodaten-mv.de/dienste/gebaeude_download?index=0"
                           "&dataset=8397b554-5cb9-4274-8be8-c20490d9a6e8"
                           f"&file=lod2_33_{e}_{n}_2_gml.zip"),
        _name=lambda e, n: f"lod2_33_{e}_{n}_2_gml",
        index_url="https://www.geodaten-mv.de/dienste/gebaeude_atom",
    ),

    # ---- Baden-Württemberg: four one-kilometre tiles inside each archive,
    # and a grid that starts on an odd easting.
    TileSource(
        name="bw-lod2", state="BW", epsg=25832, product=TileProduct.LOD2, tile_km=2,
        corner_origin=(1, 0), fmt="CityGML", zipped=True, licence="dl-de/by-2-0",
        attribution="Datenquelle: LGL, www.lgl-bw.de, dl-de/by-2-0",
        _url=lambda e, n: ("https://opengeodata.lgl-bw.de/data/lod2/"
                           f"{_adv_name('LoD2', e, n, km=2, suffix='bw')}.zip"),
        _name=lambda e, n: _adv_name("LoD2", e, n, km=2, suffix="bw"),
        probed_bytes=7_519_207,
        index_url="https://opengeodata.lgl-bw.de/assets/config/local/odp-products.json",
    ),
    TileSource(
        # Already normalised to the ground — a canopy height model, which is
        # what `canopies_in` wants and what its 5 m surface service cannot give.
        name="bw-ndom1", state="BW", epsg=25832, product=TileProduct.DOM, tile_km=2,
        corner_origin=(1, 0), normalised=True, fmt="GeoTIFF", zipped=True,
        licence="dl-de/by-2-0",
        attribution="Datenquelle: LGL, www.lgl-bw.de, dl-de/by-2-0",
        _url=lambda e, n: ("https://opengeodata.lgl-bw.de/data/ndom1/"
                           f"{_adv_name('ndom1', e, n, km=2, suffix='bw')}.zip"),
        _name=lambda e, n: _adv_name("ndom1", e, n, km=2, suffix="bw"),
        cell_m=1.0, vertical_step_m=0.01, probed_bytes=16_393_060,
    ),
)
