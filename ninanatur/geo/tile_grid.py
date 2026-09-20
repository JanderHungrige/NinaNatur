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
class TileLookup:
    """How to find a tile whose name is not arithmetic (doc 103).

    Rheinland-Pfalz and Schleswig-Holstein write the flight year into a
    raster's name, and the tile next door was flown in a different year. Both
    publish a list of everything they hold, so the name is read from there.

    The index gives a **name**; the address stays ours. `folder` is the
    registry's own prefix, so what the state's list can change is which file is
    asked for, never which host it is asked of.
    """

    #: Where the state publishes its list.
    index_url: str
    #: The address for a name the list gave, at a grid corner. Rheinland-Pfalz
    #: wants the name after a folder; Schleswig-Holstein wants it inside a
    #: query with the tile's ten-kilometre block beside it. Either way the
    #: scheme, the host and the shape are the registry's, and only the name
    #: comes from the state.
    address: Callable[[str, tuple[int, int]], str]
    #: How to read that list: grid corner to file name.
    parse: Callable[[bytes], dict[tuple[int, int], str]]


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
    #: GeoTIFF, CityGML or LAZ — what the tile *is*, which is not always what
    #: arrives: see `zipped`.
    fmt: str
    licence: str
    attribution: str
    #: Which UTM the tile numbers are in: 25832 west of 12°E, 25833 east of it.
    #: Getting it wrong is not an error, it is a tile 400 km away.
    epsg: int
    #: How the address is computed, where it can be. A source found through
    #: an index has neither — see `lookup`, and `url_for` says so if asked.
    _url: Callable[[int, int], str] | None = None
    _name: Callable[[int, int], str] | None = None
    #: Set where the name is not the grid, and then it is how a tile is found.
    lookup: TileLookup | None = None
    #: Set where the state publishes no tile at all, only whole-region
    #: archives — Hamburg one per product, Saarland one per Landkreis. Each
    #: archive's own central directory is the index, read over HTTP ranges, and
    #: one tile costs a fraction of a per cent of the file (doc 103).
    archives: tuple[str, ...] = ()
    #: Where a coarse grid starts, in kilometres. Almost every two-kilometre
    #: scheme lands on even numbers, and Baden-Württemberg's lands on an **odd**
    #: easting — `513_5404` is a tile and `514_5404` is a 404. Floor to the
    #: wrong parity and every request is for a tile that does not exist.
    corner_origin: tuple[int, int] = (0, 0)
    #: Whether the product already holds metres **above the ground** rather
    #: than above the sea. Almost every surface model is absolute and has its
    #: terrain taken off (doc 108); Baden-Württemberg's `nDOM1` is a canopy
    #: height model and is not. Subtracting the ground from it a second time
    #: would put every tree three hundred metres underground.
    normalised: bool = False
    #: Whether the tile arrives inside a zip. Six states wrap theirs, with the
    #: licence, a world file or the same heights again as text beside it — and
    #: Baden-Württemberg puts four tiles of its own grid in one archive. The
    #: grid is unchanged either way, so this is a wrapper, not a tier (doc 103).
    zipped: bool = False
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
    #: **Which** tile that was, as its south-west corner in kilometres. Without
    #: it `probed_bytes` is a number with nothing to compare against, and a
    #: health check has no square kilometre it knows should exist. A source
    #: found through a list or an archive needs none: the list is the answer.
    probed_tile: tuple[int, int] | None = None

    @property
    def computed(self) -> bool:
        """Whether this tile's address is arithmetic rather than a lookup."""
        return self._url is not None

    def url_for(self, east_km: int, north_km: int) -> str:
        """The address of the tile whose south-west corner is here."""
        if self._url is None:
            raise ValueError(f"{self.name} is found through its index, not computed")
        return self._url(east_km, north_km)

    def tile_name(self, east_km: int, north_km: int) -> str:
        """What that tile is called, without the folders around it."""
        if self._name is None:
            raise ValueError(f"{self.name} is named by its index, not computed")
        return self._name(east_km, north_km)

    def corner_of(self, easting_m: float, northing_m: float) -> tuple[int, int]:
        """The tile that covers this point, as its south-west corner in km."""
        step = self.tile_km
        origin_e, origin_n = self.corner_origin
        return (int(math.floor((easting_m / 1000 - origin_e) / step) * step + origin_e),
                int(math.floor((northing_m / 1000 - origin_n) / step) * step + origin_n))


def under(folder: str) -> Callable[[str, tuple[int, int]], str]:
    """The simple address: a name inside a folder of ours."""
    return lambda name, _corner: folder + name


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


def corner_in(name: str, fallback: tuple[int, int]) -> tuple[int, int]:
    """The grid corner a member's own name carries, or the archive's own.

    Only Baden-Württemberg needs this — four one-kilometre tiles in one
    two-kilometre archive, each named for where it is. Everywhere else the one
    member covers the tile it arrived as, and the fallback is the answer.
    """
    # The member's own name, never the folder around it: Baden-Württemberg
    # names that folder after the *archive*, so reading the whole path puts all
    # four tiles on the archive's corner, stacked on top of one another.
    numbers = [int(part) for part in re.findall(r"\d+", name.rsplit("/", 1)[-1])]
    for first, second in zip(numbers, numbers[1:], strict=False):
        # An easting is three digits of kilometres, sometimes with the zone
        # written onto the front of it (Sachsen, Brandenburg); a German
        # northing is four, between about 5 200 and 6 100.
        east = next((first - zone for zone in (0, 32_000, 33_000)
                     if 200 <= first - zone <= 999), None)
        if east is not None and 5_000 <= second <= 6_200:
            return east, second
    return fallback


__all__ = [
    "FREE_LICENCES",
    "TileLookup",
    "TileProduct",
    "TileSource",
    "corner_in",
    "tile_of",
    "under",
]
