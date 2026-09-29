"""The light model has a version, and every map says which drew it (doc 117).

Wave 26 changes what the model answers six times. A map stored by one model
and shown after the next would put an old answer under a new model's page,
with nothing to say so. The version enters the signature — the map reads
stale — and travels with the map to the page.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.garden import lightgrid_extent
from ninanatur.garden.lightgrid import signature_of
from ninanatur.garden.store import load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.migrations import apply_column_migrations
from ninanatur.solar import light
from ninanatur.web.app import app


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    app.dependency_overrides[get_connection] = lambda: made
    yield made
    app.dependency_overrides.clear()


def _drawn(client: TestClient, *, with_wall: bool = True) -> str:
    token = str(client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.52, "longitude": 13.40}).json()["share_token"])
    client.post(f"/api/v1/gardens/{token}/beds", json={
        "name": "Beet", "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]]})
    if with_wall:
        client.post(f"/api/v1/gardens/{token}/obstacles", json={
            "kind": "wall", "x": 2.0, "y": -2.0, "shape": "rect", "width": 6.0, "depth": 0.3,
            "height": 2.5})
    return token


def test_a_map_is_served_with_the_model_that_drew_it(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token = _drawn(client)
    drawn = client.post(f"/api/v1/gardens/{token}/light").json()
    assert drawn["model"] == light.MODEL_VERSION
    assert client.get(f"/api/v1/gardens/{token}/light").json()["model"] == light.MODEL_VERSION


def test_a_map_another_model_drew_reads_stale(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)
    token = _drawn(client)
    client.post(f"/api/v1/gardens/{token}/light")
    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is False
    monkeypatch.setattr(light, "MODEL_VERSION", light.MODEL_VERSION + ".next")
    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is True


def test_the_version_is_part_of_the_signature(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)
    token = _drawn(client)
    garden_id = int(conn.execute("SELECT garden_id FROM garden WHERE share_token = ?",
                                 (token,)).fetchone()[0])
    before = signature_of(load_garden(conn, garden_id))
    monkeypatch.setattr(light, "MODEL_VERSION", "0.0")
    assert f"model {light.MODEL_VERSION}" in lightgrid_extent.grid_model()
    assert signature_of(load_garden(conn, garden_id)) != before


def test_a_map_stored_before_versions_says_so() -> None:
    """A database from before Wave 26 gains the column, and its maps an empty
    version: drawn by the model before there were versions."""
    old = sqlite3.connect(":memory:")
    old.row_factory = sqlite3.Row
    old.execute("CREATE TABLE light_grid (garden_id INTEGER PRIMARY KEY, cell_m REAL,"
                " min_x REAL, min_y REAL, cols INTEGER, rows INTEGER, hours TEXT,"
                " morning TEXT, roof TEXT, signature TEXT, computed_at TEXT)")
    old.execute("INSERT INTO light_grid VALUES (1, 1, 0, 0, 1, 1, '[5]', '[]', '[]',"
                " 'sig', '2026-09-01')")
    apply_column_migrations(old)
    assert old.execute("SELECT model FROM light_grid").fetchone()[0] == ""


#: What each version answers in Wuppertal, season: open ground, 6 m behind a
#: 9 m house to the south, and the corner of the plan's L (docs 115, 117, 118)
#: — sun hours, sky seen in leaf, relative illuminance, sunshine to expect and
#: the light value, through the path the app computes them by (`relative`).
#: Change what the model answers and this fails until the version rises and
#: its answers are pinned here — so no map of an older model's reads current.
#: 26.2 answered hours only.
ANSWERS: dict[str, tuple[tuple[float, ...], ...]] = {
    "26.2": ((13.08,), (5.71,), (4.35,)),
    "26.3": ((13.08, 1.0, 1.0, 5.47, 9.0), (5.71, 0.665, 0.569, 2.47, 7.32),
             (4.35, 0.56, 0.451, 1.84, 6.47)),
    # 26.4 weighs the sun by what its beam brings (doc 119): a house to the
    # south takes the noon sun, and the light behind it falls with it.
    "26.4": ((13.08, 1.0, 1.0, 5.47, 9.0), (5.71, 0.665, 0.454, 2.47, 7.32),
             (4.35, 0.56, 0.404, 1.84, 6.47)),
    # 26.5 adds two spots behind the same house with a gable on it (doc 120).
    "26.5": ((13.08, 1.0, 1.0, 5.47, 9.0), (5.71, 0.665, 0.454, 2.47, 7.32),
             (4.35, 0.56, 0.404, 1.84, 6.47), (5.8, 0.731, 0.493, 2.51, 7.38),
             (11.75, 0.933, 0.918, 5.0, 9.0)),
    # 26.6 adds a lime of 12 m, its crown from 4 m (doc 121): at its foot, and
    # 7 m north of it. As a cylinder it answered (4.37, 0.2, 0.313, 1.76,
    # 6.25) at its foot — a crown on a trunk lets all but the high summer sun
    # in beneath it. And two crowns that are not balls: a tree of 15 m whose
    # gardener said its crown starts at 2 m, and a shrub, from the ground.
    "26.6": ((13.08, 1.0, 1.0, 5.47, 9.0), (5.71, 0.665, 0.454, 2.47, 7.32),
             (4.35, 0.56, 0.404, 1.84, 6.47), (5.8, 0.731, 0.493, 2.51, 7.38),
             (11.75, 0.933, 0.918, 5.0, 9.0), (12.98, 0.8, 0.908, 5.42, 9.0),
             (11.77, 0.93, 0.88, 4.9, 9.0), (12.29, 0.958, 0.929, 5.13, 9.0),
             (11.04, 0.883, 0.831, 4.62, 9.0),
             # And the roofs the gable alone left free to change unnoticed
             # (review of feature 5, 2026-09-28): the house hipped, asked
             # beside its western end, and pent, surveyed falling north (its
             # eaves over the spot) and falling south (its top).
             (9.79, 0.901, 0.81, 4.14, 9.0), (5.8, 0.731, 0.493, 2.51, 7.38),
             (5.71, 0.665, 0.454, 2.47, 7.32)),
}
#: 26.2 to 26.4 answered three spots; 26.5 pins roofed ones beside them, and
#: 26.6 a crowned one.
#: The bed of `_drawn`, Berlin, behind its wall: what the app stores for it —
#: the grid's path, end to end.
BED_ANSWERS: dict[str, tuple[float, ...]] = {
    "26.3": (11.6, 0.93, 0.927, 5.6, 9.0),
    "26.4": (11.6, 0.93, 0.911, 5.6, 9.0),
    # The garden's only obstacle is a wall, which no roof changes (doc 120)
    # and no crown (doc 121).
    "26.5": (11.6, 0.93, 0.911, 5.6, 9.0),
    "26.6": (11.6, 0.93, 0.911, 5.6, 9.0),
}
#: A bed 4 m north of a drawn lime of 12 m, Berlin: what the app stores for
#: it, through the crown's own path in the grid (doc 121).
TREE_BED_ANSWERS: dict[str, tuple[float, ...]] = {
    "26.6": (11.73, 0.903, 0.853, 5.5, 9.0),
}
#: A bed 2 m north of a gabled house, Berlin, through the grid's roof path
#: (doc 120) — the bed as stored, then a cell on each pitch: hours, sky,
#: relative light, sunshine to expect. And on ground rising 5 % northwards,
#: the bed's middle cell and the north pitch: hours and sky.
ROOF_ANSWERS: dict[str, tuple[tuple[float, ...], ...]] = {
    "26.6": ((8.78, 0.829, 0.699, 4.29, 9.0), (6.95, 0.789, 0.442, 3.53),
             (11.4, 0.789, 0.959, 5.33), (9.57, 0.848), (6.95, 0.789)),
}
#: How near: hours and values to two places, shares of sky and light to three.
TOLERANCE = (0.02, 0.002, 0.002, 0.02, 0.02)


def _near(got: tuple[float, ...], pinned: tuple[float, ...]) -> bool:
    return all(abs(g - p) <= tol for g, p, tol in zip(got, pinned, TOLERANCE, strict=False))


def test_the_model_answers_what_its_version_says() -> None:
    """The review of 2026-09-22 found this pinned a function nothing in the app
    called any more, and none of the sky's answers: the hour weight and the
    overcast sky could both change unnoticed."""
    from ninanatur.garden.canopy import canopy_of
    from ninanatur.garden.casting import casting
    from ninanatur.garden.lightview import _crown_of
    from ninanatur.garden.models import Element
    from ninanatur.solar.climate import climate_at
    from ninanatur.solar.position import Location
    from ninanatur.solar.raster import moments_for, parts_of
    from ninanatur.solar.relative import point_sky_light
    from ninanatur.solar.shading import Obstacle

    assert light.MODEL_VERSION in ANSWERS, "a new version pins its answers here"
    wuppertal, climate = Location(51.25, 7.15), climate_at(51.25, 7.15)
    moments = moments_for(wuppertal)
    house = [Obstacle(footprint=[(-5, -13), (5, -13), (5, -8), (-5, -8)], height=9.0)]
    ell = [Obstacle(footprint=[(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)],
                    height=9.0)]
    # The same house with the gable it would really have (doc 120), asked 2 m
    # north of it, where the eaves decide, and 7 m north, where the ridge
    # does — at the first alone a roof whose planes were wrong still passed,
    # for it answers as a 5 m block would (review, 2026-09-28).
    gabled = [casting(Element(element_id=1, kind="house", shape="polygon", x=0.0, y=0.0,
                              points=[[-5, -13], [5, -13], [5, -8], [-5, -8]], height=9.0,
                              roof="gable", eaves_m=5.0))]
    # A lime drawn as a circle, through the caster the app uses (doc 121) —
    # its assumed base, its broadleaf shares and all (review, 2026-09-28).
    lime = [casting(Element(element_id=2, kind="tree", shape="circle", x=0.0, y=-8.0,
                            width=8.0, height=12.0))]
    planted = _crown_of(canopy_of(12.0, "tree"), (0.0, -8.0), None)
    assert (planted.crown, planted.transmission, planted.bare_transmission) == (
        lime[0].crown, lime[0].transmission, lime[0].bare_transmission), \
        "planted from the catalogue, the same lime casts the same crown"
    typed = [casting(Element(element_id=3, kind="tree", shape="circle", x=0.0, y=-8.0,
                             width=6.0, height=15.0, crown_base_m=2.0))]
    shrub = [casting(Element(element_id=4, kind="shrub", shape="circle", x=0.0, y=-3.0,
                             width=3.0, height=2.5))]
    roofed = [[casting(Element(element_id=5, kind="house", shape="polygon", x=0.0, y=0.0,
                               points=[[-5, -13], [5, -13], [5, -8], [-5, -8]], height=9.0,
                               roof=roof, eaves_m=5.0, roof_fall_deg=fall))]
              for roof, fall in (("hip", None), ("pent", 0.0), ("pent", 180.0))]
    spots = (([], 0.0, 0.0), (house, 0.0, -6.0), (ell, 7.5, 7.5), (gabled, 0.0, -6.0),
             (gabled, 0.0, -1.0), (lime, 0.0, -8.0), (lime, 0.0, -1.0), (typed, 0.0, -1.0),
             (shrub, 0.0, -1.0), (roofed[0], -6.5, -6.0), (roofed[1], 0.0, -6.0),
             (roofed[2], 0.0, -6.0))
    for (obstacles, x, y), pinned in zip(spots, ANSWERS[light.MODEL_VERSION], strict=True):
        got = point_sky_light(parts_of(obstacles), moments, climate, x, y)
        hours, sky = float(got.morning[0] + got.afternoon[0]), float(got.sky[0])
        answer = (hours, sky, float(got.relative[0]), float(got.expected[0]),
                  light.light_value(round(hours, 2), round(sky, 3)))
        assert _near(answer, pinned), answer


def test_the_app_stores_what_its_version_says(conn: sqlite3.Connection) -> None:
    client = TestClient(app)
    token = _drawn(client)
    client.post(f"/api/v1/gardens/{token}/light")
    bed = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    got = tuple(bed[k] for k in ("sun_hours", "sky_view", "relative_light", "expected_sun_h",
                                 "ellenberg_l"))
    assert _near(got, BED_ANSWERS[light.MODEL_VERSION]), got


def test_the_app_stores_what_its_version_says_under_a_tree(conn: sqlite3.Connection) -> None:
    """The point path pins the crown; this pins the grid's own crown path
    (`raster_grid._shade_crown`) and the caster, end to end."""
    client = TestClient(app)
    token = _drawn(client, with_wall=False)
    client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "tree", "x": 2.0, "y": -4.0, "shape": "circle", "width": 8.0, "height": 12.0})
    client.post(f"/api/v1/gardens/{token}/light")
    bed = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    got = tuple(bed[k] for k in ("sun_hours", "sky_view", "relative_light", "expected_sun_h",
                                 "ellenberg_l"))
    assert light.MODEL_VERSION in TREE_BED_ANSWERS, "a new version pins its answers here"
    assert _near(got, TREE_BED_ANSWERS[light.MODEL_VERSION]), got


def test_the_app_stores_what_its_version_says_behind_a_roof(conn: sqlite3.Connection) -> None:
    """The point path pins the roofs; this pins the grid's roof path — the
    cut in `raster.covered`, the cells on the planes — and the same garden on
    rising ground, where the roof stands on its base (review of feature 5,
    2026-09-28: each could change with the point pins still green)."""
    from ninanatur.garden.lightgrid import compute_grid
    from ninanatur.garden.lightview import shading_obstacles
    from ninanatur.geo.terrain import TerrainWindow

    client = TestClient(app)
    token = _drawn(client, with_wall=False)
    house = client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "house", "x": 2.0, "y": -4.5, "shape": "rect", "width": 10.0, "depth": 5.0,
        "height": 9.0}).json()["obstacles"][-1]["obstacle_id"]
    client.patch(f"/api/v1/gardens/{token}/obstacles/{house}",
                 json={"roof": "gable", "eaves_m": 5.0})
    client.post(f"/api/v1/gardens/{token}/light")
    bed = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    grid = client.get(f"/api/v1/gardens/{token}/light").json()

    def cell(x: float, y: float) -> tuple[float, ...]:
        i = (int((y - grid["min_y"]) // grid["cell_m"]) * grid["cols"]
             + int((x - grid["min_x"]) // grid["cell_m"]))
        assert grid["roof"][i]
        return tuple(grid[k][i] for k in ("hours", "sky", "relative", "expected"))

    assert light.MODEL_VERSION in ROOF_ANSWERS, "a new version pins its answers here"
    pinned = ROOF_ANSWERS[light.MODEL_VERSION]
    stored = tuple(bed[k] for k in ("sun_hours", "sky_view", "relative_light",
                                    "expected_sun_h", "ellenberg_l"))
    assert _near(stored, pinned[0]), stored
    assert _near(cell(2.0, -3.0), pinned[1]) and _near(cell(2.0, -6.0), pinned[2])

    garden_id = int(conn.execute("SELECT garden_id FROM garden WHERE share_token = ?",
                                 (token,)).fetchone()[0])
    garden = load_garden(conn, garden_id)
    rising = TerrainWindow(min_x=-100.0, min_y=-100.0, cell_m=1.0, cols=200, rows=200,
                           heights=[100.0 + (row - 100) * 0.05 for row in range(200)
                                    for _ in range(200)],
                           source="Test", licence="-", attribution="-", vertical_step_m=0.01)
    sloped = compute_grid(garden, shading_obstacles(conn, garden), ground=rising)
    assert sloped is not None

    def sloped_at(x: float, y: float) -> tuple[float, ...]:
        i = (int((y - sloped.min_y) // sloped.cell_m) * sloped.cols
             + int((x - sloped.min_x) // sloped.cell_m))
        return (float(sloped.hours[i] or 0.0), float(sloped.sky[i] or 0.0))

    assert _near(sloped_at(2.0, 1.5), pinned[3]) and _near(sloped_at(2.0, -3.0), pinned[4])
