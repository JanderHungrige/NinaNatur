"""Reading and writing garden plans.

Light values are computed on save rather than per request: sampling a season for
several beds is far too slow to repeat on every page load.
"""
from __future__ import annotations

import secrets
import sqlite3

from ninanatur.garden.elements import (
    elements_for,
    geometry_for,
    insert_element,
)
from ninanatur.garden.elements import (
    now as _now,
)
from ninanatur.garden.elements import (
    polygon_centroid as _polygon_centroid,
)
from ninanatur.garden.footprint import require_buildable
from ninanatur.garden.models import (
    PLANTING_KIND,
    BedInput,
    Garden,
    ObstacleInput,
    Planting,
    Polygon,
)
from ninanatur.garden.observations import manual_colours
from ninanatur.garden.plantings import _plantings_for
from ninanatur.garden.soil import site_axes_from_soil
from ninanatur.solar.position import Location

# 32 bytes of entropy. The token is the entire access control for a garden, so it
# has to resist enumeration outright rather than merely slow it down.
TOKEN_BYTES = 32
MIN_POLYGON_POINTS = 3


class PolygonError(ValueError):
    """A polygon that does not describe an area."""


def _validate_polygon(polygon: Polygon) -> Polygon:
    if len(polygon) < MIN_POLYGON_POINTS:
        raise PolygonError(
            f"a bed needs at least {MIN_POLYGON_POINTS} points, got {len(polygon)}"
        )
    for point in polygon:
        if len(point) != 2 or not all(isinstance(c, int | float) for c in point):
            raise PolygonError(f"polygon points must be [x, y] numbers, got {point!r}")
    return polygon


def create_garden(
    conn: sqlite3.Connection,
    *,
    name: str,
    latitude: float,
    longitude: float,
    owner_id: str | None = None,
) -> int:
    """Create a garden and return its id.

    The location is rounded by `Location` before it is ever stored, to four
    decimal places — about 7 m. Deliberate, and no longer coarse: it was 0.1°
    (~6.6 km) while the coordinates only fed sun angles, and that put Wave 17's
    terrain window on a different hillside. `solar.position.LOCATION_PRECISION`
    carries the reasoning, including why the rounding is not what keeps the
    address private.
    """
    location = Location(latitude=latitude, longitude=longitude)
    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO garden (share_token, owner_id, name, latitude, longitude,
                            created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            secrets.token_urlsafe(TOKEN_BYTES),
            owner_id,
            name,
            location.latitude,
            location.longitude,
            now,
            now,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid or 0)


def add_bed(conn: sqlite3.Connection, garden_id: int, bed: BedInput) -> int:
    """Add a bed, deriving its soil axes and computing its light.

    The light computation lives here rather than in the API so the invariant
    holds whatever the entry point. It used to be the route's job, which meant a
    bed created through the store had no light value — and everything downstream
    then scored it on soil alone, silently, because a missing axis is skipped
    rather than flagged.
    """
    _validate_polygon(bed.polygon)
    axes: dict[str, float] = {}
    if bed.soil_type and bed.moisture:
        axes = site_axes_from_soil(bed.soil_type, bed.moisture)

    # Stored around its own centre so that moving it later is one update rather
    # than a rewrite of every corner.
    cx, cy = _polygon_centroid(bed.polygon)
    element_id = insert_element(
        conn,
        garden_id,
        kind=PLANTING_KIND,
        shape="polygon",
        x=cx,
        y=cy,
        name=bed.name,
        soil_type=bed.soil_type,
        moisture=bed.moisture,
        ellenberg_m=axes.get("ellenberg_m"),
        ellenberg_n=axes.get("ellenberg_n"),
        ellenberg_r=axes.get("ellenberg_r"),
        points=[[p[0] - cx, p[1] - cy] for p in bed.polygon],
    )
    _touch(conn, garden_id)
    # No recomputation here. See `lighting.recompute_light` for why every write
    # path stopped doing this.
    return element_id


