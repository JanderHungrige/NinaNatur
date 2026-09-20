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

from geokachel.tile_entries import TILE_SOURCES
from geokachel.tile_grid import FREE_LICENCES, TileProduct, TileSource, tile_of

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
