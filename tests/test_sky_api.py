"""The sky through the API — Wave 26, feature 3 (doc 118).

A light map now says, beside each cell's hours, how much of the sky it sees,
its light as a share of open ground's, and the sunshine to expect with the
climate's cloud; a bed says the same of itself; and the DWD is thanked on the
page once it can show a number the climate went into, and not before.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

#: A bed straight north of a tall wall, and one well clear of it to the south.
NORTH = {"name": "Nord", "polygon": [[0, 1], [6, 1], [6, 3], [0, 3]],
         "soil_type": "loam", "moisture": "fresh"}
SOUTH = {"name": "Süd", "polygon": [[0, -16], [6, -16], [6, -14], [0, -14]],
         "soil_type": "loam", "moisture": "fresh"}
WALL = {"kind": "wall", "x": 3.0, "y": 0.0, "shape": "rect",
        "width": 12.0, "depth": 0.4, "height": 4.0}


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _garden(client: TestClient) -> str:
    token: str = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 51.25, "longitude": 7.15}
    ).json()["share_token"]
    for bed in (NORTH, SOUTH):
        client.post(f"/api/v1/gardens/{token}/beds", json=bed)
    client.post(f"/api/v1/gardens/{token}/obstacles", json=WALL)
    return token


def test_the_map_says_of_every_cell_its_sky_its_light_and_its_sunshine(
        client: TestClient) -> None:
    token = _garden(client)
    body = client.post(f"/api/v1/gardens/{token}/light").json()

    cells = body["cols"] * body["rows"]
    for name in ("sky", "relative", "expected"):
        assert len(body[name]) == cells, name
    assert all(0.0 <= s <= 1.0 for s in body["sky"])
    assert all(0.0 <= r <= 1.0 + 1e-9 for r in body["relative"])
    # Cloud never adds sunshine: what to expect is at most what the geometry allows.
    assert all(e <= h + 1e-9 for e, h in zip(body["expected"], body["hours"], strict=True))
    assert min(body["relative"]) < 0.8 < max(body["relative"])


def test_a_bed_says_its_sky_its_light_and_its_sunshine(client: TestClient) -> None:
    token = _garden(client)
    client.post(f"/api/v1/gardens/{token}/light")
    beds = {b["name"]: b for b in client.get(f"/api/v1/gardens/{token}").json()["beds"]}

    north, south = beds["Nord"], beds["Süd"]
    for bed in (north, south):
        assert 0.0 < bed["sky_view"] <= 1.0
        assert 0.0 < bed["relative_light"] <= 1.0 + 1e-9
        assert 0.0 < bed["expected_sun_h"] <= bed["sun_hours"] + 1e-9
    assert north["relative_light"] < south["relative_light"]
    assert north["sky_view"] < south["sky_view"]
    # The wall takes the north bed's sun far more than its light: the sky still reaches it.
    assert north["relative_light"] > north["sun_hours"] / south["sun_hours"]


def test_every_bed_is_matched_by_the_light_value_its_hours_and_sky_give(
        client: TestClient) -> None:
    """The owner's rule of 2026-09-22 (doc 118), as stored: the hours'
    convention, floored by the sky in leaf — so the value can always be
    worked back from the two numbers beside it."""
    from ninanatur.solar.light import light_value

    token = _garden(client)
    client.post(f"/api/v1/gardens/{token}/light")
    for bed in client.get(f"/api/v1/gardens/{token}").json()["beds"]:
        assert bed["ellenberg_l"] == light_value(bed["sun_hours"], bed["sky_view"])


def test_under_a_drawn_tree_the_value_stays_at_the_hours_floor(client: TestClient) -> None:
    """A drawn tree is still an opaque prism from the ground (until feature 6):
    inside it hours and sky both read 0, and the sky's floor took the bed to
    0.0 where the hours had always held it at 2.5 (review, 2026-09-22)."""
    token: str = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 51.25, "longitude": 7.15}
    ).json()["share_token"]
    client.post(f"/api/v1/gardens/{token}/obstacles", json={
        "kind": "tree", "x": 0.0, "y": 0.0, "shape": "circle", "width": 8.0, "height": 10.0})
    client.post(f"/api/v1/gardens/{token}/beds", json={
        "name": "Baumscheibe", "polygon": [[-1.5, -1.5], [1.5, -1.5], [1.5, 1.5], [-1.5, 1.5]],
        "soil_type": "loam", "moisture": "fresh"})
    client.post(f"/api/v1/gardens/{token}/light")
    [bed] = client.get(f"/api/v1/gardens/{token}").json()["beds"]
    assert bed["sun_hours"] == 0.0 and bed["sky_view"] == 0.0
    assert bed["ellenberg_l"] == 2.5


def test_a_bed_stores_its_cells_means_each_under_its_own_name(client: TestClient) -> None:
    """Swapping the sky and the relative light between the columns passed every
    range and ordering check (review, 2026-09-22): each is its cells' mean of
    its own list, and one served cell is what the model says of that spot."""
    from ninanatur.garden.lightgrid_store import load_grid
    from ninanatur.garden.lightview import shading_obstacles
    from ninanatur.garden.store import load_garden
    from ninanatur.solar.climate import climate_at
    from ninanatur.solar.position import Location
    from ninanatur.solar.raster import moments_for, parts_of
    from ninanatur.solar.relative import point_sky_light

    token = _garden(client)
    body = client.post(f"/api/v1/gardens/{token}/light").json()
    conn: sqlite3.Connection = app.dependency_overrides[get_connection]()
    garden_id = conn.execute("SELECT garden_id FROM garden WHERE share_token = ?",
                             (token,)).fetchone()[0]
    stored = load_grid(conn, garden_id)
    assert stored is not None
    grid = stored[0]
    for bed in client.get(f"/api/v1/gardens/{token}").json()["beds"]:
        for column, values, digits in (("sky_view", grid.sky, 3),
                                       ("relative_light", grid.relative, 3),
                                       ("expected_sun_h", grid.expected, 2)):
            mean = grid.mean_over(bed["polygon"], values)
            assert mean is not None and bed[column] == round(mean, digits), column
    garden = load_garden(conn, garden_id)
    parts = parts_of(shading_obstacles(conn, garden))
    col, row = body["cols"] // 2, body["rows"] // 3
    x, y = grid.centre_of(col, row)
    spot = point_sky_light(parts, moments_for(Location(51.25, 7.15)), climate_at(51.25, 7.15),
                           x, y)
    index = row * body["cols"] + col
    assert body["sky"][index] == pytest.approx(float(spot.sky[0]), abs=6e-4)
    assert body["relative"][index] == pytest.approx(float(spot.relative[0]), abs=6e-4)
    assert body["expected"][index] == pytest.approx(float(spot.expected[0]), abs=0.006)


def test_the_dwd_is_thanked_once_a_map_rests_on_its_climate(client: TestClient) -> None:
    token = _garden(client)
    before = client.get(f"/api/v1/gardens/{token}/sources").json()
    assert all(c["about"] != "climate" for c in before)

    client.post(f"/api/v1/gardens/{token}/light")
    [climate] = [c for c in client.get(f"/api/v1/gardens/{token}/sources").json()
                 if c["about"] == "climate"]
    assert climate["licence"] == "CC-BY-4.0"
    assert climate["licence_url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert climate["attribution"].startswith("Datenbasis: Deutscher Wetterdienst")


def test_a_map_from_before_the_sky_counted_loads_and_its_months_are_credited(
        client: TestClient) -> None:
    """What a volume holds after the upgrade until somebody recomputes: the
    new columns at their default. The season's map loads and says no sky; a
    month's map is computed on the spot with the climate in it, so the DWD is
    thanked all the same — once it was not, under its own numbers (review,
    2026-09-22)."""
    token = _garden(client)
    client.post(f"/api/v1/gardens/{token}/light")
    conn: sqlite3.Connection = app.dependency_overrides[get_connection]()
    conn.execute("UPDATE light_grid SET sky = '[]', relative = '[]', expected = '[]'")

    season = client.get(f"/api/v1/gardens/{token}/light").json()
    assert season["sky"] == season["relative"] == season["expected"] == []
    assert len(season["hours"]) == season["cols"] * season["rows"]
    june = client.get(f"/api/v1/gardens/{token}/light", params={"month": 6}).json()
    assert len(june["expected"]) == june["cols"] * june["rows"]
    sources = client.get(f"/api/v1/gardens/{token}/sources").json()
    assert [c["about"] for c in sources] == ["climate"]
