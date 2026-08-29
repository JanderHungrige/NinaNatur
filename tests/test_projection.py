"""Degrees into the metres a plan is drawn in."""
import math

import pytest

from ninanatur.geo.projection import (
    LatLon,
    Metres,
    bounding_box,
    centroid,
    to_latlon,
    to_metres,
)

BERLIN = LatLon(52.5, 13.4)


def test_the_anchor_is_the_origin() -> None:
    assert to_metres(BERLIN, BERLIN) == Metres(0.0, 0.0)


def test_north_is_positive_y() -> None:
    # The whole shading model reads y as north; a sign error here mirrors every
    # shadow in the garden.
    north = to_metres(LatLon(52.501, 13.4), BERLIN)
    assert north.y > 0
    assert north.x == pytest.approx(0.0, abs=1e-9)


def test_east_is_positive_x() -> None:
    assert to_metres(LatLon(52.5, 13.401), BERLIN).x > 0


def test_a_degree_of_longitude_is_shorter_this_far_north() -> None:
    """At 52.5° a degree of longitude is about cos(52.5) of one of latitude.
    Treating them as equal would stretch every garden east-west by 64%."""
    lat_m = to_metres(LatLon(53.5, 13.4), BERLIN).y
    lon_m = to_metres(LatLon(52.5, 14.4), BERLIN).x
    assert lon_m / lat_m == pytest.approx(math.cos(math.radians(52.5)), rel=1e-3)


def test_it_round_trips() -> None:
    point = LatLon(52.5031, 13.4088)
    back = to_latlon(to_metres(point, BERLIN), BERLIN)
    assert back.lat == pytest.approx(point.lat, abs=1e-9)
    assert back.lon == pytest.approx(point.lon, abs=1e-9)


def test_a_known_distance_comes_out_right() -> None:
    # 0.001° of latitude is 111.32 m by definition of the constant used.
    assert to_metres(LatLon(52.501, 13.4), BERLIN).y == pytest.approx(111.32, rel=1e-4)


def test_the_bounding_box_is_square_in_metres() -> None:
    south, west, north, east = bounding_box(BERLIN, 50.0)
    top = to_metres(LatLon(north, BERLIN.lon), BERLIN).y
    bottom = to_metres(LatLon(south, BERLIN.lon), BERLIN).y
    right = to_metres(LatLon(BERLIN.lat, east), BERLIN).x
    left = to_metres(LatLon(BERLIN.lat, west), BERLIN).x
    height, width = top - bottom, right - left
    assert width == pytest.approx(height, rel=1e-6)
    assert height == pytest.approx(100.0, rel=1e-6)


def test_a_centroid_needs_points() -> None:
    with pytest.raises(ValueError):
        centroid([])


def test_the_centroid_sits_in_the_middle() -> None:
    square = [LatLon(52.4, 13.3), LatLon(52.4, 13.5), LatLon(52.6, 13.5), LatLon(52.6, 13.3)]
    c = centroid(square)
    assert c.lat == pytest.approx(52.5)
    assert c.lon == pytest.approx(13.4)


def test_it_works_south_of_the_equator_too() -> None:
    # Not a use case, but a cosine that only works for positive latitudes is a
    # trap for whoever reuses this.
    anchor = LatLon(-33.9, 18.4)
    assert to_metres(LatLon(-33.899, 18.4), anchor).y > 0
