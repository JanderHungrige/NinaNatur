"""Reading and writing garden plans.

Light values are computed on save rather than per request: sampling a season for
several beds is far too slow to repeat on every page load.
"""
from __future__ import annotations

import json
import secrets
import sqlite3

from ninanatur.garden.elements import (
    elements_for,
    geometry_for,
    insert_element,
    update_element,
)
from ninanatur.garden.elements import (
    now as _now,
)
from ninanatur.garden.elements import (
    polygon_centroid as _polygon_centroid,
)
from ninanatur.garden.lighting import recompute_light
from ninanatur.garden.models import (
    PLANTING_KIND,
    BedInput,
    Garden,
    ObstacleInput,
    Planting,
    Polygon,
)
from ninanatur.garden.observations import manual_colours
from ninanatur.garden.plantings import _plantings_for, drop_plantings
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
    recompute_light(conn, garden_id)
    return element_id


def add_obstacle(conn: sqlite3.Connection, garden_id: int, obstacle: ObstacleInput) -> int:
    shape, points, width, hint = geometry_for(
        shape=obstacle.shape, width=obstacle.width, depth=obstacle.depth,
        rotation=obstacle.rotation, points=obstacle.points,
    )
    element_id = insert_element(
        conn, garden_id, kind=obstacle.kind, shape=shape, x=obstacle.x,
        y=obstacle.y, width=width, constraint_hint=hint, height=obstacle.height,
        label=obstacle.label, height_source=obstacle.height_source, points=points,
        roof=obstacle.roof, eaves_m=obstacle.eaves_m,
    )
    _touch(conn, garden_id)
    return element_id


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
    update_element(conn, bed_id, **changes)
    conn.commit()


#: What a caller may change directly. `depth` and `rotation` are absent because
#: they are not columns any more — they are still accepted as *input*, and
#: converted below, because that is what a resize handle produces.
_EDITABLE = frozenset(
    {
        "kind", "x", "y", "label", "height", "height_source", "constraint_hint",
        # A bed may differ from its garden: bought soil, a watered corner.
        "soil_type", "moisture",
        # What shape the roof is. One of the few things somebody can answer by
        # looking out of the window.
        "roof", "eaves_m",
    }
)
_GEOMETRY = frozenset({"shape", "width", "depth", "rotation", "points"})


def update_obstacle(conn: sqlite3.Connection, obstacle_id: int, **fields: object) -> None:
    """Change some of an element's fields. Only what was passed is written.

    An explicit None is a value here, not an omission: clearing the rectangle
    hint is exactly `constraint_hint=None`, and a filter that dropped nulls
    would make it impossible to say. The caller sends only what was set.
    """
    changes = {k: v for k, v in fields.items() if k in _EDITABLE}
    geometry = {k: v for k, v in fields.items() if k in _GEOMETRY}

    if geometry:
        # Width, depth and an angle go in; points come out. Anything not named
        # keeps what the element already has, so a resize does not silently
        # reset a shape to its default.
        current = conn.execute(
            "SELECT shape, width, points, constraint_hint FROM element"
            " WHERE element_id = ?",
            (obstacle_id,),
        ).fetchone()
        if current is None:
            return
        shape_in = str(geometry.get("shape") or current["shape"])
        # A stored polygon carrying the rect hint came from a width and a depth,
        # so that is how a caller may go on editing it.
        if shape_in == "polygon" and current["constraint_hint"] == "rect" and (
            "width" in geometry or "depth" in geometry or "rotation" in geometry
        ):
            shape_in = "rect"
        raw_points = geometry.get("points")
        shape, points, width, hint = geometry_for(
            shape=shape_in,
            width=_number(geometry.get("width")),
            depth=_number(geometry.get("depth")),
            rotation=_number(geometry.get("rotation")) or 0.0,
            points=raw_points if isinstance(raw_points, list) else None,
        )
        # Never null out geometry nobody supplied. A caller sending a width for
        # a free polygon means "make it this big", not "throw the outline away"
        # — and doing the latter left the element with no footprint at all, so
        # reading the garden raised rather than returning it.
        if points is None and shape in {"polygon", "line"}:
            points = None if current["points"] is None else json.loads(current["points"])
        if points is None and shape in {"polygon", "line"}:
            # Nothing stored and nothing given: leave the geometry alone
            # entirely rather than writing a shape with no outline.
            changes.update(width=width)
        else:
            changes.update(shape=shape, width=width, points=points)
        # Only overwrite the hint when the geometry itself decided one; an
        # explicit null from the caller still wins, and that is how dragging a
        # vertex ends the promise.
        if "constraint_hint" not in fields:
            changes["constraint_hint"] = hint

    if not changes:
        return
    # An element that stops being a planting site takes its plants with it.
    # Decided with the user over refusing the change or keeping them hidden:
    # a dead end mid-drawing is worse, and invisible data is worse still. The
    # The UI warns first, counting the plants it is already displaying.
    kind = changes.get("kind")
    if isinstance(kind, str) and kind != PLANTING_KIND:
        drop_plantings(conn, obstacle_id)
    if isinstance(kind, str) and kind == PLANTING_KIND:
        changes.update(_inherited_soil(conn, obstacle_id, changes))
    elif "soil_type" in changes or "moisture" in changes:
        changes.update(_axes_for(conn, obstacle_id, changes))
    update_element(conn, obstacle_id, **changes)
    conn.commit()


def _inherited_soil(
    conn: sqlite3.Connection, element_id: int, changes: dict[str, object]
) -> dict[str, object]:
    """What a new bed starts from: its own answer, or the garden's.

    Only fills what is missing. A raised bed with bought soil keeps what it was
    told, and a garden-level change never reaches back over it.
    """
    current = conn.execute(
        "SELECT soil_type, moisture FROM element WHERE element_id = ?", (element_id,)
    ).fetchone()
    if current is None:
        return {}
    garden_soil, garden_moisture = _garden_soil(conn, element_id)
    soil = changes.get("soil_type") or current["soil_type"] or garden_soil
    moisture = changes.get("moisture") or current["moisture"] or garden_moisture
    if not isinstance(soil, str) or not isinstance(moisture, str):
        return {}
    return {"soil_type": soil, "moisture": moisture, **site_axes_from_soil(soil, moisture)}


def _axes_for(
    conn: sqlite3.Connection, element_id: int, changes: dict[str, object]
) -> dict[str, object]:
    """Re-derive the axes when a bed is told a different soil or moisture."""
    current = conn.execute(
        "SELECT soil_type, moisture FROM element WHERE element_id = ?", (element_id,)
    ).fetchone()
    if current is None:
        return {}
    soil = changes.get("soil_type") or current["soil_type"]
    moisture = changes.get("moisture") or current["moisture"]
    if not isinstance(soil, str) or not isinstance(moisture, str):
        return {}
    return dict(site_axes_from_soil(soil, moisture))


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) else None


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


def _garden_soil(conn: sqlite3.Connection, element_id: int) -> tuple[str | None, str | None]:
    row = conn.execute(
        "SELECT g.soil_type, g.moisture FROM element e"
        " JOIN garden g ON g.garden_id = e.garden_id WHERE e.element_id = ?",
        (element_id,),
    ).fetchone()
    return (None, None) if row is None else (row["soil_type"], row["moisture"])


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