def add_obstacle(conn: sqlite3.Connection, garden_id: int, obstacle: ObstacleInput) -> int:
    shape, points, width, hint = geometry_for(
        shape=obstacle.shape, width=obstacle.width, depth=obstacle.depth,
        rotation=obstacle.rotation, points=obstacle.points,
    )
    # Before the insert: a row written first and refused afterwards stays
    # committed, and breaks every later read of the garden.
    require_buildable(shape=shape, width=width, points=points)
    element_id = insert_element(
        conn, garden_id, kind=obstacle.kind, shape=shape, x=obstacle.x,
        y=obstacle.y, width=width, constraint_hint=hint, height=obstacle.height,
        label=obstacle.label, height_source=obstacle.height_source, points=points,
        roof=obstacle.roof, roof_source=obstacle.roof_source,
        eaves_m=obstacle.eaves_m, eaves_source=obstacle.eaves_source,
    )
    _touch(conn, garden_id)
    return element_id


def set_garden_soil(
    conn: sqlite3.Connection, garden_id: int, *, soil_type: str, moisture: str
) -> None:
    """Record what the ground is, once, for the whole garden.

    One question per garden rather than one per bed — the shape Wave 8 settled
    on for building heights, and for the same reason: asking it of every bed is
    a wall in front of somebody who has just arrived.

    Beds that already carry their own answer are left alone. This value is a
    starting point for what is drawn next, not a broadcast over what exists.
    """
    # Validated here rather than at the edge, so the invariant holds whatever
    # the entry point — and an unknown soil would otherwise reach the axes.
    site_axes_from_soil(soil_type, moisture)
    conn.execute(
        "UPDATE garden SET soil_type = ?, moisture = ? WHERE garden_id = ?",
        (soil_type, moisture, garden_id),
    )
    _touch(conn, garden_id)


def _touch(conn: sqlite3.Connection, garden_id: int) -> None:
    conn.execute("UPDATE garden SET updated_at = ? WHERE garden_id = ?", (_now(), garden_id))
    conn.commit()


def _load(conn: sqlite3.Connection, row: sqlite3.Row | None) -> Garden | None:
    if row is None:
        return None
    garden_id = int(row["garden_id"])
    # One query for the plantings rather than one per element: a garden with
    # twenty beds was twenty round trips, and the loop that made them was easy
    # to miss because each one on its own is fast.
    plantings: dict[int, list[Planting]] = {}
    for element_id in (
        int(r[0])
        for r in conn.execute(
            "SELECT DISTINCT p.element_id FROM planting p"
            " JOIN element e ON e.element_id = p.element_id WHERE e.garden_id = ?",
            (garden_id,),
        )
    ):
        plantings[element_id] = _plantings_for(conn, element_id)
    return Garden(
        garden_id=garden_id,
        share_token=row["share_token"],
        owner_id=row["owner_id"],
        name=row["name"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        soil_type=row["soil_type"],
        moisture=row["moisture"],
        observed_colours=manual_colours(conn),
        elements=elements_for(conn, garden_id, plantings),
    )


def load_garden(conn: sqlite3.Connection, garden_id: int) -> Garden:
    garden = _load(conn, conn.execute(
        "SELECT * FROM garden WHERE garden_id = ?", (garden_id,)).fetchone())
    if garden is None:
        raise LookupError(f"no such garden: {garden_id}")
    return garden


def garden_by_token(conn: sqlite3.Connection, token: str) -> Garden | None:
    """Fetch by share token. Returns None for an unknown token — never raises,
    so a probe cannot distinguish 'wrong token' from 'server error'."""
    return _load(conn, conn.execute(
        "SELECT * FROM garden WHERE share_token = ?", (token,)).fetchone())


def delete_garden(conn: sqlite3.Connection, garden_id: int) -> None:
    """Beds and obstacles go with it — the FKs cascade and enforcement is on."""
    conn.execute("DELETE FROM garden WHERE garden_id = ?", (garden_id,))
    conn.commit()
