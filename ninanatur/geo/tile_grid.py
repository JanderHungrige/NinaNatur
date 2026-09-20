"""What a tile source *is* — Wave 25, doc 102.

The registry itself lives in `tile_sources.py`; this is the shape its entries
have, kept apart because the entries are a list that grows with every state
and this is a definition that does not.

The idea in one line: a state publishes its country as a grid of files, and
you take the one your garden is in. Every scheme in this family is that grid
written down, so a tile's address is arithmetic on two integers and never a
lookup — which is also what keeps a garden's data away from a path.
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
    #: The ground and everything standing on it, as a raster. How fine it is
    #: varies — Bayern's is 20 cm — so the resolution is `cell_m`, not the name.
    DOM = "dom"
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
    #: A raster's own cell, in metres: 1 m for a DGM1, 0.2 for Bayern's DOM20.
    cell_m: float | None = None
    #: A raster's height step, where it has one.
    vertical_step_m: float | None = None
    #: A cloud's density, where it is one.
    points_per_m2: float | None = None
    #: Where the state says which tiles exist, if it says so anywhere.
    index_url: str | None = None
    #: What the probe found on the date in the registry's docstring.
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


def tile_of(source: TileSource, east_km: int, north_km: int) -> tuple[int, int]:
    """The two kilometre numbers back out of a tile's name — the round trip the
    test insists on, and what reads a state's index into this registry's terms."""
    numbers = [int(part) for part in re.findall(r"\d+", source.tile_name(east_km, north_km))]
    # The pair that is the grid: an easting is three digits of kilometres, a
    # northing four. Zone, sheet size and state suffix are the other numbers —
    # and Bayern writes the zone *onto the front of* the easting, so a number is
    # the easting if it is one, or if it is one with a zone in front of it.
    zones = (0, 32_000, 33_000)
    for first, second in zip(numbers, numbers[1:], strict=False):
        if second == north_km and any(first - zone == east_km for zone in zones):
            return east_km, north_km
    raise ValueError(f"{source.name}: {source.tile_name(east_km, north_km)} does not hold its grid")


__all__ = ["FREE_LICENCES", "TileProduct", "TileSource", "tile_of"]
