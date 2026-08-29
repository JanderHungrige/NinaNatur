"""Address search, and turning a map selection into a garden.

Both outbound calls go through the server rather than the browser. Nominatim and
Overpass ask for a User-Agent that identifies the caller and for restraint in
how often you call; doing that in one place is possible, doing it in every
visitor's browser is not — and a visitor's browser cannot share a cache.
"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ninanatur.api.deps import get_connection
from ninanatur.api.gardens import to_out
from ninanatur.api.schemas import (
    HeightReport,
    ImageryOut,
    MapGardenOut,
    MapSelection,
    PlaceOut,
    PlaceSearchOut,
)
from ninanatur.garden.models import BedInput, ObstacleInput
from ninanatur.garden.store import (
    add_bed,
    add_obstacle,
    create_garden,
    load_garden,
    recompute_light,
)
from ninanatur.geo.orthophotos import by_state
from ninanatur.geo.osm import buildings_in, search_address, state_at
from ninanatur.geo.projection import LatLon, bounding_box, centroid, to_metres
from ninanatur.geo.surroundings import MARGIN_M, NeighbourhoodKind, surroundings_from

router = APIRouter(prefix="/api/v1", tags=["geo"])


@router.get("/geo/search", response_model=PlaceSearchOut)
def find_place(q: Annotated[str, Query(max_length=200)] = "") -> PlaceSearchOut:
    """Addresses matching a query. Empty in, empty out — a keystroke-per-request
    search would be a poor way to treat a free community service."""
    places = search_address(q)
    return PlaceSearchOut(
        places=[PlaceOut(name=p.name, lat=p.lat, lon=p.lon) for p in places]
    )


@router.get("/geo/imagery", response_model=ImageryOut)
def imagery_at(
    lat: Annotated[float, Query(ge=47.0, le=55.2)],
    lon: Annotated[float, Query(ge=5.5, le=15.2)],
) -> ImageryOut:
    """Which state's orthophotos may be shown here, if any.

    Per Bundesland because the licences are: there is no federal source, and a
    state without an entry gets no imagery rather than a neighbour's.
    """
    state = state_at(lat, lon)
    entry = by_state(state) if state else None
    if entry is None:
        return ImageryOut(available=False, state=state)
    return ImageryOut(
        available=True,
        state=entry.state,
        url=entry.url,
        layer=entry.layer,
        licence=entry.licence,
        attribution=entry.attribution,
    )


@router.post(
    "/gardens/from-map", response_model=MapGardenOut, status_code=status.HTTP_201_CREATED
)
def garden_from_map(
    payload: MapSelection,
    conn: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> MapGardenOut:
    """Create a garden from an outline drawn on the map, with what shades it.

    The margin is 50 m and objects are filtered by whether their shadow could
    arrive at all — generous where it matters, quiet where it does not.
    """
    outline = [LatLon(lat=p.lat, lon=p.lon) for p in payload.outline]
    anchor = centroid(outline)

    south, west, north, east = bounding_box(anchor, MARGIN_M)
    found = buildings_in(south, west, north, east)
    around = surroundings_from(
        anchor, found, neighbourhood=NeighbourhoodKind(payload.neighbourhood)
    )

    garden_id = create_garden(
        conn, name=payload.name, latitude=anchor.lat, longitude=anchor.lon
    )
    polygon = [[round(m.x, 2), round(m.y, 2)] for m in (to_metres(p, anchor) for p in outline)]
    add_bed(
        conn,
        garden_id,
        BedInput(name="Gesamtfläche", polygon=polygon, soil_type="loam", moisture="fresh"),
    )
    for obj in around.objects:
        add_obstacle(
            conn,
            garden_id,
            ObstacleInput(
                kind="building",
                x=obj.x,
                y=obj.y,
                radius=obj.radius_m,
                height=obj.height_m,
                label=obj.label,
            ),
        )
    recompute_light(conn, garden_id)

    return MapGardenOut(
        garden=to_out(load_garden(conn, garden_id)),
        heights=HeightReport(
            measured=around.measured, estimated=around.estimated, assumed=around.assumed
        ),
    )
