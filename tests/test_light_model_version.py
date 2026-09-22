"""The light model has a version, and every map says which drew it (doc 117).

Wave 26 changes what the model answers five times. A map stored by one model
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


def _drawn(client: TestClient) -> str:
    token = str(client.post("/api/v1/gardens", json={
        "name": "G", "latitude": 52.52, "longitude": 13.40}).json()["share_token"])
    client.post(f"/api/v1/gardens/{token}/beds", json={
        "name": "Beet", "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]]})
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
}
#: The bed of `_drawn`, Berlin, behind its wall: what the app stores for it —
#: the grid's path, end to end.
BED_ANSWERS: dict[str, tuple[float, ...]] = {
    "26.3": (11.6, 0.93, 0.927, 5.6, 9.0),
    "26.4": (11.6, 0.93, 0.911, 5.6, 9.0),
}
#: How near: hours and values to two places, shares of sky and light to three.
TOLERANCE = (0.02, 0.002, 0.002, 0.02, 0.02)


def _near(got: tuple[float, ...], pinned: tuple[float, ...]) -> bool:
    return all(abs(g - p) <= tol for g, p, tol in zip(got, pinned, TOLERANCE, strict=False))


def test_the_model_answers_what_its_version_says() -> None:
    """The review of 2026-09-22 found this pinned a function nothing in the app
    called any more, and none of the sky's answers: the hour weight and the
    overcast sky could both change unnoticed."""
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
    for (obstacles, x, y), pinned in zip((([], 0.0, 0.0), (house, 0.0, -6.0), (ell, 7.5, 7.5)),
                                         ANSWERS[light.MODEL_VERSION], strict=True):
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
