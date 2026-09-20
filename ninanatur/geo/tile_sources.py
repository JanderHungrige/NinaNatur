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
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

#: Licences under which a tile may be used here. dl-de/zero-2-0 asks for
#: nothing and is credited anyway; the others require the named credit. A
#: licence that is not in this set keeps its state out of the registry, however
#: a catalogue describes it (doc 68's Saarland).
FREE_LICENCES: frozenset[str] = frozenset({
    "CC-BY-4.0",
    "dl-de/by-2-0",
    "dl-de/zero-2-0",
    "Copernicus",
})


class TileProduct(StrEnum):
    """What a tile holds."""

    #: The ground, as a raster.
    DGM1 = "dgm1"
    #: The ground and everything standing on it, as a raster.
    DOM1 = "dom1"
    #: Buildings with measured height and a standardised roof, as CityGML.
    LOD2 = "lod2"
    #: The laser points themselves, classified.
    LAZ = "laz"


@dataclass(frozen=True)
class TileSource:
    """One state's product, as a grid of files.

    `url_for` takes UTM kilometres — the easting and northing of the tile's
    south-west corner — because that is what every one of these schemes is:
    the grid written down. `tile_of` reads the same numbers back out, so what
    the registry computes it can also recognise.
    """

    #: `<state>-<product>`, lower case: the name the probe script prints.
    name: str
    #: The two-letter state key, as the rest of the codebase writes it.
    state: str
    product: TileProduct
    #: How wide one tile is, in kilometres.
    tile_km: int
    #: GeoTIFF, CityGML, LAZ, zip — what arrives, for whoever opens it.
    fmt: str
    licence: str
    attribution: str
    #: Which UTM the tile numbers are in: 25832 west of 12°E, 25833 east of it.
    #: Getting it wrong is not an error, it is a tile 400 km away.
    epsg: int
    _url: Callable[[int, int], str]
    _name: Callable[[int, int], str]
    #: A raster's height step, where it has one.
    vertical_step_m: float | None = None
    #: A cloud's density, where it is one.
    points_per_m2: float | None = None
    #: Where the state says which tiles exist, if it says so anywhere.
    index_url: str | None = None
    #: What the probe found on the date in this module's docstring.
    probed_bytes: int | None = None

    def url_for(self, east_km: int, north_km: int) -> str:
        """The address of the tile whose south-west corner is here."""
        return self._url(east_km, north_km)

    def tile_name(self, east_km: int, north_km: int) -> str:
        """What that tile is called, without the folders around it."""
        return self._name(east_km, north_km)

    def corner_of(self, easting_m: float, northing_m: float) -> tuple[int, int]:
        """The tile that covers this point, as its south-west corner in km."""
        step = self.tile_km
        return (int(math.floor(easting_m / 1000 / step) * step),
                int(math.floor(northing_m / 1000 / step) * step))


def _bayern(product: str, extension: str) -> Callable[[int, int], str]:
    return lambda e, n: f"https://download1.bayernwolke.de/a/{product}/{e}_{n}.{extension}"


#: Bayern: the tile is simply the two kilometre numbers.
def _bayern_name(east_km: int, north_km: int) -> str:
    return f"{east_km}_{north_km}"


#: NRW: the zone in front, the sheet number and the state behind.
def _nrw_name(east_km: int, north_km: int, prefix: str, suffix: str) -> str:
    return f"{prefix}_32_{east_km}_{north_km}_1_{suffix}"


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
        name="by-lod2", state="BY", epsg=25832, product=TileProduct.LOD2, tile_km=1, fmt="CityGML",
        licence="CC-BY-4.0",
        attribution="Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de",
        _url=_bayern("lod2/citygml", "gml"), _name=_bayern_name,
        probed_bytes=161_627_079,
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
#: a tile's name says "by". One place knows both.
STATE_KEYS: dict[str, str] = {
    "baden-württemberg": "BW", "bayern": "BY", "berlin": "BE", "brandenburg": "BB",
    "bremen": "HB", "hamburg": "HH", "hessen": "HE", "mecklenburg-vorpommern": "MV",
    "niedersachsen": "NI", "nordrhein-westfalen": "NW", "rheinland-pfalz": "RP",
    "saarland": "SL", "sachsen": "SN", "sachsen-anhalt": "ST",
    "schleswig-holstein": "SH", "thüringen": "TH",
}


def key_of(state: str) -> str:
    """The two-letter key for a state, however it was named."""
    return STATE_KEYS.get(state.strip().lower(), state.strip().upper())


def sources_for(state: str) -> tuple[TileSource, ...]:
    """Every tile product this state publishes openly, by key or by name.
    Empty is an answer."""
    key = key_of(state)
    return tuple(source for source in TILE_SOURCES if source.state == key)


def ground_tiles_for(state: str) -> TileSource | None:
    """The state's ground, as tiles — the tier under the coverage services."""
    for source in sources_for(state):
        if source.product is TileProduct.DGM1:
            return source
    return None


def tile_of(source: TileSource, east_km: int, north_km: int) -> tuple[int, int]:
    """The two kilometre numbers back out of a tile's name — the round trip the
    test insists on, and what reads a state's index into this registry's terms."""
    numbers = [int(part) for part in re.findall(r"\d+", source.tile_name(east_km, north_km))]
    # The pair that is the grid: an easting is three digits of kilometres, a
    # northing four. Zone, sheet size and state suffix are the other numbers.
    for first, second in zip(numbers, numbers[1:], strict=False):
        if (first, second) == (east_km, north_km):
            return first, second
    raise ValueError(f"{source.name}: {source.tile_name(east_km, north_km)} does not hold its grid")


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
    "sources_for",
    "tile_of",
]
