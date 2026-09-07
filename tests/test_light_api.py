"""The sun map through the API, and the day's shadows."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

BED = {"name": "Beet", "polygon": [[0, 0], [6, 0], [6, 4], [0, 4]],
       "soil_type": "loam", "moisture": "fresh"}
#: Due south of the bed and tall enough to matter.
WALL = {"kind": "wall", "x": 3.0, "y": -3.0, "shape": "rect",
        "width": 8.0, "depth": 0.4, "height": 4.0}


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _garden(client: TestClient, with_wall: bool = False) -> str:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5171, "longitude": 13.3889}
    ).json()["share_token"]
    client.post(f"/api/v1/gardens/{token}/beds", json=BED)
    if with_wall:
        client.post(f"/api/v1/gardens/{token}/obstacles", json=WALL)
    # Since 2026-09-07 nothing recomputes on a write, so a garden has no map
    # until somebody asks for one. Every test below is about the map, so they
    # all ask first — which is what a gardener does too.
    client.post(f"/api/v1/gardens/{token}/light")
    return token


# --- the map ---------------------------------------------------------------

def test_a_garden_with_nothing_drawn_has_no_map(client: TestClient) -> None:
    """Null rather than an empty grid. There is no ground to say anything about
    yet, and a grid of zeros would read as a garden in total darkness."""
    token = client.post(
        "/api/v1/gardens", json={"name": "leer", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]

    assert client.get(f"/api/v1/gardens/{token}/light").json() is None


def test_the_map_comes_back_with_its_shape(client: TestClient) -> None:
    token = _garden(client)

    body = client.get(f"/api/v1/gardens/{token}/light").json()

    assert body["cols"] * body["rows"] == len(body["hours"])
    assert body["cell_m"] > 0
    assert body["max_hours"] > 0
    assert body["computed_at"]


def test_a_wall_shows_up_in_the_map(client: TestClient) -> None:
    """The point of the whole feature: the strip behind the wall is darker than
    the far end, which a single number per bed could never say."""
    token = _garden(client, with_wall=True)

    body = client.get(f"/api/v1/gardens/{token}/light").json()

    cols, rows, cell = body["cols"], body["rows"], body["cell_m"]
    hours = body["hours"]
    southern = [hours[0 * cols + c] for c in range(cols)]
    northern = [hours[(rows - 1) * cols + c] for c in range(cols)]
    assert min(southern) < max(northern), f"cell {cell} m, {cols}x{rows}"


# --- staleness -------------------------------------------------------------

def test_a_fresh_map_is_not_stale(client: TestClient) -> None:
    token = _garden(client)
    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is False


def test_renaming_a_bed_does_not_make_the_map_stale(client: TestClient) -> None:
    """The reason staleness is a signature rather than a list of actions: a name
    cannot move a shadow, and a list would have to remember that."""
    token = _garden(client)
    bed_id = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["bed_id"]

    client.patch(f"/api/v1/gardens/{token}/obstacles/{bed_id}",
                 json={"label": "hinten links"})

    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is False


def test_the_button_rebuilds_it(client: TestClient) -> None:
    """Belt as well as braces. If the signature ever misses something, this is
    how somebody fixes their own map without knowing why it was wrong."""
    token = _garden(client)
    before = client.get(f"/api/v1/gardens/{token}/light").json()["computed_at"]

    rebuilt = client.post(f"/api/v1/gardens/{token}/light").json()

    assert rebuilt["stale"] is False
    assert rebuilt["computed_at"] >= before


def test_an_unknown_garden_is_404_not_an_empty_map(client: TestClient) -> None:
    assert client.get("/api/v1/gardens/gibtesnicht/light").status_code == 404


# --- the day ---------------------------------------------------------------

def test_a_day_of_shadows_comes_back_in_frames(client: TestClient) -> None:
    token = _garden(client, with_wall=True)

    body = client.get(f"/api/v1/gardens/{token}/shadows?month=6").json()

    assert body["month"] == 6
    assert body["day"] == 15, "the middle of the month, not either edge"
    assert len(body["frames"]) > 10
    assert all(f["polygons"] for f in body["frames"]), "the wall casts all day"


def test_the_shadow_is_longest_at_the_ends_of_the_day(client: TestClient) -> None:
    """A shadow that did not grow towards evening would mean the azimuth or the
    altitude was being read wrong, and both are easy to get subtly wrong."""
    token = _garden(client, with_wall=True)
    frames = client.get(f"/api/v1/gardens/{token}/shadows?month=6").json()["frames"]

    def reach(frame: dict[str, object]) -> float:
        polygon = frame["polygons"][0]  # type: ignore[index]
        return max(abs(y) for _x, y in polygon)  # type: ignore[misc]

    noon = max(frames, key=lambda f: f["altitude"])
    evening = frames[-1]
    assert reach(evening) > reach(noon)


def test_a_month_outside_the_year_is_refused(client: TestClient) -> None:
    token = _garden(client)
    assert client.get(f"/api/v1/gardens/{token}/shadows?month=13").status_code == 422


def test_a_garden_with_nothing_standing_has_frames_and_no_shadows(
    client: TestClient,
) -> None:
    """Sun positions still exist. An empty list of frames would look like a
    failure; an empty list of polygons is the honest answer."""
    token = _garden(client)

    frames = client.get(f"/api/v1/gardens/{token}/shadows?month=6").json()["frames"]

    assert frames
    assert all(f["polygons"] == [] for f in frames)


# --- the ground ------------------------------------------------------------

def test_a_garden_with_no_ground_fetched_has_no_terrain(client: TestClient) -> None:
    """Null, and the page says so in words. Nine Bundesländer have no service,
    and a garden there keeps the flat assumption it always had — which is fine,
    and being quiet about it is not."""
    token = _garden(client)

    assert client.get(f"/api/v1/gardens/{token}/terrain").json() is None


def test_terrain_comes_back_with_its_relief_and_its_credit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ninanatur.geo.projection import LatLon
    from ninanatur.geo.terrain import TerrainWindow
    from ninanatur.geo.terrain_store import cache_key, save_window

    token = _garden(client)
    conn = app.dependency_overrides[get_connection]()
    size = 30
    save_window(
        conn,
        cache_key(LatLon(lat=52.5171, lon=13.3889)),
        TerrainWindow(
            min_x=-15.0, min_y=-15.0, cell_m=1.0, cols=size, rows=size,
            heights=[100.0 + row * 0.2 for row in range(size) for _ in range(size)],
            source="Brandenburg", licence="dl-de/by-2-0",
            attribution="© GeoBasis-DE/LGB", vertical_step_m=0.01,
        ),
    )

    body = client.get(f"/api/v1/gardens/{token}/terrain").json()

    assert body["cols"] * body["rows"] == len(body["relief"])
    assert all(0.0 <= v <= 1.0 for v in body["relief"])
    assert body["attribution"] == "© GeoBasis-DE/LGB"
    assert body["licence"] == "dl-de/by-2-0"
    assert body["vertical_step_m"] == 0.01
    assert body["highest"] > body["lowest"]


def test_an_unknown_garden_has_no_terrain_either(client: TestClient) -> None:
    assert client.get("/api/v1/gardens/gibtesnicht/terrain").status_code == 404


# --- one month at a time ----------------------------------------------------

def test_a_month_can_be_asked_for_instead_of_the_season(client: TestClient) -> None:
    """March and June are different gardens wherever anything stands to the
    south, and one number for the whole season describes neither."""
    token = _garden(client, with_wall=True)

    season = client.get(f"/api/v1/gardens/{token}/light").json()
    march = client.get(f"/api/v1/gardens/{token}/light?month=3").json()
    june = client.get(f"/api/v1/gardens/{token}/light?month=6").json()

    assert june["max_hours"] > season["max_hours"] > march["max_hours"]
    # Same garden, same grid: only the answer in each cell changes.
    assert (march["cols"], march["rows"]) == (season["cols"], season["rows"])


def test_a_month_is_computed_now_so_it_is_never_stale(client: TestClient) -> None:
    """It is not the stored map. Nothing narrows the season on disk, so a month
    can only be the current garden — and saying `stale` would be a lie."""
    token = _garden(client)
    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "house", "x": 2, "y": -6, "radius": 6, "height": 9},
    )

    assert client.get(f"/api/v1/gardens/{token}/light").json()["stale"] is True
    assert client.get(f"/api/v1/gardens/{token}/light?month=6").json()["stale"] is False


def test_winter_cannot_be_asked_for(client: TestClient) -> None:
    """The whole light model stops at October. A December map would drag every
    German garden into shade and answer a question nobody plants by."""
    token = _garden(client)
    assert client.get(f"/api/v1/gardens/{token}/light?month=12").status_code == 422
    assert client.get(f"/api/v1/gardens/{token}/light?month=1").status_code == 422


def test_the_warnings_do_not_flicker_as_the_months_are_scrolled(
    client: TestClient,
) -> None:
    """Misplacement is a judgement about a growing season. Warnings appearing
    and vanishing while somebody looks through the months would be noise."""
    token = _garden(client, with_wall=True)
    season = client.get(f"/api/v1/gardens/{token}/light").json()["misplaced"]

    for month in (3, 6, 10):
        shown = client.get(f"/api/v1/gardens/{token}/light?month={month}").json()
        assert shown["misplaced"] == season


# --- there is no ground under a house ---------------------------------------

def test_a_building_is_answered_on_its_roof_rather_than_under_it(
    client: TestClient,
) -> None:
    """The ground under a house gets no sun at all, all day, every day. Reporting
    that is true and useless: what a plan shows at a house is the roof, and the
    roof is in the sun. So the cell is answered up there instead, and flagged."""
    token = client.post(
        "/api/v1/gardens", json={"name": "Haus", "latitude": 51.2564, "longitude": 7.1501}
    ).json()["share_token"]
    client.post(f"/api/v1/gardens/{token}/beds", json=BED)
    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "house", "x": 6, "y": 8, "width": 10, "depth": 8,
              "height": 9, "roof": "gable", "eaves_m": 6},
    )
    client.post(f"/api/v1/gardens/{token}/light")

    body = client.get(f"/api/v1/gardens/{token}/light").json()
    roofs = [h for h, on_roof in zip(body["hours"], body["roof"], strict=True) if on_roof]

    assert roofs, "the house's footprint is flagged as roof"
    assert min(roofs) > 1.0, "and it is not the darkness under the building"


def test_a_sunny_roof_does_not_set_the_scale_for_the_garden(
    client: TestClient,
) -> None:
    """Nothing is planted on a roof. `max_hours` is what the drawing scales the
    ground against and what the panel calls the brightest point in the garden."""
    token = client.post(
        "/api/v1/gardens", json={"name": "Haus", "latitude": 51.2564, "longitude": 7.1501}
    ).json()["share_token"]
    client.post(f"/api/v1/gardens/{token}/beds", json=BED)
    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "house", "x": 6, "y": 8, "width": 10, "depth": 8, "height": 9},
    )
    client.post(f"/api/v1/gardens/{token}/light")

    body = client.get(f"/api/v1/gardens/{token}/light").json()
    ground = [h for h, on_roof in zip(body["hours"], body["roof"], strict=True)
              if not on_roof and h is not None]

    assert body["max_hours"] == pytest.approx(max(ground))


def test_a_tree_still_has_ground_under_it(client: TestClient) -> None:
    """Dappled shade under an apple tree is exactly what somebody planting there
    is asking about. Only a roof takes the ground away."""
    token = client.post(
        "/api/v1/gardens", json={"name": "Baum", "latitude": 51.2564, "longitude": 7.1501}
    ).json()["share_token"]
    client.post(f"/api/v1/gardens/{token}/beds", json=BED)
    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "tree", "x": 2, "y": 2, "radius": 3, "height": 8},
    )
    client.post(f"/api/v1/gardens/{token}/light")

    body = client.get(f"/api/v1/gardens/{token}/light").json()

    assert None not in body["hours"]
    assert not any(body["roof"]), "a crown is not a roof"
