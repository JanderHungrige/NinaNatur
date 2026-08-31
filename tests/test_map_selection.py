"""Turning a map selection into a garden with its surroundings."""
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ninanatur.api import geo as geo_routes
from ninanatur.api.deps import get_connection
from ninanatur.geo.osm import Place
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

# A square garden of about 20 x 20 m near Kleinmachnow.
OUTLINE = [
    {"lat": 52.4055, "lon": 13.2100},
    {"lat": 52.4055, "lon": 13.21029},
    {"lat": 52.40568, "lon": 13.21029},
    {"lat": 52.40568, "lon": 13.2100},
]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)

    def fake_buildings(south: float, west: float, north: float, east: float, **_: Any) -> Any:
        from ninanatur.geo.projection import LatLon
        from ninanatur.geo.surroundings import OsmBuilding

        return [
            # Just south of the garden, tall enough to matter.
            OsmBuilding(1, LatLon(52.40530, 13.21015), [], {"building": "house", "height": "9"}),
            # No height at all — the normal case in a German suburb.
            OsmBuilding(2, LatLon(52.40544, 13.21034), [], {"building": "house"}),
            # A shed, too low to reach the garden from where it stands.
            OsmBuilding(3, LatLon(52.40500, 13.21100), [], {"building": "shed", "height": "2"}),
        ]

    monkeypatch.setattr(geo_routes, "buildings_in", fake_buildings)
    # Streets are stubbed here rather than per test, so no test can reach
    # Overpass by forgetting to. A suite that sometimes goes to the network is
    # a suite that sometimes fails for reasons nobody changed.
    monkeypatch.setattr(geo_routes, "streets_in", lambda *_a, **_k: [])
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create(client: TestClient, **extra: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/gardens/from-map",
        json={"name": "Kartengarten", "outline": OUTLINE, **extra},
    )
    assert response.status_code in (200, 201), response.text
    body: dict[str, Any] = response.json()
    return body


def test_the_selection_becomes_a_garden_at_that_place(client: TestClient) -> None:
    body = _create(client)
    # Rounded to 0.1° on the way in: the map knows where the garden is, the
    # database does not need to.
    assert body["garden"]["latitude"] == pytest.approx(52.4, abs=0.05)


def test_the_outline_becomes_a_bed_in_metres(client: TestClient) -> None:
    bed = _create(client)["garden"]["beds"][0]
    xs = [p[0] for p in bed["polygon"]]
    ys = [p[1] for p in bed["polygon"]]
    assert max(xs) - min(xs) == pytest.approx(20, abs=3)
    assert max(ys) - min(ys) == pytest.approx(20, abs=3)


def test_buildings_that_can_shade_it_come_with_it(client: TestClient) -> None:
    obstacles = _create(client)["garden"]["obstacles"]
    assert len(obstacles) == 2, "the 2 m shed cannot reach and should not be here"


def test_it_reports_how_many_heights_it_had_to_assume(client: TestClient) -> None:
    """75-88% of suburban buildings carry no height. A model that did not say so
    would present an assumption as a measurement."""
    body = _create(client)
    assert body["heights"]["measured"] == 1
    assert body["heights"]["assumed"] == 1


def test_the_neighbourhood_answer_sets_the_assumed_heights(client: TestClient) -> None:
    flats = _create(client, neighbourhood="apartment")["garden"]["obstacles"]
    houses = _create(client, neighbourhood="detached")["garden"]["obstacles"]
    tallest = lambda obs: max(o["height"] for o in obs)  # noqa: E731
    assert tallest(flats) > tallest(houses)


def test_the_light_is_computed_from_the_surroundings(client: TestClient) -> None:
    # The point of the whole feature: a garden that arrives already knowing what
    # shades it.
    bed = _create(client)["garden"]["beds"][0]
    assert bed["sun_hours"] is not None
    assert bed["sun_hours"] < 12.6


def test_an_outline_with_two_points_is_refused(client: TestClient) -> None:
    response = client.post(
        "/api/v1/gardens/from-map",
        json={"name": "Linie", "outline": OUTLINE[:2]},
    )
    assert response.status_code == 422


def test_a_selection_outside_germany_is_refused(client: TestClient) -> None:
    # The catalogue is German. A garden in Ohio would get suggestions for plants
    # that do not grow there and a licence position that does not apply.
    far = [{"lat": 40.0, "lon": -83.0} for _ in range(4)]
    response = client.post("/api/v1/gardens/from-map", json={"name": "Ohio", "outline": far})
    assert response.status_code == 422


