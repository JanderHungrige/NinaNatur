"""Fetching what the surveys know about a garden's buildings, once.

The sibling of `terrain_sync`, and it runs in the same place and for the same
reason: on the explicit recompute, which is a button somebody pressed knowing it
would take a moment. A LoD2 tile is tens of megabytes and a surface window is
one request; neither belongs in a page load.

Everything here is allowed to fail. A garden whose buildings could not be
measured keeps the heights it had, which is what every garden had before this
existed — and that is a supported state rather than an error.
"""
from __future__ import annotations

import logging
import sqlite3

from ninanatur.garden.measured import apply, measure
from ninanatur.garden.models import Garden
from ninanatur.geo.lod2 import Lod2Building, buildings_from, in_garden_frame, tile_name
from ninanatur.geo.osm import state_at
from ninanatur.geo.projection import LatLon
from ninanatur.geo.surface import SurfaceWindow, fetch_surface
from ninanatur.geo.surface_sources import by_state, measures_buildings
from ninanatur.geo.terrain_store import cache_key, load_window
from ninanatur.geo.utm import to_utm
from ninanatur.ingest.http import get_bytes

log = logging.getLogger(__name__)

#: Where Nordrhein-Westfalen publishes its 3D building model.
#:
#: The only state whose LoD2 is addressable by coordinate — the tile name is
#: computable, so there is no index to consult. Everywhere else the roof shape
#: stays whatever it was.
NRW_LOD2 = "https://www.opengeodata.nrw.de/produkte/geobasis/3dg/lod2_gml/lod2_gml"


def measure_buildings(conn: sqlite3.Connection, garden: Garden) -> int:
    """Measure this garden's buildings. Returns how many changed.

    Zero is an ordinary answer: no service for this state, nothing surveyed near
    enough to match, or every building already spoken for by the user.
    """
    anchor = LatLon(lat=garden.latitude, lon=garden.longitude)
    state = state_at(anchor.lat, anchor.lon)
    if state is None:
        return 0

    surveyed = _surveyed(anchor, state)
    surface = _surface(conn, anchor, state)
    if surveyed is None and surface is None:
        return 0
    return apply(conn, measure(garden, surveyed, surface))


def _surveyed(anchor: LatLon, state: str) -> list[Lod2Building] | None:
    """The official 3D model for this square kilometre, on the garden's axes."""
    if state != "Nordrhein-Westfalen":
        return None
    east, north = to_utm(anchor.lat, anchor.lon, 32)
    try:
        document = get_bytes(f"{NRW_LOD2}/{tile_name(east, north)}")
        return in_garden_frame(buildings_from(document), anchor, 32)
    except Exception:
        log.warning("LoD2 tile failed for %s", state, exc_info=True)
        return None


def _surface(
    conn: sqlite3.Connection, anchor: LatLon, state: str
) -> SurfaceWindow | None:
    """Object heights over this garden, from the state's surface model."""
    source = by_state(state)
    if source is None or not measures_buildings(source):
        return None
    ground = load_window(conn, cache_key(anchor))
    try:
        return fetch_surface(anchor, source, ground)
    except Exception:
        log.warning("surface model failed for %s", state, exc_info=True)
        return None


__all__ = ["NRW_LOD2", "measure_buildings"]
