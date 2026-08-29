"""What the map contributes to a garden, and what it honestly cannot.

Measured while planning Wave 8: across 4,912 suburban buildings, **zero** carry
an OSM `height` tag and 75-88% carry nothing at all. The confidence ladder here
is built around that, not around the central-Berlin sample that suggested
otherwise.
"""
import pytest

from ninanatur.geo.projection import LatLon
from ninanatur.geo.surroundings import (
    MARGIN_M,
    HeightSource,
    NeighbourhoodKind,
    OsmBuilding,
    reaches,
    surroundings_from,
)

ANCHOR = LatLon(52.4055, 13.2100)


def _building(name: str, dlat: float, dlon: float, tags: dict[str, str]) -> OsmBuilding:
    return OsmBuilding(
        osm_id=abs(hash(name)) % 100000,
        centre=LatLon(ANCHOR.lat + dlat, ANCHOR.lon + dlon),
        outline=[],
        tags=tags,
    )


# --- the reach filter ------------------------------------------------------

def test_a_tall_building_far_away_still_reaches() -> None:
    # 12 m at a 15 degree sun casts 45 m. A margin that dropped it would lose
    # most of what a garden actually feels in the morning and evening.
    assert reaches(height_m=12.0, distance_m=44.0) is True


def test_a_low_fence_far_away_does_not() -> None:
    assert reaches(height_m=2.0, distance_m=30.0) is False


def test_a_low_fence_close_by_does() -> None:
    assert reaches(height_m=2.0, distance_m=5.0) is True


def test_an_object_at_the_edge_of_its_own_reach_counts() -> None:
    # tan(15°) ≈ 0.268, so 12 m reaches ~44.8 m.
    assert reaches(height_m=12.0, distance_m=44.7) is True
    assert reaches(height_m=12.0, distance_m=45.5) is False


# --- heights ---------------------------------------------------------------

def test_an_osm_height_is_used_and_marked_measured() -> None:
    result = surroundings_from(ANCHOR, [_building("a", 0.0002, 0, {"height": "9.5"})])
    obj = result.objects[0]
    assert obj.height_m == pytest.approx(9.5)
    assert obj.height_source is HeightSource.OSM_HEIGHT


def test_levels_become_a_height_and_are_marked_estimated() -> None:
    result = surroundings_from(
        ANCHOR, [_building("b", 0.0002, 0, {"building:levels": "2"})]
    )
    obj = result.objects[0]
    assert obj.height_m == pytest.approx(6.0)
    assert obj.height_source is HeightSource.OSM_LEVELS


def test_a_building_with_nothing_takes_the_neighbourhood_answer() -> None:
    """75-88% of suburban buildings. This is the normal case, not the fallback."""
    result = surroundings_from(
        ANCHOR, [_building("c", 0.0002, 0, {})], neighbourhood=NeighbourhoodKind.DETACHED
    )
    obj = result.objects[0]
    assert obj.height_m == pytest.approx(NeighbourhoodKind.DETACHED.height_m)
    assert obj.height_source is HeightSource.NEIGHBOURHOOD


def test_the_neighbourhood_answer_never_overrides_a_recorded_height() -> None:
    result = surroundings_from(
        ANCHOR,
        [_building("d", 0.0002, 0, {"height": "14"})],
        neighbourhood=NeighbourhoodKind.DETACHED,
    )
    assert result.objects[0].height_m == pytest.approx(14.0)


def test_a_height_in_feet_is_refused_rather_than_believed() -> None:
    # OSM allows units. A "30'" read as 30 metres is a ten-storey shadow over
    # somebody's vegetable patch.
    result = surroundings_from(ANCHOR, [_building("e", 0.0002, 0, {"height": "30'"})])
    assert result.objects[0].height_source is not HeightSource.OSM_HEIGHT


def test_the_report_counts_what_it_had_to_assume(client_free: None = None) -> None:
    result = surroundings_from(
        ANCHOR,
        [
            _building("f", 0.0002, 0, {"height": "9"}),
            _building("g", 0.00021, 0, {"building:levels": "2"}),
            _building("h", 0.00022, 0, {}),
            _building("i", 0.00023, 0, {}),
        ],
    )
    assert result.measured == 1
    assert result.estimated == 1
    assert result.assumed == 2


# --- the margin ------------------------------------------------------------

def test_things_beyond_the_margin_are_not_fetched_at_all() -> None:
    far = _building("j", MARGIN_M * 3 / 111_320, 0, {"height": "20"})
    assert surroundings_from(ANCHOR, [far]).objects == []


def test_a_building_inside_the_margin_but_out_of_reach_is_dropped() -> None:
    # Inside 50 m but only 2 m tall: its shadow cannot arrive, and showing it
    # would be another object for the user to confirm for nothing.
    near_but_low = _building("k", 40 / 111_320, 0, {"height": "2"})
    assert surroundings_from(ANCHOR, [near_but_low]).objects == []


def test_coordinates_come_back_in_garden_metres() -> None:
    north = _building("l", 20 / 111_320, 0, {"height": "10"})
    obj = surroundings_from(ANCHOR, [north]).objects[0]
    assert obj.y == pytest.approx(20.0, rel=0.01)
    assert obj.x == pytest.approx(0.0, abs=0.5)
