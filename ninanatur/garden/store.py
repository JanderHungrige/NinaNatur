"""Reading and writing garden plans.

Light values are computed on save rather than per request: sampling a season for
several beds is far too slow to repeat on every page load.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import UTC, datetime

from ninanatur.garden.models import (
    Bed,
    BedInput,
    Garden,
    Obstacle,
    ObstacleInput,
    Polygon,
)
from ninanatur.garden.soil import site_axes_from_soil
from ninanatur.solar.light import bed_light_value
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle as ShadingObstacle
from ninanatur.solar.shading import Point

# 32 bytes of entropy. The token is the entire access control for a garden, so it
# has to resist enumeration outright rather than merely slow it down.
TOKEN_BYTES = 32
MIN_POLYGON_POINTS = 3


class PolygonError(ValueError):
    """A polygon that does not describe an area."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _validate_polygon(polygon: Polygon) -> Polygon:
    if len(polygon) < MIN_POLYGON_POINTS:
        raise PolygonError(
            f"a bed needs at least {MIN_POLYGON_POINTS} points, got {len(polygon)}"
        )
    for point in polygon:
        if len(point) != 2 or not all(isinstance(c, (int, float)) for c in point):
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

    The location is rounded by `Location` before it is ever stored — 0.1° is about
    11 km, which solar geometry cannot tell apart and which keeps a private
    garden's coordinates coarse.
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
    """Add a bed, deriving its soil axes if a soil description was given."""
    _validate_polygon(bed.polygon)
    axes: dict[str, float] = {}
    if bed.soil_type and bed.moisture:
        axes = site_axes_from_soil(bed.soil_type, bed.moisture)

    cursor = conn.execute(
        """
        INSERT INTO bed (garden_id, name, polygon, soil_type, moisture,
                         ellenberg_m, ellenberg_n, ellenberg_r)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            garden_id,
            bed.name,
            json.dumps(bed.polygon),
            bed.soil_type,
            bed.moisture,
            axes.get("ellenberg_m"),
            axes.get("ellenberg_n"),
            axes.get("ellenberg_r"),
        ),
    )
    _touch(conn, garden_id)
    return int(cursor.lastrowid or 0)


def add_obstacle(conn: sqlite3.Connection, garden_id: int, obstacle: ObstacleInput) -> int:
    cursor = conn.execute(
        "INSERT INTO obstacle (garden_id, kind, x, y, radius, height) VALUES (?, ?, ?, ?, ?, ?)",
        (garden_id, obstacle.kind, obstacle.x, obstacle.y, obstacle.radius, obstacle.height),
    )
    _touch(conn, garden_id)
    return int(cursor.lastrowid or 0)


def _touch(conn: sqlite3.Connection, garden_id: int) -> None:
    conn.execute("UPDATE garden SET updated_at = ? WHERE garden_id = ?", (_now(), garden_id))
    conn.commit()


def _polygon_centroid(polygon: Polygon) -> Point:
    return Point(
        x=sum(p[0] for p in polygon) / len(polygon),
        y=sum(p[1] for p in polygon) / len(polygon),
    )


def recompute_light(conn: sqlite3.Connection, garden_id: int) -> int:
    """Recompute every bed's light from the garden's obstacles. Returns beds updated."""
    garden = load_garden(conn, garden_id)
    obstacles = [
        ShadingObstacle(x=o.x, y=o.y, radius=o.radius, height=o.height)
        for o in garden.obstacles
    ]
    location = Location(latitude=garden.latitude, longitude=garden.longitude)

    updated = 0
    for bed in garden.beds:
        light = bed_light_value(location, _polygon_centroid(bed.polygon), obstacles)
        conn.execute(
            "UPDATE bed SET ellenberg_l = ?, sun_hours = ?, light_computed_at = ?"
            " WHERE bed_id = ?",
            (light.ellenberg_l, light.sun_hours, _now(), bed.bed_id),
        )
        updated += 1
    conn.commit()
    return updated


def _row_to_bed(row: sqlite3.Row) -> Bed:
    return Bed(
        bed_id=int(row["bed_id"]),
        name=row["name"],
        polygon=json.loads(row["polygon"]),
        soil_type=row["soil_type"],
        moisture=row["moisture"],
        ellenberg_l=row["ellenberg_l"],
        ellenberg_m=row["ellenberg_m"],
        ellenberg_n=row["ellenberg_n"],
        ellenberg_r=row["ellenberg_r"],
        sun_hours=row["sun_hours"],
        light_computed_at=row["light_computed_at"],
    )


def _load(conn: sqlite3.Connection, row: sqlite3.Row | None) -> Garden | None:
    if row is None:
        return None
    garden_id = int(row["garden_id"])
    beds = [
        _row_to_bed(r)
        for r in conn.execute("SELECT * FROM bed WHERE garden_id = ? ORDER BY bed_id", (garden_id,))
    ]
    obstacles = [
        Obstacle(
            obstacle_id=int(r["obstacle_id"]), kind=r["kind"],
            x=r["x"], y=r["y"], radius=r["radius"], height=r["height"],
        )
        for r in conn.execute(
            "SELECT * FROM obstacle WHERE garden_id = ? ORDER BY obstacle_id", (garden_id,)
        )
    ]
    return Garden(
        garden_id=garden_id,
        share_token=row["share_token"],
        owner_id=row["owner_id"],
        name=row["name"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        beds=beds,
        obstacles=obstacles,
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
