"""A building on the plan is the building's own shape, at its own size.

Reported with a screenshot: after the surroundings fix brought the neighbours
back, they arrived as huge overlapping squares in the wrong places relative to
each other and to the plot.

Measured against live OSM data before the fix, the squares were **2.1 to 2.8
times** the real footprint area, every one of them axis-aligned. Two causes:
`_radius_of` returned half the bounding box's *diagonal*, and the plan then drew
a square of side `radius × 1.77` around it.
"""
from __future__ import annotations

import math

from ninanatur.geo.osm import buildings_in
from ninanatur.geo.projection import LatLon, centroid
from ninanatur.geo.surroundings import OsmBuilding, surroundings_from

PLOT = [
    LatLon(lat=52.4000, lon=13.2000),
    LatLon(lat=52.4000, lon=13.2004),
    LatLon(lat=52.4003, lon=13.2004),
    LatLon(lat=52.4003, lon=13.2000),
]


def _north(anchor: LatLon, metres: float) -> float:
    return anchor.lat + metres / 111_320.0


def _east(anchor: LatLon, metres: float) -> float:
    return anchor.lon + metres / (111_320.0 * math.cos(math.radians(anchor.lat)))


def _long_barn(anchor: LatLon) -> OsmBuilding:
    """30 m by 8 m, lying east-west just north of the plot."""
    south, north = _north(anchor, 25.0), _north(anchor, 33.0)
    west, east = _east(anchor, -15.0), _east(anchor, 15.0)
    return OsmBuilding(
        osm_id=1,
        centre=LatLon(lat=_north(anchor, 29.0), lon=anchor.lon),
        outline=[
            LatLon(lat=south, lon=west),
            LatLon(lat=south, lon=east),
            LatLon(lat=north, lon=east),
            LatLon(lat=north, lon=west),
        ],
        tags={"building": "barn", "height": "8"},
    )


def _area(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for index, (ax, ay) in enumerate(points):
        bx, by = points[(index + 1) % len(points)]
        total += ax * by - bx * ay
    return abs(total) / 2


def test_a_building_keeps_its_outline() -> None:
    anchor = centroid(PLOT)

    kept = surroundings_from(anchor, [_long_barn(anchor)], outline=PLOT).objects

    assert len(kept) == 1
    assert len(kept[0].outline) == 4, "the shape OSM drew, not a stand-in for it"


def test_the_outline_is_the_right_size() -> None:
    """30 x 8 m is 240 m². The square it replaces was 2.1-2.8 times the real
    area on live data, which is what made them overlap each other."""
    anchor = centroid(PLOT)

    kept = surroundings_from(anchor, [_long_barn(anchor)], outline=PLOT).objects

    assert _area(kept[0].outline) == pytest_approx(240.0, 20.0)


def test_the_outline_is_relative_to_the_building_itself() -> None:
    """`footprint_of` adds the element's x and y to every point, so points that
    were absolute would place the building twice as far out as it is."""
    anchor = centroid(PLOT)

    kept = surroundings_from(anchor, [_long_barn(anchor)], outline=PLOT).objects
    barn = kept[0]

    middle_x = sum(x for x, _ in barn.outline) / len(barn.outline)
    middle_y = sum(y for _, y in barn.outline) / len(barn.outline)
    assert abs(middle_x) < 1.0 and abs(middle_y) < 1.0, (
        "the points are offsets from the building's own position"
    )
    assert barn.y > 20, "and the position itself is where the barn is"


def test_the_radius_is_the_circle_of_equal_area() -> None:
    """The shading model is cylinders, so a footprint still needs one number.
    Half the bounding box's diagonal was the wrong one — for a 30 x 8 m barn it
    is 15.5 m, a circle of 755 m² standing in for 240."""
    anchor = centroid(PLOT)

    barn = surroundings_from(anchor, [_long_barn(anchor)], outline=PLOT).objects[0]

    assert barn.radius_m == pytest_approx(math.sqrt(240.0 / math.pi), 1.0)


def test_a_building_without_an_outline_still_gets_a_size() -> None:
    """Overpass can answer without geometry — a relation whose members were not
    returned. A default is better than nothing, and it is the one place a made-up
    number is still in use."""
    anchor = centroid(PLOT)
    plain = OsmBuilding(
        osm_id=2,
        centre=LatLon(lat=_north(anchor, 25.0), lon=anchor.lon),
        outline=[],
        tags={"building": "house", "height": "8"},
    )

    kept = surroundings_from(anchor, [plain], outline=PLOT).objects

    assert kept and kept[0].outline == []
    assert kept[0].radius_m > 0


def test_a_relation_uses_its_outer_ring_only() -> None:
    """A multipolygon's members are outer rings and holes, and concatenating
    them gives a bounding box spanning both — which is how a courtyard building
    became enormous."""

    def fake(_url: str, _params: dict[str, str] | None = None) -> dict[str, object]:
        return {
            "elements": [
                {
                    "id": 3,
                    "type": "relation",
                    "tags": {"building": "yes"},
                    "members": [
                        {"role": "outer", "geometry": [
                            {"lat": 52.4000, "lon": 13.2000},
                            {"lat": 52.4000, "lon": 13.2002},
                            {"lat": 52.4001, "lon": 13.2002},
                            {"lat": 52.4001, "lon": 13.2000},
                        ]},
                        {"role": "inner", "geometry": [
                            {"lat": 52.40004, "lon": 13.20004},
                            {"lat": 52.40004, "lon": 13.20016},
                            {"lat": 52.40006, "lon": 13.20016},
                        ]},
                    ],
                }
            ]
        }

    found = buildings_in(52.39, 13.19, 52.41, 13.21, fetch=fake)

    assert len(found) == 1
    assert len(found[0].outline) == 4, "the outer ring, and only it"


def pytest_approx(value: float, tolerance: float) -> object:
    import pytest

    return pytest.approx(value, abs=tolerance)