def test_address_search_is_proxied_rather_than_called_from_the_browser(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through the server so the cache, the delay and the User-Agent the usage
    policy asks for are in one place, not in every visitor's browser."""
    monkeypatch.setattr(
        geo_routes, "search_address",
        lambda q, **_: [Place(name="Hauptstraße 1", lat=52.4, lon=13.2)],
    )
    body = client.get("/api/v1/geo/search", params={"q": "Hauptstraße"}).json()
    assert body["places"][0]["name"] == "Hauptstraße 1"


def test_an_empty_search_is_not_sent_on(client: TestClient) -> None:
    assert client.get("/api/v1/geo/search", params={"q": "  "}).json()["places"] == []


def test_imagery_is_offered_only_where_its_licence_reaches(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Per Bundesland, because the licences are per Bundesland. A state without
    an entry gets no imagery rather than a neighbour's — that would be using one
    state's imagery over another state's ground."""
    monkeypatch.setattr(geo_routes, "state_at", lambda lat, lon, **_: "Brandenburg")
    body = client.get("/api/v1/geo/imagery", params={"lat": 52.4, "lon": 13.2}).json()
    assert body["available"] is True
    assert body["attribution"].startswith("©")

    monkeypatch.setattr(geo_routes, "state_at", lambda lat, lon, **_: "Hessen")
    assert client.get("/api/v1/geo/imagery", params={"lat": 50.1, "lon": 8.7}).json()[
        "available"
    ] is False


def test_a_place_whose_state_is_unknown_gets_no_imagery(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(geo_routes, "state_at", lambda lat, lon, **_: None)
    body = client.get("/api/v1/geo/imagery", params={"lat": 52.4, "lon": 13.2}).json()
    assert body["available"] is False
    assert body["url"] is None


def test_a_garden_from_the_map_gets_the_streets_around_it(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """The map knows the street and the plan did not show it. It is drawn so
    somebody looking at the plan knows which way round it is."""
    from ninanatur.api import geo as geo_routes
    from ninanatur.geo.osm import OsmStreet
    from ninanatur.geo.projection import LatLon

    monkeypatch.setattr(geo_routes, "buildings_in", lambda *a, **k: [])
    monkeypatch.setattr(
        geo_routes,
        "streets_in",
        lambda *a, **k: [
            OsmStreet(
                osm_id=1,
                name="Gartenweg",
                centreline=[
                    LatLon(lat=52.4998, lon=13.3998),
                    LatLon(lat=52.5006, lon=13.4008),
                ],
                width_m=6.0,
            )
        ],
    )

    made = client.post(
        "/api/v1/gardens/from-map",
        json={
            "name": "Mit Straße",
            "outline": [
                {"lat": 52.5, "lon": 13.4},
                {"lat": 52.5004, "lon": 13.4},
                {"lat": 52.5004, "lon": 13.4006},
            ],
        },
    )
    assert made.status_code == 201, made.json()
    streets = [o for o in made.json()["garden"]["obstacles"] if o["kind"] == "street"]
    assert len(streets) == 1
    street = streets[0]
    # A line with a width, which is the element Wave 11 built — not a polygon
    # somebody had to draw around the road.
    assert street["shape"] == "line"
    assert street["width"] == 6.0
    assert street["label"] == "Gartenweg"
    # And it casts nothing: a road does not shade a garden.
    assert street["height"] is None


def test_a_street_is_not_fatal_when_overpass_will_not_answer(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """Overpass is free and has no SLA. A garden must still be made."""
    from ninanatur.api import geo as geo_routes

    monkeypatch.setattr(geo_routes, "buildings_in", lambda *a, **k: [])

    def refuse(*_a: object, **_k: object) -> list[object]:
        raise RuntimeError("Overpass says no")

    monkeypatch.setattr(geo_routes, "streets_in", refuse)
    made = client.post(
        "/api/v1/gardens/from-map",
        json={
            "name": "Ohne Straße",
            "outline": [
                {"lat": 52.5, "lon": 13.4},
                {"lat": 52.5004, "lon": 13.4},
                {"lat": 52.5004, "lon": 13.4006},
            ],
        },
    )
    assert made.status_code == 201, made.json()
    assert [
        o for o in made.json()["garden"]["obstacles"] if o["kind"] == "street"
    ] == []
