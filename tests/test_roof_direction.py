"""The ridge the survey saw, carried through to the roof and its light (doc 94).

The house in most of these is the turned case: eight metres east-west and twelve
north-south, so the long-axis assumption runs its ridge north-south — and the
survey says it runs east-west, as it does on two thirds of city gables.
"""
from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from geokachel.utm import to_latlon, to_utm

from ninanatur.api.deps import get_connection
from ninanatur.garden.elements import insert_element
from ninanatur.garden.lightgrid import LightGrid, compute_grid, signature_of
from ninanatur.garden.lightview import shading_obstacles
from ninanatur.garden.measured import apply, measure
from ninanatur.garden.models import PLANTING_KIND, Garden, ObstacleInput
from ninanatur.garden.roofs import Roof
from ninanatur.garden.roofshape import surface_of
from ninanatur.garden.store import add_obstacle, create_garden, garden_by_token, load_garden
from ninanatur.geo.lod2 import Lod2Building, buildings_from, in_garden_frame
from ninanatur.geo.projection import LatLon, to_metres
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

TURNED = [(-4.0, -6.0), (4.0, -6.0), (4.0, 6.0), (-4.0, 6.0)]
WUPPERTAL = LatLon(lat=51.2564, lon=7.1501)


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


# --- the surface --------------------------------------------------------------------

def test_a_surveyed_ridge_turns_the_pitches() -> None:
    assumed = surface_of(TURNED, Roof.GABLE, 9.0, 6.0)
    surveyed = surface_of(TURNED, Roof.GABLE, 9.0, 6.0, fall_deg=0.0)
    assert assumed is not None and surveyed is not None
    # Assumed: the ridge runs north-south, so the north end is a gable wall
    # and a point east of the middle climbs west.
    assert assumed.slope_aspect_at(2.0, 0.0)[1] == pytest.approx(270.0)
    # Surveyed: the ridge runs east-west, and the north pitch climbs south.
    assert surveyed.slope_aspect_at(0.0, 3.0)[1] == pytest.approx(180.0)
    assert surveyed.slope_aspect_at(0.0, -3.0)[1] == pytest.approx(0.0)


def test_the_pitch_is_measured_across_the_surveyed_ridge() -> None:
    assumed = surface_of(TURNED, Roof.GABLE, 9.0, 6.0)
    surveyed = surface_of(TURNED, Roof.GABLE, 9.0, 6.0, fall_deg=0.0)
    assert assumed is not None and surveyed is not None
    assert assumed.pitch_deg == pytest.approx(math.degrees(math.atan(3 / 4)))
    assert surveyed.pitch_deg == pytest.approx(math.degrees(math.atan(3 / 6)))


def test_a_hip_across_the_short_side_comes_to_a_point() -> None:
    surface = surface_of(TURNED, Roof.HIP, 9.0, 6.0, fall_deg=0.0)
    assert surface is not None
    assert surface.ridge[0] == pytest.approx(surface.ridge[1])


def test_a_pent_with_a_known_fall_is_one_slope() -> None:
    shed = [(-4.0, -3.0), (4.0, -3.0), (4.0, 3.0), (-4.0, 3.0)]
    surface = surface_of(shed, Roof.PENT, 5.0, 3.0, fall_deg=0.0)
    assert surface is not None
    assert surface.height_at(0.0, -3.0) == pytest.approx(5.0)
    assert surface.height_at(0.0, 0.0) == pytest.approx(4.0)
    assert surface.height_at(0.0, 3.0) == pytest.approx(3.0)
    slope, aspect = surface.slope_aspect_at(1.0, 0.0)
    assert slope == pytest.approx(math.degrees(math.atan(2 / 6)))
    assert aspect == pytest.approx(180.0)


# --- the survey --------------------------------------------------------------------

def _survey_face(points: list[tuple[float, float, float]]) -> str:
    flat = " ".join(f"{x} {y} {z}" for x, y, z in points)
    return (
        "<bldg:boundedBy><bldg:RoofSurface><bldg:lod2MultiSurface><gml:MultiSurface>"
        "<gml:surfaceMember><gml:Polygon><gml:exterior><gml:LinearRing>"
        f"<gml:posList>{flat}</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>"
        "</gml:surfaceMember></gml:MultiSurface></bldg:lod2MultiSurface></bldg:RoofSurface>"
        "</bldg:boundedBy>"
    )


