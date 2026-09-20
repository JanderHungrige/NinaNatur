"""Elevation and building tiles that may actually be used — Wave 25, doc 102.

The fourth registry after orthophotos (doc 8), terrain (doc 68) and surface
models (doc 80), and the same rule: an entry is a request of ours that was
answered, a state with nothing gets no entry, and a licence that forbids this
use is a state without an entry.

What differs is the shape. Those three hold *services* — ask for a window, get
the window. This one holds **files**: a state publishes its country as a grid
and you take the tile your garden is in. It is the tier Wave 17 named and never
built, and the only route into the states that publish the data and run no
service.

Probed on **2026-09-20**, each with a real request
(`python -m scripts.probe_tile_sources`). Two answers from that day shape the
rest of the wave:

- The federal **LoD2-DE** exists and is *"nur einem eingeschränkten Kreis
  Nutzungsberechtigter"* — federal authorities. It does not replace the state
  adapters, and it is not here.
- **Niedersachsen** publishes no laser data at all; its LoD2, bDOM20, DGM1 and
  DOM1 are open. It is a raster state for the trees.

Six states hand their tiles out through an index or an Atom feed — Thüringen,
Schleswig-Holstein, Hamburg, Bremen, Rheinland-Pfalz, Sachsen. Each joins this
registry when its index has been fetched and answered, which is feature 1.
"""
from __future__ import annotations

import math
from collections.abc import Callable

from ninanatur.geo.tile_grid import FREE_LICENCES, TileProduct, TileSource, tile_of


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
)

#: The whole-country fallback: 30 m, one file per degree cell, for a horizon
#: ring where no state serves anything (doc 102). Not a `TileSource` — its grid
#: is degrees, not kilometres, and a 30 m answer is a different kind of answer.
COPERNICUS_GLO30 = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
    "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif"
)
COPERNICUS_LICENCE = "Copernicus"
COPERNICUS_ATTRIBUTION = (
    "Copernicus DEM GLO-30, produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 "
    "and © Airbus Defence and Space GmbH 2014–2018, provided under COPERNICUS by the "
    "European Union and ESA"
)


def glo30_url(latitude: float, longitude: float) -> str:
    """The degree cell this place is in, as a Copernicus GLO-30 tile."""
    lat, lon = math.floor(latitude), math.floor(longitude)
    return COPERNICUS_GLO30.format(
        ns="N" if lat >= 0 else "S", lat=abs(lat),
        ew="E" if lon >= 0 else "W", lon=abs(lon),
    )


#: The rest of the codebase says "Bayern", and OSM says it too (`state_at`);
#: a tile's name says "by"; the terrain services are registered under the full
#: name. One place knows both, and every lookup goes through it — a registry
#: that answers to one spelling and not the other is a source that silently
#: is not there.
STATES: dict[str, str] = {
    "BW": "Baden-Württemberg", "BY": "Bayern", "BE": "Berlin", "BB": "Brandenburg",
    "HB": "Bremen", "HH": "Hamburg", "HE": "Hessen", "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen", "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz",
    "SL": "Saarland", "SN": "Sachsen", "ST": "Sachsen-Anhalt",
    "SH": "Schleswig-Holstein", "TH": "Thüringen",
}
STATE_KEYS: dict[str, str] = {name.lower(): key for key, name in STATES.items()}


def key_of(state: str) -> str:
    """The two-letter key for a state, however it was named."""
    return STATE_KEYS.get(state.strip().lower(), state.strip().upper())


def name_of(state: str) -> str:
    """The name the state calls itself, from a key or from itself."""
    return STATES.get(state.strip().upper(), state.strip())


def sources_for(state: str) -> tuple[TileSource, ...]:
    """Every tile product this state publishes openly, by key or by name.
    Empty is an answer."""
    key = key_of(state)
    return tuple(source for source in TILE_SOURCES if source.state == key)


def _product_for(state: str, product: TileProduct) -> TileSource | None:
    for source in sources_for(state):
        if source.product is product:
            return source
    return None


def ground_tiles_for(state: str) -> TileSource | None:
    """The state's ground, as tiles — the tier under the coverage services."""
    return _product_for(state, TileProduct.DGM1)


def laser_tiles_for(state: str) -> TileSource | None:
    """The state's point cloud: the only product that can say where a canopy
    starts, and the only one that sees under a tree (doc 107)."""
    return _product_for(state, TileProduct.LAZ)


def lod2_tiles_for(state: str) -> TileSource | None:
    """The state's 3D building model: measured height and a surveyed roof
    shape, which no surface raster can give (doc 105)."""
    return _product_for(state, TileProduct.LOD2)


__all__ = [
    "COPERNICUS_ATTRIBUTION",
    "COPERNICUS_LICENCE",
    "FREE_LICENCES",
    "TILE_SOURCES",
    "TileProduct",
    "TileSource",
    "glo30_url",
    "ground_tiles_for",
    "key_of",
    "laser_tiles_for",
    "name_of",
    "lod2_tiles_for",
    "sources_for",
    "tile_of",
]
