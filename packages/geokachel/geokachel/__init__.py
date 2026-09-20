"""Official German open elevation data, from all sixteen Bundesländer.

Germany publishes superb elevation data and publishes it sixteen different
ways. Every state runs its own surveying office, and they disagree about
everything except the ground itself: where the UTM zone goes in a filename,
whether a tile is one kilometre or two, whether a grid starts on an even
easting or an odd one, whether you get a GeoTIFF or a million lines of text,
whether there is a tile to address at all or only a twelve-gigabyte archive.

This is one interface over all of it, and a record of which requests were
actually answered and when.

    from geokachel import ground_tiles_for, net

    source = ground_tiles_for("BY")
    print(source.attribution)
    # Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de
    print(source.url_for(690, 5334))
    # https://download1.bayernwolke.de/a/dgm/dgm1/690_5334.tif

Three rules it keeps, because they are what make the data safe to use:

**An entry is a request that was answered**, dated — never a portal page that
says a thing exists. Each carries the tile it was verified at and the bytes
that came back, so `geokachel check` can ask again.

**A credit is a licence obligation, not a caption.** Every source carries the
exact string its licence requires, as a required field. A height shown without
it is a height used outside its licence. See NOTICE.

**A gap is a gap.** No state borrows its neighbour's ground, and nothing
unsurveyed is guessed at: it is NaN, and it says so.

What this does *not* do is decide what your coordinate frame is. It hands back
rasters in the source's own UTM, north-up, with NaN for unknown — putting those
on your own axes is yours, because the right answer differs for a shadow model,
a flood model and a map.
"""
from __future__ import annotations

from geokachel.addressing import INSIDE, Grab, addressed, decode, rasters, tiles_across
from geokachel.health import Check, Verdict, check_coverage, check_tile_source
from geokachel.orthophotos import ORTHOPHOTOS, Orthophoto
from geokachel.remote_zip import member_of, names_in
from geokachel.surface_sources import SURFACE_SOURCES, SurfaceSource
from geokachel.terrain_sources import TERRAIN_SOURCES, TerrainSource
from geokachel.tiff import MAX_PIXELS, WHOLE_TILE_PIXELS, Raster, TiffError, read_raster
from geokachel.tile_cache import TileCache, cache_at
from geokachel.tile_grid import (
    FREE_LICENCES,
    TileLookup,
    TileProduct,
    TileSource,
    corner_in,
    tile_of,
    under,
)
from geokachel.tile_index import ListingError, from_geojson_links, from_metalink
from geokachel.tile_sources import (
    COPERNICUS_ATTRIBUTION,
    COPERNICUS_LICENCE,
    STATES,
    TILE_SOURCES,
    glo30_url,
    ground_tiles_for,
    key_of,
    laser_tiles_for,
    lod2_tiles_for,
    name_of,
    sources_for,
)
from geokachel.tile_zip import ArchiveError, extract, named, unpack
from geokachel.utm import central_meridian, to_latlon, to_utm, zone_for
from geokachel.xyz import read_grid

__version__ = "0.1.0"

#: The day every source in this registry last answered as it should
#: (`geokachel check`). An entry older than a season deserves a re-probe.
VERIFIED_ON = "2026-09-20"

__all__ = [
    "COPERNICUS_ATTRIBUTION",
    "COPERNICUS_LICENCE",
    "FREE_LICENCES",
    "INSIDE",
    "MAX_PIXELS",
    "ORTHOPHOTOS",
    "Orthophoto",
    "STATES",
    "SURFACE_SOURCES",
    "TERRAIN_SOURCES",
    "TILE_SOURCES",
    "VERIFIED_ON",
    "WHOLE_TILE_PIXELS",
    "ArchiveError",
    "Check",
    "Grab",
    "ListingError",
    "Raster",
    "SurfaceSource",
    "TerrainSource",
    "TiffError",
    "TileCache",
    "TileLookup",
    "TileProduct",
    "TileSource",
    "Verdict",
    "__version__",
    "addressed",
    "cache_at",
    "central_meridian",
    "check_coverage",
    "check_tile_source",
    "corner_in",
    "decode",
    "extract",
    "from_geojson_links",
    "from_metalink",
    "glo30_url",
    "ground_tiles_for",
    "key_of",
    "laser_tiles_for",
    "lod2_tiles_for",
    "member_of",
    "name_of",
    "named",
    "names_in",
    "rasters",
    "read_grid",
    "read_raster",
    "sources_for",
    "tile_of",
    "tiles_across",
    "to_latlon",
    "to_utm",
    "under",
    "unpack",
    "zone_for",
]
