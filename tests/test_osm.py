"""Address search and building fetch, with the network stated rather than stubbed."""
from typing import Any

import pytest

from ninanatur.geo.osm import COUNTRY_CODES, buildings_in, search_address


def test_a_search_asks_for_german_addresses_only() -> None:
    """A search that happily finds Ohio produces a garden this catalogue has no
    plants for."""
    seen: dict[str, Any] = {}

    def fetch(url: str, params: dict[str, Any] | None = None) -> Any:
        seen.update(params or {})
        return []

    search_address("Hauptstraße 1", fetch=fetch)
    assert seen["countrycodes"] == COUNTRY_CODES


def test_an_empty_query_asks_nothing() -> None:
    # A keystroke-per-request search would be rude to a free service.
    called = False

    def fetch(url: str, params: dict[str, Any] | None = None) -> Any:
        nonlocal called
        called = True
        return []

    assert search_address("   ", fetch=fetch) == []
    assert called is False


def test_places_come_back_with_their_coordinates() -> None:
    def fetch(url: str, params: dict[str, Any] | None = None) -> Any:
        return [{"display_name": "Hauptstraße 1, Potsdam", "lat": "52.4", "lon": "13.06"}]

    place = search_address("Hauptstraße 1", fetch=fetch)[0]
    assert place.lat == 52.4
    assert place.name.startswith("Hauptstraße")


def test_a_malformed_result_is_skipped_rather_than_crashing() -> None:
    def fetch(url: str, params: dict[str, Any] | None = None) -> Any:
        return [
            {"display_name": "ohne Koordinaten"},
            {"display_name": "gut", "lat": "1", "lon": "2"},
        ]

    assert len(search_address("x", fetch=fetch)) == 1


def test_buildings_carry_their_tags() -> None:
    def fetch(url: str, params: dict[str, Any] | None = None) -> Any:
        return {"elements": [
            {"id": 7, "center": {"lat": 52.4, "lon": 13.2},
             "tags": {"building": "house", "height": "9"}},
        ]}

    building = buildings_in(52.3, 13.1, 52.5, 13.3, fetch=fetch)[0]
    assert building.osm_id == 7
    assert building.tags["height"] == "9"


def test_an_element_without_a_centre_is_skipped() -> None:
    def fetch(url: str, params: dict[str, Any] | None = None) -> Any:
        return {"elements": [{"id": 1, "tags": {"building": "yes"}}]}

    assert buildings_in(52.3, 13.1, 52.5, 13.3, fetch=fetch) == []


def test_the_query_asks_for_outlines_and_for_relations() -> None:
    """Reversed, with the reason.

    This used to assert `out tags center`, on the grounds that a centre is a
    fraction of the payload and all the shading model needs. It is not: without
    a size, a 60 m barn is judged and drawn as the same 9 m square as a garden
    shed. The payload is larger and the disk cache means a rerun costs nothing.

    `relation` alongside `way` for the same reason a centre was not enough — a
    building drawn as a multipolygon is a relation, and asking only for ways
    dropped it silently.
    """
    seen: dict[str, Any] = {}

    def fetch(url: str, params: dict[str, Any] | None = None) -> Any:
        seen.update(params or {})
        return {"elements": []}

    buildings_in(52.3, 13.1, 52.5, 13.3, fetch=fetch)
    assert "out tags geom" in seen["data"]
    assert 'relation["building"]' in seen["data"]


def test_a_building_comes_back_with_its_outline() -> None:
    """`out tags center` gave one point per building and nothing about its size,
    so every house in a plan was drawn as the same 9 m square and judged for
    shading as if it were one — a 60 m barn included.

    `out tags geom` gives the node list. It costs more payload and the disk
    cache means a rerun costs nothing at all.
    """
    from ninanatur.geo.osm import buildings_in

    captured: dict[str, str] = {}

    def fake(_url: str, params: dict[str, str] | None = None) -> dict[str, object]:
        captured.update(params or {})
        return {
            "elements": [
                {
                    "id": 1,
                    "tags": {"building": "house"},
                    "geometry": [
                        {"lat": 52.4000, "lon": 13.2000},
                        {"lat": 52.4000, "lon": 13.2010},
                        {"lat": 52.4005, "lon": 13.2010},
                        {"lat": 52.4005, "lon": 13.2000},
                    ],
                }
            ]
        }

    found = buildings_in(52.39, 13.19, 52.41, 13.21, fetch=fake)

    assert "geom" in captured["data"], "the outline has to be asked for"
    assert len(found) == 1
    assert len(found[0].outline) == 4
    # The centre is computed from the outline, because `out geom` does not also
    # return `center` — verified against the live API, not assumed.
    assert found[0].centre.lat == pytest.approx(52.40025, abs=1e-4)


def test_a_building_without_geometry_still_arrives_if_it_has_a_centre() -> None:
    """Relations answer with member geometry rather than their own, and an
    element with neither is no use. A building with only a centre is still a
    building that shades a garden."""
    from ninanatur.geo.osm import buildings_in

    def fake(_url: str, _params: dict[str, str] | None = None) -> dict[str, object]:
        return {
            "elements": [
                {"id": 2, "tags": {"building": "yes"},
                 "center": {"lat": 52.4, "lon": 13.2}},
                {"id": 3, "tags": {"building": "yes"}},
            ]
        }

    found = buildings_in(52.39, 13.19, 52.41, 13.21, fetch=fake)

    assert [b.osm_id for b in found] == [2]
    assert found[0].outline == []