def test_the_survey_reads_the_fall_and_turns_it_onto_true_north() -> None:
    """Faces falling grid north and south. The UTM grid and true north differ
    by about 1.4° at Wuppertal, and the fall is turned the way the outline is."""
    e, n = to_utm(WUPPERTAL.lat, WUPPERTAL.lon, 32)
    ground = [(e, n, 100.0), (e + 12, n, 100.0), (e + 12, n + 8, 100.0), (e, n + 8, 100.0),
              (e, n, 100.0)]
    south = [(e, n, 106.0), (e + 12, n, 106.0), (e + 12, n + 4, 109.0), (e, n + 4, 109.0),
             (e, n, 106.0)]
    north = [(e, n + 4, 109.0), (e + 12, n + 4, 109.0), (e + 12, n + 8, 106.0), (e, n + 8, 106.0),
             (e, n + 4, 109.0)]
    flat = " ".join(f"{x} {y} {z}" for x, y, z in ground)
    document = (
        '<core:CityModel xmlns:core="http://www.opengis.net/citygml/1.0" '
        'xmlns:bldg="http://www.opengis.net/citygml/building/1.0" '
        'xmlns:gml="http://www.opengis.net/gml"><bldg:Building gml:id="DE_R">'
        "<bldg:roofType>3100</bldg:roofType><bldg:measuredHeight>9.0</bldg:measuredHeight>"
        "<bldg:boundedBy><bldg:GroundSurface><bldg:lod2MultiSurface><gml:MultiSurface>"
        "<gml:surfaceMember><gml:Polygon><gml:exterior><gml:LinearRing>"
        f"<gml:posList>{flat}</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>"
        "</gml:surfaceMember></gml:MultiSurface></bldg:lod2MultiSurface></bldg:GroundSurface>"
        "</bldg:boundedBy>" + _survey_face(south) + _survey_face(north)
        + "</bldg:Building></core:CityModel>"
    )
    [building] = buildings_from(document.encode())
    assert building.fall_deg is not None and building.fall_deg == pytest.approx(0.0, abs=0.01)

    [moved] = in_garden_frame([building], WUPPERTAL, 32)
    here, ahead = (to_metres(LatLon(*to_latlon(e, n + d, 32)), WUPPERTAL) for d in (0, 10))
    grid_north = math.degrees(math.atan2(ahead.x - here.x, ahead.y - here.y)) % 180
    assert moved.fall_deg is not None
    assert moved.fall_deg == pytest.approx(grid_north, abs=0.01)
    assert min(moved.fall_deg, 180 - moved.fall_deg) > 0.5


def _imported(conn: sqlite3.Connection) -> tuple[Garden, int]:
    garden_id = create_garden(conn, name="G", latitude=WUPPERTAL.lat, longitude=WUPPERTAL.lon)
    house = insert_element(conn, garden_id, kind="house", shape="polygon", x=0.0, y=0.0,
                           points=[list(p) for p in TURNED], height=9.0)
    conn.execute("UPDATE element SET height_source = 'osm_levels', roof_source = 'osm'"
                 " WHERE element_id = ?", (house,))
    conn.commit()
    return load_garden(conn, garden_id), house


def _surveyed(fall: float | None) -> Lod2Building:
    return Lod2Building(building_id="DE_T", roof=Roof.GABLE, height_m=9.0, eaves_m=6.0,
                        outline=list(TURNED), fall_deg=fall)


def _stored_fall(conn: sqlite3.Connection, element_id: int) -> float | None:
    row = conn.execute("SELECT roof_fall_deg FROM element WHERE element_id = ?",
                       (element_id,)).fetchone()
    return None if row[0] is None else float(row[0])


def test_the_survey_writes_the_fall_with_the_shape(conn: sqlite3.Connection) -> None:
    garden, house = _imported(conn)
    apply(conn, measure(garden, [_surveyed(0.0)], None))
    assert _stored_fall(conn, house) == pytest.approx(0.0)


