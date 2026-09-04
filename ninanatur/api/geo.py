"""Address search, and turning a map selection into a garden.

Both outbound calls go through the server rather than the browser. Nominatim and
Overpass ask for a User-Agent that identifies the caller and for restraint in
how often you call; doing that in one place is possible, doing it in every
visitor's browser is not — and a visitor's browser cannot share a cache.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from ninanatur.api.accounts import current_account
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
from ninanatur.auth.sessions import Account
from ninanatur.garden.lighting import recompute_light
from ninanatur.garden.models import ObstacleInput
from ninanatur.garden.store import (
    add_obstacle,
    create_garden,
    load_garden,
)
from ninanatur.geo.orthophotos import by_state
from ninanatur.geo.osm import buildings_in, search_address, state_at, streets_in
from ninanatur.geo.projection import LatLon, bounding_box_of, centroid, to_metres
from ninanatur.geo.surroundings import MARGIN_M, NeighbourhoodKind, surroundings_from

logger = logging.getLogger(__name__)

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
    account: Annotated[Account | None, Depends(current_account)] = None,
) -> MapGardenOut:
    """Create a garden from an outline drawn on the map, with what shades it.

    The margin is 50 m and objects are filtered by whether their shadow could
    arrive at all — generous where it matters, quiet where it does not.
    """
    outline = [LatLon(lat=p.lat, lon=p.lon) for p in payload.outline]
    anchor = centroid(outline)

    # Around the whole plot, not around its middle. A box drawn from the
    # centroid of a 60 m garden reaches 20 m past the hedge instead of 50, so a
    # farmyard's neighbours were never fetched to be judged at all.
    south, west, north, east = bounding_box_of(outline, MARGIN_M)
    found = buildings_in(south, west, north, east)
    around = surroundings_from(
        anchor,
        found,
        neighbourhood=NeighbourhoodKind(payload.neighbourhood),
        outline=outline,
    )

    # Theirs from the moment it exists, like the plain create. This is the way
    # most people start, so it is the one that mattered most.
    garden_id = create_garden(
        conn,
        name=payload.name,
        latitude=anchor.lat,
        longitude=anchor.lon,
        owner_id=None if account is None else str(account.account_id),
    )
    _add_streets(conn, garden_id, anchor, south, west, north, east)

    polygon = [[round(m.x, 2), round(m.y, 2)] for m in (to_metres(p, anchor) for p in outline)]
    # The ground, not a bed. It used to arrive as one large flower bed, which
    # made the whole plot a planting site — the beds are what the gardener draws
    # inside it, and a garden that arrives with none is the honest starting
    # state.
    add_obstacle(
        conn,
        garden_id,
        ObstacleInput(
            kind="garden",
            x=0.0,
            y=0.0,
            shape="polygon",
            points=polygon,
            label=payload.name,
        ),
    )
    for obj in around.objects:
        # The shape OSM drew, when it drew one. The square this replaces was
        # sized from half the bounding box's diagonal and came out 2.1 to 2.8
        # times the real footprint on live data — every one axis-aligned, so a
        # farmyard arrived as a pile of overlapping boxes at the wrong angles.
        #
        # A square is still the answer when Overpass sent no geometry, and then
        # it is sized from the equal-area radius rather than the diagonal.
        if len(obj.outline) >= 3:
            drawn = ObstacleInput(
                kind="house",
                x=obj.x,
                y=obj.y,
                shape="polygon",
                points=[[corner[0], corner[1]] for corner in obj.outline],
                height=obj.height_m,
                label=obj.label,
                height_source=obj.height_source.value,
            )
        else:
            side = obj.radius_m * 1.77
            drawn = ObstacleInput(
                kind="house",
                x=obj.x,
                y=obj.y,
                shape="rect",
                width=side,
                depth=side,
                rotation=0.0,
                height=obj.height_m,
                label=obj.label,
                height_source=obj.height_source.value,
            )
        add_obstacle(conn, garden_id, drawn)
    recompute_light(conn, garden_id)

    return MapGardenOut(
        garden=to_out(load_garden(conn, garden_id)),
        heights=HeightReport(
            measured=around.measured, estimated=around.estimated, assumed=around.assumed
        ),
    )


def _add_streets(
    conn: sqlite3.Connection,
    garden_id: int,
    anchor: LatLon,
    south: float,
    west: float,
    north: float,
    east: float,
) -> None:
    """Draw the ways around the garden, as lines.

    A street is a centreline and a width, which is exactly the `line` element
    Wave 11 built — no polygon anybody had to trace around a road, and
    `band_of` already turns it into the footprint everything downstream reads.

    It carries no height on purpose. A road does not shade a garden, and a
    height here would put it into the light model as an obstacle.

    Overpass is a free service with the same no-SLA standing as Nominatim. A
    refusal costs the streets, not the garden.
    """
    try:
        found = streets_in(south, west, north, east)
    except Exception as unreachable:  # noqa: BLE001 — the garden matters more
        logger.warning("streets unavailable, garden made without them: %s", unreachable)
        return

    for street in found:
        metres = [to_metres(p, anchor) for p in street.centreline]
        # Around its own first point, so moving it later is one update rather
        # than a rewrite of every corner.
        origin = metres[0]
        add_obstacle(
            conn,
            garden_id,
            ObstacleInput(
                kind="street",
                x=round(origin.x, 2),
                y=round(origin.y, 2),
                shape="line",
                width=street.width_m,
                points=[
                    [round(m.x - origin.x, 2), round(m.y - origin.y, 2)] for m in metres
                ],
                # None, not zero: a street has no height, and Wave 8's rule is
                # that an unrecorded one is never a zero. With none it never
                # reaches the light model as an obstacle.
                height=None,
                label=street.name,
            ),
        )
