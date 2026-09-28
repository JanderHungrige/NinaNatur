"""Where the laser saw a crown start — doc 121, and its review of 2026-09-28.

A laser window is shared by every garden in its place and drawn on the axes
of the garden that read it; its crown bases are only a tree's where a building
model told the roofs from the crowns. Both were true of Wave 25's windows and
neither mattered, because nothing read the crown bases until doc 121.
"""
from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.garden import cloud_sync
from ninanatur.garden.canopies_found import remember
from ninanatur.garden.cloud_sync import crown_base_under, ensure_cloud, fill_crown_bases
from ninanatur.garden.models import Garden
from ninanatur.garden.store import garden_by_token
from ninanatur.geo.canopy import Canopy
from ninanatur.geo.cloud_store import save_cloud, stored_cloud
from ninanatur.geo.pointcloud import CloudWindow
from ninanatur.geo.projection import LatLon, to_metres
from ninanatur.geo.terrain_store import cache_key
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

#: Two gardens 53 m apart that share a place key (review, 2026-09-28).
HOME = LatLon(51.2562, 7.1508)
NEXT_DOOR = LatLon(51.2558, 7.1512)


def _cloud(crowns: list[tuple[float, float, float]], cols: int = 240) -> CloudWindow:
    """A window of metre cells on its reader's axes, a crown base within 3 m
    of each (x, y, base) and nothing elsewhere."""
    reach = cols / 2
    bases = []
    for row in range(cols):
        for col in range(cols):
            x, y = -reach + col + 0.5, -reach + row + 0.5
            found = [b for cx, cy, b in crowns if math.hypot(x - cx, y - cy) <= 3.0]
            bases.append(found[0] if found else math.nan)
    return CloudWindow(min_x=-reach, min_y=-reach, cell_m=1.0, cols=cols, rows=cols,
                       ground=[150.0] * cols * cols, surface=[150.0] * cols * cols,
                       crown_base=bases, source="NW", licence="dl-de/zero-2-0",
                       attribution="Geobasis NRW", points_per_m2=20.0)


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


def _garden(client: TestClient, at: LatLon) -> str:
    token: str = client.post("/api/v1/gardens", json={
        "name": "G", "latitude": at.lat, "longitude": at.lon}).json()["share_token"]
    return token


def _accept(client: TestClient, conn: sqlite3.Connection, token: str,
            x: float = 8.0, y: float = -6.0) -> dict[str, Any]:
    garden = garden_by_token(conn, token)
    assert garden is not None
    remember(conn, garden.garden_id, [Canopy(x=x, y=y, radius_m=4.0, height_m=18.0)])
    first = client.get(f"/api/v1/gardens/{token}/canopies").json()[0]
    body = client.post(f"/api/v1/gardens/{token}/canopies/{first['suggestion_id']}").json()
    tree: dict[str, Any] = next(o for o in body["obstacles"] if o["kind"] == "tree")
    return tree


def test_a_tree_taken_from_the_laser_starts_where_the_laser_saw_it_start(
    conn: sqlite3.Connection,
) -> None:
    client = TestClient(app)
    token = _garden(client, HOME)
    save_cloud(conn, cache_key(HOME), _cloud([(8.0, -6.0, 4.2)]), HOME, classified=True)

    tree = _accept(client, conn, token)

    assert (tree["crown_base_m"], tree["crown_base_source"]) == (4.2, "measured")
    assert tree["height_source"] == "measured"


def test_without_a_point_cloud_the_base_is_nobodys(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    tree = _accept(client, conn, _garden(client, HOME))

    assert (tree["crown_base_m"], tree["crown_base_source"]) == (None, None)
    assert tree["height_source"] == "measured", "the height is still the laser's"


def test_a_window_no_building_model_classified_gives_no_base(conn: sqlite3.Connection) -> None:
    """Without one, a roof's lowest returns read as a crown's (doc 107)."""
    client = TestClient(app)
    token = _garden(client, HOME)
    save_cloud(conn, cache_key(HOME), _cloud([(8.0, -6.0, 4.2)]), HOME, classified=False)

    assert _accept(client, conn, token)["crown_base_m"] is None


def test_a_garden_sharing_its_place_reads_the_laser_under_its_own_tree(
    conn: sqlite3.Connection,
) -> None:
    """The window was read around the first garden. The second, 53 m away,
    read it on its own axes and took the first garden's tree for its own."""
    assert cache_key(HOME) == cache_key(NEXT_DOOR)
    client = TestClient(app)
    token = _garden(client, NEXT_DOOR)
    # Next door's tree at its own (8, −6) stands here, on the first garden's axes.
    offset = to_metres(NEXT_DOOR, HOME)
    theirs = (8.0 + offset.x, -6.0 + offset.y, 9.0)
    save_cloud(conn, cache_key(HOME), _cloud([(8.0, -6.0, 4.2), theirs]), HOME,
               classified=True)

    assert _accept(client, conn, token)["crown_base_m"] == 9.0


def test_a_window_stored_without_its_anchor_gives_no_base(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token = _garden(client, HOME)
    save_cloud(conn, cache_key(HOME), _cloud([(8.0, -6.0, 4.2)]), None, classified=True)

    assert _accept(client, conn, token)["crown_base_m"] is None


def _cells(values: dict[tuple[float, float], float], cols: int = 20) -> CloudWindow:
    """A window of metre cells holding these crown bases, by cell centre."""
    window = _cloud([], cols=cols)
    bases = list(window.crown_base)
    for (x, y), base in values.items():
        bases[int(y - window.min_y) * cols + int(x - window.min_x)] = base
    return CloudWindow(**{**vars(window), "crown_base": bases})


def test_a_drawn_house_is_no_crown() -> None:
    """Part of the crown's middle lies over a roof the survey's model did not
    know, and the laser reads a roof as a crown; its cells are left out."""
    window = _cells({(x + 0.5, y + 0.5): (2.9 if x < 0 else 7.0)
                     for x in range(-3, 3) for y in range(-3, 3)})
    house = [[(-0.25, -5.0), (5.0, -5.0), (5.0, 5.0), (-0.25, 5.0)]]

    assert crown_base_under(window, 0.0, 0.0, 4.0) == 7.0, "over the roof, the roof counts"
    assert crown_base_under(window, 0.0, 0.0, 4.0, house) == 2.9


def test_the_base_is_read_over_the_crowns_middle_not_its_rim() -> None:
    """Nearer the rim, the lowest leaves of a round crown are its side: its
    cells read higher than the base, and there are more of them."""
    window = _cells({(x + 0.5, y + 0.5): (3.0 if math.hypot(x + 0.5, y + 0.5) <= 2.6 else 8.0)
                     for x in range(-5, 5) for y in range(-5, 5)
                     if math.hypot(x + 0.5, y + 0.5) <= 4.6})

    assert crown_base_under(window, 0.0, 0.0, 4.0) == 3.0


def test_a_garden_whose_place_is_not_precise_reads_no_laser(conn: sqlite3.Connection) -> None:
    """Gardens made before 2026-09-07 sit on a 0.1° grid, kilometres from
    their ground; the laser there is somebody else's (`terrain_sync.is_precise`)."""
    rounded = LatLon(51.2, 7.1)
    client = TestClient(app)
    token = _garden(client, rounded)
    client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "tree", "shape": "circle", "x": 0.0, "y": 0.0, "width": 6, "height": 12})
    save_cloud(conn, cache_key(rounded), _cloud([(0.0, 0.0, 3.4)]), rounded, classified=True)
    garden = garden_by_token(conn, token)
    assert garden is not None

    assert fill_crown_bases(conn, garden) == 0