def test_a_chosen_shape_keeps_the_survey_out_of_its_direction_too(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    garden, house = _imported(conn)
    apply(conn, measure(garden, [_surveyed(0.0)], None))
    token = garden.share_token
    client.patch(f"/api/v1/gardens/{token}/obstacles/{house}", json={"roof": "hip"})
    # The direction described the survey's roof, not the one chosen.
    assert _stored_fall(conn, house) is None

    again = garden_by_token(conn, token)
    assert again is not None
    apply(conn, measure(again, [_surveyed(90.0)], None))
    assert _stored_fall(conn, house) is None


def test_a_new_outline_forgets_the_direction_and_a_move_keeps_it(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    garden, house = _imported(conn)
    apply(conn, measure(garden, [_surveyed(0.0)], None))
    url = f"/api/v1/gardens/{garden.share_token}/obstacles/{house}"

    client.patch(url, json={"x": 1.0, "y": 2.0})
    assert _stored_fall(conn, house) == pytest.approx(0.0)

    client.patch(url, json={"points": [[-4, -6], [4, -6], [4, 7], [-4, 7]]})
    assert _stored_fall(conn, house) is None


def test_the_page_is_told_the_direction_and_the_pitch(
    client: TestClient, conn: sqlite3.Connection
) -> None:
    garden, house = _imported(conn)
    conn.execute("UPDATE element SET eaves_m = 6.0 WHERE element_id = ?", (house,))
    conn.execute("UPDATE element SET roof = 'gable' WHERE element_id = ?", (house,))
    conn.commit()
    body: dict[str, Any] = client.get(f"/api/v1/gardens/{garden.share_token}").json()
    before = next(o for o in body["obstacles"] if o["obstacle_id"] == house)
    assert before["roof_fall_deg"] is None
    assert before["roof_pitch_deg"] == pytest.approx(math.degrees(math.atan(3 / 4)), abs=0.1)

    conn.execute("UPDATE element SET roof_fall_deg = 0 WHERE element_id = ?", (house,))
    conn.commit()
    body = client.get(f"/api/v1/gardens/{garden.share_token}").json()
    after = next(o for o in body["obstacles"] if o["obstacle_id"] == house)
    assert after["roof_fall_deg"] == pytest.approx(0.0)
    assert after["roof_pitch_deg"] == pytest.approx(math.degrees(math.atan(3 / 6)), abs=0.1)


# --- the light: the demo state ------------------------------------------------------

def _turned_house_garden(conn: sqlite3.Connection, fall: float | None,
                         height: float = 9.0) -> Garden:
    garden_id = create_garden(conn, name="G", latitude=WUPPERTAL.lat, longitude=WUPPERTAL.lon)
    house = add_obstacle(conn, garden_id, ObstacleInput(
        kind="house", x=0, y=0, shape="rect", width=8, depth=12,
        height=height, roof="gable", eaves_m=6.0, label="Haus"))
    conn.execute("UPDATE element SET roof_fall_deg = ? WHERE element_id = ?", (fall, house))
    insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
                   name="Beet", points=[[-8.0, -16.0], [8.0, -16.0], [8.0, -10.0], [-8.0, -10.0]])
    conn.commit()
    return load_garden(conn, garden_id)


def _halves(grid: LightGrid) -> tuple[float, float]:
    """Mean hours on the roof's northern half and its southern half."""
    north: list[float] = []
    south: list[float] = []
    for index, hours in enumerate(grid.hours):
        if hours is None or not grid.is_roof(index):
            continue
        _x, y = grid.centre_of(index % grid.cols, index // grid.cols)
        if y > 1.0:
            north.append(hours)
        elif y < -1.0:
            south.append(hours)
    assert north and south
    return sum(north) / len(north), sum(south) / len(south)


def test_the_north_side_is_darker_because_the_ridge_was_measured(
    conn: sqlite3.Connection,
) -> None:
    """Wave 21's demo, in one test. The long side runs north-south, so the
    assumption faces the pitches east and west and the roof's two halves read
    alike; the surveyed ridge faces them north and south, and the north one
    loses the noon sun behind it.

    On a 38° roof, as doc 65 measured it. This used a 27° one and asked for
    0.2 h, which the old sampling's noise supplied: sampled until the answer
    stops moving, a 27° pitch loses the noon sun only in late October, and in
    hours its two halves differ by a tenth (doc 117). A steeper pitch loses it
    all of March and October: 1.2 h."""
    assumed = _turned_house_garden(conn, None, height=10.7)
    surveyed = _turned_house_garden(conn, 0.0, height=10.7)
    a_north, a_south = _halves(compute_grid(assumed, shading_obstacles(conn, assumed)))
    s_north, s_south = _halves(compute_grid(surveyed, shading_obstacles(conn, surveyed)))

    assert s_north < s_south
    assert (s_south - s_north) > (a_south - a_north) + 0.8


def test_a_map_computed_before_the_direction_was_known_is_stale(
    conn: sqlite3.Connection,
) -> None:
    garden, house = _imported(conn)
    before = signature_of(garden)
    conn.execute("UPDATE element SET roof_fall_deg = 0 WHERE element_id = ?", (house,))
    conn.commit()
    assert signature_of(load_garden(conn, garden.garden_id)) != before
