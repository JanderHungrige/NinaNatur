"""Reading and writing garden plans.

Light values are computed on save rather than per request: sampling a season for
several beds is far too slow to repeat on every page load.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import UTC, datetime

from ninanatur.garden.canopy import Canopy, canopy_of, shades
from ninanatur.garden.models import (
    Bed,
    BedInput,
    Garden,
    Obstacle,
    ObstacleInput,
    Planting,
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


class UnknownTaxon(ValueError):
    """A planting pointing at a species that is not in the catalogue.

    Rejected rather than stored: a dangling reference would leave the bloom
    timeline silently short a species instead of failing where it can be seen.
    """


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
    recompute_light(conn, garden_id)
    return int(cursor.lastrowid or 0)


def add_obstacle(conn: sqlite3.Connection, garden_id: int, obstacle: ObstacleInput) -> int:
    cursor = conn.execute(
        "INSERT INTO obstacle (garden_id, kind, x, y, radius, height, label, height_source)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (garden_id, obstacle.kind, obstacle.x, obstacle.y, obstacle.radius,
         obstacle.height, obstacle.label, obstacle.height_source),
    )
    _touch(conn, garden_id)
    return int(cursor.lastrowid or 0)


def add_planting(
    conn: sqlite3.Connection,
    bed_id: int,
    taxon_id: int | None = None,
    quantity: int = 1,
    raw_name: str | None = None,
) -> int:
    """Put a plant in a bed, named or not.

    `taxon_id` identifies it against the catalogue; `raw_name` is what the user
    typed. A planting with only a raw name is one the catalogue could not name —
    an ordinary answer, since it holds 8,939 German species and no cultivars at
    all. Refusing it would tell someone their garden is wrong because our data
    is incomplete.
    """
    if quantity < 1:
        # Zero would be a deletion expressed as an update, and the two would then
        # disagree about whether the species is in the bed at all.
        raise ValueError(f"quantity must be at least 1, got {quantity}")
    if taxon_id is None and not (raw_name or "").strip():
        raise ValueError("a planting needs either a taxon or a name")

    if taxon_id is not None:
        known = conn.execute(
            "SELECT 1 FROM taxon WHERE taxon_id = ?", (taxon_id,)
        ).fetchone()
        if known is None:
            raise UnknownTaxon(f"no such taxon in the catalogue: {taxon_id}")

    if taxon_id is None:
        # No conflict target: NULLs are distinct, so two unidentified roses are
        # two rows, which is what should happen.
        cursor = conn.execute(
            "INSERT INTO planting (bed_id, taxon_id, raw_name, quantity, added_at)"
            " VALUES (?, NULL, ?, ?, ?)",
            (bed_id, raw_name, quantity, _now()),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)

    conn.execute(
        """
        INSERT INTO planting (bed_id, taxon_id, raw_name, quantity, added_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (bed_id, taxon_id) DO UPDATE SET
            quantity = planting.quantity + excluded.quantity,
            -- Never overwrite the words the user typed with nothing.
            raw_name = COALESCE(excluded.raw_name, planting.raw_name)
        """,
        (bed_id, taxon_id, raw_name, quantity, _now()),
    )
    conn.commit()
    _relight_if_woody(conn, bed_id, taxon_id)
    row = conn.execute(
        "SELECT planting_id FROM planting WHERE bed_id = ? AND taxon_id = ?",
        (bed_id, taxon_id),
    ).fetchone()
    return int(row["planting_id"])


def _relight_if_woody(conn: sqlite3.Connection, bed_id: int, taxon_id: int) -> None:
    """Recompute the garden's light when what was planted casts a shadow.

    Here rather than in the route, for the same reason the light computation
    itself lives in this module: the invariant has to hold whatever the entry
    point. Every unit test of planted shade called `recompute_light` itself and
    passed, while the running app left a bed at 12.6 h and Ellenberg 8 with a
    24 m oak standing in it.

    Skipped for anything under 1.5 m — recomputing a whole garden for a
    perennial is work that cannot change an answer.
    """
    canopy = _woody_heights(conn, [taxon_id]).get(taxon_id)
    if not shades(canopy):
        return
    row = conn.execute("SELECT garden_id FROM bed WHERE bed_id = ?", (bed_id,)).fetchone()
    if row is not None:
        recompute_light(conn, int(row["garden_id"]))


def update_bed(conn: sqlite3.Connection, bed_id: int, **fields: object) -> None:
    """Change some of a bed's fields. Only what was passed is written.

    An update that also rewrites the untouched fields turns a partial edit into
    a full overwrite, and two people editing different things would clobber
    each other.
    """
    allowed = {"name", "soil_type", "moisture", "height_above_ground", "label"}
    changes = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not changes:
        return
    assignments = ", ".join(f"{k} = ?" for k in changes)
    conn.execute(
        f"UPDATE bed SET {assignments} WHERE bed_id = ?",  # noqa: S608
        (*changes.values(), bed_id),
    )
    conn.commit()


def update_obstacle(conn: sqlite3.Connection, obstacle_id: int, **fields: object) -> None:
    """Change some of an obstacle's fields. Only what was passed is written."""
    allowed = {"kind", "x", "y", "radius", "height", "label", "height_source"}
    changes = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not changes:
        return
    assignments = ", ".join(f"{k} = ?" for k in changes)
    conn.execute(
        f"UPDATE obstacle SET {assignments} WHERE obstacle_id = ?",  # noqa: S608
        (*changes.values(), obstacle_id),
    )
    conn.commit()


def remove_planting(conn: sqlite3.Connection, planting_id: int) -> None:
    # Read the bed before the row is gone: removing a tree gives the light back,
    # and afterwards there is nothing left to say which garden to recompute.
    row = conn.execute(
        "SELECT p.bed_id, p.taxon_id, b.garden_id FROM planting p"
        " JOIN bed b ON b.bed_id = p.bed_id WHERE p.planting_id = ?",
        (planting_id,),
    ).fetchone()
    conn.execute("DELETE FROM planting WHERE planting_id = ?", (planting_id,))
    conn.commit()
    if row is None:
        return
    canopy = _woody_heights(conn, [int(row["taxon_id"])]).get(int(row["taxon_id"]))
    if shades(canopy):
        recompute_light(conn, int(row["garden_id"]))


def _plantings_for(conn: sqlite3.Connection, bed_id: int) -> list[Planting]:
    return [
        Planting(
            planting_id=int(r["planting_id"]),
            taxon_id=None if r["taxon_id"] is None else int(r["taxon_id"]),
            canonical_name=r["canonical_name"],
            quantity=int(r["quantity"]),
            added_at=r["added_at"],
            raw_name=r["raw_name"],
        )
        for r in conn.execute(
            """
            -- LEFT, not INNER: an inner join drops exactly the rows this
            -- feature exists to keep — the plants the catalogue cannot name.
            SELECT p.planting_id, p.taxon_id, p.quantity, p.added_at, p.raw_name,
                   x.canonical_name
            FROM planting p LEFT JOIN taxon x ON x.taxon_id = p.taxon_id
            WHERE p.bed_id = ? ORDER BY COALESCE(x.canonical_name, p.raw_name)
            """,
            (bed_id,),
        )
    ]


def _touch(conn: sqlite3.Connection, garden_id: int) -> None:
    conn.execute("UPDATE garden SET updated_at = ? WHERE garden_id = ?", (_now(), garden_id))
    conn.commit()


def _polygon_centroid(polygon: Polygon) -> Point:
    return Point(
        x=sum(p[0] for p in polygon) / len(polygon),
        y=sum(p[1] for p in polygon) / len(polygon),
    )


def _planted_obstacles(
    conn: sqlite3.Connection, garden: Garden
) -> list[tuple[int, ShadingObstacle]]:
    """Woody plantings, as the shadows they will cast, tagged with their own bed.

    A bed is a marked area; a tree standing in it is not a different kind of bed,
    it is a thing that blocks the sun. The shading model already describes
    obstacles as vertical cylinders — the exact shape of a tree — and simply was
    never told about the ones the user plants.

    Positioned at the bed's centroid because a planting has no coordinates of
    its own — which is also why the bed it stands in is excluded from its
    shadow. Light is sampled at that same centroid, so a plant would always sit
    exactly on the sample point and darken its own bed completely: one 2 m shrub
    in a 16 m² bed took it from 12.6 sun hours to 0.0 and Ellenberg 8 to 3.

    That is an artifact of not knowing where in the bed the plant stands, not a
    fact about shade. Between beds the geometry is real and is used. Wave 7's
    drawing tool gives plantings a position, and this exclusion goes with it.
    """
    heights = _woody_heights(
        conn,
        [p.taxon_id for bed in garden.beds for p in bed.plantings if p.taxon_id is not None],
    )
    obstacles: list[tuple[int, ShadingObstacle]] = []
    for bed in garden.beds:
        centre = _polygon_centroid(bed.polygon)
        for planting in bed.plantings:
            if planting.taxon_id is None:
                continue
            canopy = heights.get(planting.taxon_id)
            if not shades(canopy):
                continue
            assert canopy is not None  # narrowed by shades()
            obstacles.append(
                (
                    bed.bed_id,
                    ShadingObstacle(
                        x=centre.x, y=centre.y, radius=canopy.radius_m, height=canopy.height_m
                    ),
                )
            )
    return obstacles


def _woody_heights(
    conn: sqlite3.Connection, taxon_ids: list[int]
) -> dict[int, Canopy | None]:
    """Height and growth form for a set of species, in one query."""
    if not taxon_ids:
        return {}
    unique = sorted(set(taxon_ids))
    placeholders = ",".join("?" for _ in unique)
    rows = conn.execute(
        "SELECT taxon_id, trait_key, value_num, value_text FROM trait"
        f" WHERE taxon_id IN ({placeholders})"  # noqa: S608
        " AND trait_key IN ('height_max_m', 'growth_form')",
        unique,
    )
    heights: dict[int, float] = {}
    forms: dict[int, str] = {}
    for row in rows:
        tid = int(row["taxon_id"])
        if row["trait_key"] == "height_max_m" and row["value_num"] is not None:
            # Sources disagree and none overwrites another; the tallest recorded
            # value is the one that decides whether a shadow reaches a neighbour.
            heights[tid] = max(heights.get(tid, 0.0), float(row["value_num"]))
        elif row["value_text"] is not None:
            forms[tid] = str(row["value_text"])
    return {tid: canopy_of(heights.get(tid), forms.get(tid)) for tid in unique}


def recompute_light(conn: sqlite3.Connection, garden_id: int) -> int:
    """Recompute every bed's light from the garden's obstacles and its own trees.

    Returns beds updated.
    """
    garden = load_garden(conn, garden_id)
    obstacles = [
        ShadingObstacle(x=o.x, y=o.y, radius=o.radius, height=o.height)
        for o in garden.obstacles
    ]
    planted = _planted_obstacles(conn, garden)
    location = Location(latitude=garden.latitude, longitude=garden.longitude)

    updated = 0
    for bed in garden.beds:
        # A bed is not shaded by what grows in it — see _planted_obstacles.
        from_others = [o for owner, o in planted if owner != bed.bed_id]
        light = bed_light_value(
            location,
            _polygon_centroid(bed.polygon),
            obstacles + from_others,
            height_above_ground=bed.height_above_ground,
        )
        conn.execute(
            "UPDATE bed SET ellenberg_l = ?, sun_hours = ?, light_computed_at = ?"
            " WHERE bed_id = ?",
            (light.ellenberg_l, light.sun_hours, _now(), bed.bed_id),
        )
        updated += 1
    conn.commit()
    return updated


def _row_to_bed(row: sqlite3.Row, plantings: list[Planting] | None = None) -> Bed:
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
        height_above_ground=float(row["height_above_ground"] or 0.0),
        label=row["label"],
        plantings=plantings or [],
    )


def _load(conn: sqlite3.Connection, row: sqlite3.Row | None) -> Garden | None:
    if row is None:
        return None
    garden_id = int(row["garden_id"])
    bed_rows = conn.execute(
        "SELECT * FROM bed WHERE garden_id = ? ORDER BY bed_id", (garden_id,)
    ).fetchall()
    beds = [_row_to_bed(r, _plantings_for(conn, int(r["bed_id"]))) for r in bed_rows]
    obstacles = [
        Obstacle(
            obstacle_id=int(r["obstacle_id"]), kind=r["kind"],
            x=r["x"], y=r["y"], radius=r["radius"], height=r["height"],
            label=r["label"], height_source=r["height_source"],
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
