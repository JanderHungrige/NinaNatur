"""Which casters are crowns, and where a crown starts — doc 121.

A tree or shrub the gardener drew was an opaque block to its top; a planted
one was a cylinder from the ground. Both are crowns on trunks now, and the
base of each is the gardener's word, the laser's reading, or an assumption
that says it is one.
"""
from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.garden.canopy import canopy_of
from ninanatur.garden.casting import casting
from ninanatur.garden.lightview import _crown_of
from ninanatur.garden.models import Element
from ninanatur.ingest.db import connect, init_schema
from ninanatur.solar.crown import Crown
from ninanatur.web.app import app

#: Precise enough for the stored windows to be read (`terrain_sync.is_precise`).
WUPPERTAL = (51.2562, 7.1508)


def _element(kind: str, **fields: Any) -> Element:
    base: dict[str, Any] = {"element_id": 7, "kind": kind, "shape": "circle", "x": 4.0,
                            "y": -3.0, "width": 6.0, "height": 9.0}
    return Element(**(base | fields))


def test_a_drawn_tree_casts_as_a_crown_with_a_broadleafs_shares() -> None:
    cast = casting(_element("tree"))

    assert cast.crown == Crown(x=4.0, y=-3.0, radius=3.0, base=3.0, top=9.0), \
        "a third of its height, assumed"
    assert (cast.transmission, cast.bare_transmission) == (0.20, 0.75)
    assert cast.owner == 7


def test_a_shrub_branches_from_the_ground_and_a_hedge_stays_a_prism() -> None:
    shrub = casting(_element("shrub", width=2.0, height=1.8))
    assert shrub.crown is not None and shrub.crown.base == 0.0

    hedge = casting(_element("hedge", shape="polygon", width=None,
                             points=[[0, 0], [6, 0], [6, 0.6], [0, 0.6]], height=2.0))
    assert hedge.crown is None, "leaves to the ground, not a crown on a trunk"
    assert hedge.transmission == 0.0


def test_the_gardeners_base_is_used_and_kept_inside_the_tree() -> None:
    assert casting(_element("tree", crown_base_m=2.2)).crown == Crown(
        x=4.0, y=-3.0, radius=3.0, base=2.2, top=9.0)
    above = casting(_element("tree", crown_base_m=12.0))
    assert above.crown is not None and above.crown.base == 9.0


def test_a_crown_with_no_depth_still_casts() -> None:
    """A base at the tree's top, which the API takes, left a crown of no
    depth and the light model dividing by it (review, 2026-09-28)."""
    from ninanatur.solar.position import Location
    from ninanatur.solar.raster import moments_for, parts_of, point_hours

    flat = casting(_element("tree", crown_base_m=9.0))
    morning, afternoon = point_hours(parts_of([flat]), moments_for(Location(51.25, 7.15), month=6),
                                     4.0, -8.0)
    hours = float(morning + afternoon)
    assert math.isfinite(hours) and 0.0 < hours < 16.0


def test_a_row_or_an_l_is_no_crown_and_casts_as_itself() -> None:
    """A disc of the same area stood where nothing was drawn: a row of shrubs
    became a ball at its middle that shaded open ground and left the row's
    own side lit (review, 2026-09-28). An outline no crown fits casts as the
    outline, passing a crown's share wherever a ray meets it."""
    row = casting(_element("shrub", shape="line", width=1.0, height=2.0,
                           points=[[-10, 0], [10, 0]]))
    ell = casting(_element("tree", shape="polygon", width=None,
                           points=[[0, 0], [8, 0], [8, 1], [1, 1], [1, 8], [0, 8]]))
    # A band drawn as an outline: its middle is inside it, its ends 2.2 times
    # as far out as a circle of its area reaches.
    band = casting(_element("shrub", shape="polygon", width=None,
                            points=[[0, 0], [6, 0], [6, 1], [0, 1]]))
    for cast in (row, ell, band):
        assert cast.crown is None
        assert (cast.transmission, cast.bare_transmission) == (0.20, 0.75)
    oblong = casting(_element("tree", shape="polygon", width=None,
                              points=[[0, 0], [4, 0], [4, 2], [0, 2]]))
    assert oblong.crown is not None, "a 2:1 outline is still one crown"


def test_a_tree_drawn_as_an_outline_holds_the_leaves_it_was_drawn_with() -> None:
    # An outline's corners are measured from the element's own position.
    square = casting(_element("tree", shape="polygon", width=None,
                              points=[[8, 8], [12, 8], [12, 12], [8, 12]]))

    assert square.crown is not None
    assert (square.crown.x, square.crown.y) == pytest.approx((4.0 + 10.0, -3.0 + 10.0))
    assert square.crown.radius == pytest.approx(math.sqrt(16 / math.pi))