def test_the_measured_base_is_kept_to_the_centimetre() -> None:
    """The median of 2.9 and 3.05 was stored as 2.9749999999999996, and the
    form showed it so (review, 2026-09-28)."""
    window = _cells({(0.5, 0.5): 3.05, (-0.5, 0.5): 2.9})

    assert crown_base_under(window, 0.0, 0.0, 2.0) == 2.97


def test_the_laser_fills_every_tree_nobody_has_spoken_for(conn: sqlite3.Connection) -> None:
    """Drawn trees too, and on the light's path: the plan's crown base comes
    from the point cloud where there is one. A typed base is the gardener's;
    an emptied one is nobody's again, and the laser may answer it (doc 93's
    rule for eaves). A shrub starts at the ground."""
    client = TestClient(app)
    token = _garden(client, HOME)
    save_cloud(conn, cache_key(HOME), _cloud([(0.0, 0.0, 3.4), (20.0, 0.0, 5.0),
                                              (0.0, 20.0, 1.2)]), HOME, classified=True)
    made = []
    for kind, x, y in (("tree", 0.0, 0.0), ("tree", 20.0, 0.0), ("shrub", 0.0, 20.0)):
        body = client.post(f"/api/v1/gardens/{token}/obstacles", json={
            "kind": kind, "shape": "circle", "x": x, "y": y, "width": 6, "height": 12}).json()
        made.append(body["obstacles"][-1]["obstacle_id"])
    drawn, typed, shrub = made
    client.patch(f"/api/v1/gardens/{token}/obstacles/{typed}", json={"crown_base_m": 2.0})

    client.post(f"/api/v1/gardens/{token}/light")

    def base(element: int) -> tuple[Any, Any]:
        found = next(o for o in client.get(f"/api/v1/gardens/{token}").json()["obstacles"]
                     if o["obstacle_id"] == element)
        return found["crown_base_m"], found["crown_base_source"]

    assert base(drawn) == (3.4, "measured")
    assert base(typed) == (2.0, "user")
    assert base(shrub) == (None, None)
    client.patch(f"/api/v1/gardens/{token}/obstacles/{drawn}", json={"crown_base_m": None})
    garden = garden_by_token(conn, token)
    assert garden is not None
    assert fill_crown_bases(conn, garden) == 1
    assert base(drawn) == (3.4, "measured")


def _reads(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Which reads of the laser happened, each by whether it had buildings."""
    reads: list[bool] = []

    def read(anchor: LatLon, source: object, buildings: list[object]) -> CloudWindow:
        reads.append(bool(buildings))
        return _cloud([], cols=20)

    monkeypatch.setattr(cloud_sync, "state_at", lambda *_a: "Nordrhein-Westfalen")
    monkeypatch.setattr(cloud_sync, "_read", read)
    return reads


def test_a_window_is_read_again_until_it_is_anchored_and_classified(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    reads = _reads(monkeypatch)
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="G", latitude=HOME.lat,
                    longitude=HOME.lon, created_at="", updated_at="")
    key = cache_key(HOME)
    save_cloud(conn, key, _cloud([], cols=20))  # as Wave 25 stored them

    assert ensure_cloud(conn, garden) is True
    assert reads == [False], "without its anchor, read again"
    assert ensure_cloud(conn, garden) is True
    assert reads == [False], "anchored, and no building model to classify it with"
    assert ensure_cloud(conn, garden, buildings=[object()]) is True  # type: ignore[list-item]
    assert reads == [False, True], "a building model arrived"
    assert ensure_cloud(conn, garden, buildings=[object()]) is True  # type: ignore[list-item]
    assert reads == [False, True]
    stored = stored_cloud(conn, key)
    assert stored is not None and stored.anchored and stored.classified
