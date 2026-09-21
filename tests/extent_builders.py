"""Gardens as the map import leaves them, for the light grid's extent tests."""
from __future__ import annotations

import sqlite3

from ninanatur.garden.elements import insert_element
from ninanatur.garden.lightgrid_extent import GRID_MARGIN_M
from ninanatur.garden.store import create_garden

M = GRID_MARGIN_M


def rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


#: The plot a 25 x 40 m garden arrives with, and the box its grid covers.
PLOT = rect(0.0, 0.0, 25.0, 40.0)
PLOT_BOX = (-M, -M, 25.0 + M, 40.0 + M)


def garden_with(conn: sqlite3.Connection, plot: list[list[float]] | None) -> int:
    """A plot (or none), with one bed inside it."""
    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    if plot is not None:
        insert_element(conn, garden_id, kind="garden", shape="polygon", x=0, y=0,
                       points=plot)
    insert_element(conn, garden_id, kind="bed", shape="polygon", x=0, y=0,
                   name="Beet", points=rect(2.0, 2.0, 6.0, 5.0))
    conn.commit()
    return garden_id


def add(conn: sqlite3.Connection, garden_id: int, kind: str,
        points: list[list[float]], height: float | None,
        height_source: str = "user", roof_source: str = "user") -> int:
    """One element. A street is a 7 m line, everything else an outline."""
    shape = "line" if kind == "street" else "polygon"
    element_id = insert_element(
        conn, garden_id, kind=kind, shape=shape, x=0, y=0, points=points,
        width=7.0 if shape == "line" else None, height=height,
        height_source=height_source, roof_source=roof_source,
    )
    conn.commit()
    return element_id


def neighbour(conn: sqlite3.Connection, garden_id: int,
              points: list[list[float]], height: float = 9.0) -> int:
    """A house as `garden_from_map` inserts it."""
    return add(conn, garden_id, "house", points, height,
               height_source="osm_levels", roof_source="osm")