def test_an_outline_stands_its_crown_on_its_centre_of_area() -> None:
    """Not on the mean of its corners: three more corners along one edge
    would pull that towards the edge."""
    uneven = casting(_element("tree", shape="polygon", width=None,
                              points=[[0, 0], [4, 0], [4, 4], [3, 4], [2, 4], [1, 4], [0, 4]]))

    assert uneven.crown is not None
    assert (uneven.crown.x, uneven.crown.y) == pytest.approx((4.0 + 2.0, -3.0 + 2.0))


def test_a_planted_tree_stands_on_a_trunk_and_a_planted_shrub_does_not() -> None:
    tree = canopy_of(15.0, "tree")
    shrub = canopy_of(3.0, "shrub")
    assert tree is not None and shrub is not None
    assert (tree.base_m, shrub.base_m) == (5.0, 0.0)

    crown = _crown_of(tree, (2.0, 1.0), "deciduous").crown
    assert crown == Crown(x=2.0, y=1.0, radius=5.0, base=5.0, top=15.0)


# --- through the API ----------------------------------------------------------


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    yield connection


@pytest.fixture()
def client(conn: sqlite3.Connection) -> Iterator[TestClient]:
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _garden_with_a_tree(client: TestClient) -> tuple[str, int]:
    token = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": WUPPERTAL[0], "longitude": WUPPERTAL[1]}).json()["share_token"]
    body = client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "tree", "shape": "circle", "x": 0, "y": 0, "width": 6, "height": 9}).json()
    return token, int(body["obstacles"][-1]["obstacle_id"])


def _patch(client: TestClient, token: str, element: int, **fields: Any) -> dict[str, Any]:
    body = client.patch(f"/api/v1/gardens/{token}/obstacles/{element}", json=fields).json()
    found: dict[str, Any] = next(o for o in body["obstacles"] if o["obstacle_id"] == element)
    return found


def test_a_typed_crown_base_is_the_gardeners_and_emptying_it_is_nobodys(
    client: TestClient,
) -> None:
    token, tree = _garden_with_a_tree(client)
    drawn = _patch(client, token, tree, label="Linde")
    assert (drawn["crown_base_m"], drawn["crown_base_source"]) == (None, None)

    typed = _patch(client, token, tree, crown_base_m=2.5, crown_base_source="measured")
    assert (typed["crown_base_m"], typed["crown_base_source"]) == (2.5, "user"), \
        "the server says whose it is, never the client"

    renamed = _patch(client, token, tree, label="Die Linde")
    assert renamed["crown_base_source"] == "user", "a rename says nothing about the crown"

    emptied = _patch(client, token, tree, crown_base_m=None)
    assert (emptied["crown_base_m"], emptied["crown_base_source"]) == (None, None)


def test_a_changed_crown_base_makes_the_map_stale(client: TestClient,
                                                  conn: sqlite3.Connection) -> None:
    from ninanatur.garden.lightgrid import signature_of
    from ninanatur.garden.store import garden_by_token

    token, tree = _garden_with_a_tree(client)
    garden = garden_by_token(conn, token)
    assert garden is not None
    before = signature_of(garden)
    _patch(client, token, tree, crown_base_m=4.0)
    after = garden_by_token(conn, token)
    assert after is not None and signature_of(after) != before


def test_the_page_is_told_where_no_crown_fits_and_a_base_would_change_nothing(
    client: TestClient,
) -> None:
    """A tree drawn as a long band casts as the solid a row is, from the
    ground: the form asked for its crown base anyway, and a base typed there
    changed nothing (review of stage 3, 2026-09-28). The answer says which
    outlines a crown fits — of every kind, so a hedge drawn as a line that
    the form turns into a tree is known to be none (review of 45eb56a)."""
    token, tree = _garden_with_a_tree(client)
    assert _patch(client, token, tree, label="Linde")["crown_fits"] is True
    band = _patch(client, token, tree, shape="polygon",
                  points=[[0, 0], [12, 0], [12, 1], [0, 1]])
    assert band["crown_fits"] is False
    hedge = client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "hedge", "shape": "line", "x": 20, "y": 0, "width": 1,
        "points": [[0, 0], [10, 0]], "height": 2}).json()["obstacles"][-1]
    assert hedge["crown_fits"] is False
