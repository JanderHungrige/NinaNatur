"""Address search and building fetch, with the network stated rather than stubbed."""
from typing import Any

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


def test_the_query_asks_for_centres_not_full_geometry() -> None:
    # `out center` is a fraction of the payload and all the shading model needs;
    # full geometry over a shared free service would be a poor way to behave.
    seen: dict[str, Any] = {}

    def fetch(url: str, params: dict[str, Any] | None = None) -> Any:
        seen.update(params or {})
        return {"elements": []}

    buildings_in(52.3, 13.1, 52.5, 13.3, fetch=fetch)
    assert "out tags center" in seen["data"]
