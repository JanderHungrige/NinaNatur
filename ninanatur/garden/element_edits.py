"""Changing what is already drawn: an element's kind, its numbers, its outline,
and the soil a bed inherits.

Split from `store.py` in Wave 21, which keeps creating, loading and deleting.
An update writes only what it was given — an update that also rewrote the
untouched fields would turn a partial edit into a full overwrite.
"""
from __future__ import annotations

import json
import sqlite3

from ninanatur.garden.elements import geometry_for, update_element
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.plantings import drop_plantings
from ninanatur.garden.soil import site_axes_from_soil


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
        # Set by the endpoint from what changed, never taken from a caller.
        "roof_source", "eaves_source", "roof_fall_deg",
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
        # A new outline is not the one the survey read a ridge off (doc 94);
        # a move keeps it, because x and y are not geometry.
        changes["roof_fall_deg"] = None
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


def _garden_soil(conn: sqlite3.Connection, element_id: int) -> tuple[str | None, str | None]:
    row = conn.execute(
        "SELECT g.soil_type, g.moisture FROM element e"
        " JOIN garden g ON g.garden_id = e.garden_id WHERE e.element_id = ?",
        (element_id,),
    ).fetchone()
    return (None, None) if row is None else (row["soil_type"], row["moisture"])
