"""What the map hands over, measured from the plot rather than from a point.

Reported with screenshots: a farmyard with four or five buildings plainly drawn
on OSM and on the aerial photo arrived in the plan as **one** small square.

Everything here measures from the garden's *outline*. The code it replaces
measured from the outline's centroid, which is the same thing only for a plot
small enough not to matter — and these are the gardens where it matters most.
"""
from __future__ import annotations

import math

from ninanatur.geo.projection import LatLon, centroid
from ninanatur.geo.surroundings import (
    NeighbourhoodKind,
    OsmBuilding,
    surroundings_from,
)

#: A plot 40 m across and 60 m deep at 52.4°N — an ordinary rural garden, and
#: the size at which measuring from the middle starts losing the neighbours.
PLOT = [
    LatLon(lat=52.4000, lon=13.2000),
    LatLon(lat=52.4000, lon=13.2006),  # ~41 m east
    LatLon(lat=52.4005, lon=13.2006),  # ~56 m north
    LatLon(lat=52.4005, lon=13.2000),
]

HOUSE_TAGS = {"building": "house", "building:levels": "2"}


def _building(osm_id: int, lat: float, lon: float, **tags: str) -> OsmBuilding:
    return OsmBuilding(
        osm_id=osm_id,
        centre=LatLon(lat=lat, lon=lon),
        outline=[],
        tags={**HOUSE_TAGS, **tags},
    )


def _metres_north(anchor: LatLon, metres: float) -> float:
    return anchor.lat + metres / 111_320.0


def test_a_neighbour_beside_the_plot_is_kept() -> None:
    """The reported case, in one assertion.

    A house whose wall is a few metres from the boundary, whose centre is 65 m
    from the centroid of a 60 m deep plot. Measured from the middle it is out of
    range; measured from the plot it is next door.
    """
    anchor = centroid(PLOT)
    # North of the plot's northern edge by ~8 m.
    neighbour = _building(1, _metres_north(anchor, 36.0), 13.2003)

    kept = surroundings_from(anchor, [neighbour], outline=PLOT).objects

    assert [o.osm_id for o in kept] == [1]


def test_the_margin_is_measured_from_the_boundary_not_the_middle() -> None:
    """The plot's north edge is ~28 m from its centroid, so a building 70 m from
    the centroid is 42 m from the hedge — inside the margin, and outside the box
    this replaces. Tall enough to pass the reach filter, which is the other
    gate and not what is being tested here."""
    anchor = centroid(PLOT)
    tall = {"building": "apartments", "height": "20"}
    inside_margin = _building(2, _metres_north(anchor, 70.0), 13.2003, **tall)
    well_beyond = _building(3, _metres_north(anchor, 400.0), 13.2003, **tall)

    kept = {o.osm_id for o in surroundings_from(anchor, [inside_margin, well_beyond],
                                                outline=PLOT).objects}

    assert 2 in kept, "a building 42 m past the boundary shades the garden"
    assert 3 not in kept, "the margin still has to end somewhere"


def test_a_shed_that_cannot_reach_is_still_dropped() -> None:
    """The reach filter is what lets the margin be generous. Widening the box
    must not turn the plan into every shed in the village."""
    anchor = centroid(PLOT)
    shed = _building(4, _metres_north(anchor, 60.0), 13.2003,
                     **{"building": "shed", "height": "2"})

    kept = surroundings_from(anchor, [shed], outline=PLOT).objects

    assert kept == []


def test_without_an_outline_it_behaves_as_before() -> None:
    """Callers that have only a point still work — the anchor is then the plot,
    which is exactly the old behaviour and correct for a point."""
    anchor = LatLon(lat=52.4, lon=13.2)
    near = _building(5, _metres_north(anchor, 20.0), 13.2)
    far = _building(6, _metres_north(anchor, 400.0), 13.2)

    kept = {o.osm_id for o in surroundings_from(anchor, [near, far]).objects}

    assert kept == {5}


def test_a_large_building_is_measured_by_its_wall() -> None:
    """A barn whose centre is far away because the barn is long. Its wall is
    what stands beside the garden, and the reach filter already says so — the
    box in front of it did not."""
    anchor = centroid(PLOT)
    barn = OsmBuilding(
        osm_id=7,
        centre=LatLon(lat=_metres_north(anchor, 70.0), lon=13.2003),
        # 60 m long: the near wall is 40 m from the centre.
        outline=[
            LatLon(lat=_metres_north(anchor, 40.0), lon=13.2000),
            LatLon(lat=_metres_north(anchor, 40.0), lon=13.2006),
            LatLon(lat=_metres_north(anchor, 100.0), lon=13.2006),
            LatLon(lat=_metres_north(anchor, 100.0), lon=13.2000),
        ],
        tags={"building": "barn", "height": "8"},
    )

    kept = surroundings_from(anchor, [barn], outline=PLOT).objects

    assert [o.osm_id for o in kept] == [7]
    assert kept[0].radius_m > 20, "half the diagonal of a 60 m barn"


def test_the_neighbourhood_height_still_applies() -> None:
    anchor = centroid(PLOT)
    plain = _building(8, _metres_north(anchor, 36.0), 13.2003)
    plain = OsmBuilding(osm_id=8, centre=plain.centre, outline=[], tags={"building": "yes"})

    kept = surroundings_from(
        anchor, [plain], outline=PLOT, neighbourhood=NeighbourhoodKind.APARTMENT
    ).objects

    assert kept and kept[0].height_m == NeighbourhoodKind.APARTMENT.height_m


def test_distance_is_to_the_nearest_corner_of_the_plot() -> None:
    """Not to the centroid. On a 60 m plot those are 30 m apart, which is the
    difference between a shadow that arrives and one the filter throws away."""
    anchor = centroid(PLOT)
    # Due north, just past the northern edge. Its shadow reaches the near part
    # of the plot even though the centroid is far from it.
    near_edge = _building(9, _metres_north(anchor, 34.0), 13.2003,
                          **{"building": "house", "height": "6"})

    kept = surroundings_from(anchor, [near_edge], outline=PLOT).objects

    assert [o.osm_id for o in kept] == [9]
    # A 6 m house reaches 22 m at the filter's sun altitude. From the centroid
    # it is 34 m away and would have been dropped.
    assert 34.0 * math.tan(math.radians(15.0)) > 6.0  # sanity: it would not reach
