"""The projection, against points whose coordinates are known independently.

This is the kind of code that is quietly wrong by thirty metres and only shows
up much later as a garden whose hill is in the wrong direction. So it is checked
against things that can be looked up rather than against itself.
"""
from __future__ import annotations

import math

import pytest

from ninanatur.geo.utm import central_meridian, to_latlon, to_utm, zone_for


def test_the_central_meridian_is_exactly_the_false_easting() -> None:
    """The one value in the whole system that is exact by definition: on zone
    32's central meridian, easting is 500000 m, at any latitude."""
    for latitude in (47.0, 51.0, 55.0):
        easting, _ = to_utm(latitude, 9.0, 32)
        assert easting == pytest.approx(500000.0, abs=1e-3)


def test_koeln_dom_lands_on_koeln_dom() -> None:
    """A published control point rather than a round trip: 50.9413 N, 6.9583 E
    is UTM32 356560 / 5645282."""
    easting, northing = to_utm(50.9413, 6.9583, 32)
    assert easting == pytest.approx(356560, abs=2)
    assert northing == pytest.approx(5645282, abs=2)


def test_zone_33_works_too() -> None:
    """Half of these services publish in 33, and a request sent in the wrong
    zone does not fail — it returns ground a few hundred kilometres away."""
    easting, northing = to_utm(52.3906, 13.0645, 33)
    assert 300000 < easting < 400000
    assert 5_800_000 < northing < 5_815_000


@pytest.mark.parametrize(
    ("latitude", "longitude", "zone"),
    [
        (47.4211, 10.9853, 32),   # Zugspitze, the southern edge
        (54.9081, 8.3126, 32),    # Sylt, the northern
        (51.0, 6.0, 32),          # far west in its zone, convergence at its worst
        (51.0, 12.0, 33),         # far west in zone 33
        (52.5200, 13.4050, 33),   # Berlin
    ],
)
def test_the_round_trip_comes_back_to_the_same_place(
    latitude: float, longitude: float, zone: int
) -> None:
    """Forward then inverse, to within a millimetre of ground. The inverse is
    what keeps north pointing north when a raster is pasted into the garden's
    frame, so it has to be as good as the forward."""
    back_lat, back_lon = to_latlon(*to_utm(latitude, longitude, zone), zone)
    assert back_lat == pytest.approx(latitude, abs=1e-8)
    assert back_lon == pytest.approx(longitude, abs=1e-8)


def test_grid_north_is_not_true_north_and_the_inverse_knows_it() -> None:
    """The reason the inverse exists at all.

    Step 100 m due grid-north in UTM from a point well off the central meridian,
    convert back, and the bearing that comes out is not 0°. That difference is
    the meridian convergence, and pasting a raster in without it would rotate
    every slope and every hill by that much.
    """
    latitude, longitude, zone = 51.0, 6.0, 32
    easting, northing = to_utm(latitude, longitude, zone)
    north_lat, north_lon = to_latlon(easting, northing + 100.0, zone)

    east_m = (north_lon - longitude) * 111_320 * math.cos(math.radians(latitude))
    north_m = (north_lat - latitude) * 111_320
    bearing = math.degrees(math.atan2(east_m, north_m))

    assert abs(bearing) > 1.5, f"convergence should be about 2° here, got {bearing:.2f}°"
    assert abs(bearing) < 3.0


def test_the_zone_rule_matches_the_meridians_it_names() -> None:
    assert zone_for(9.0) == 32
    assert zone_for(13.4) == 33
    assert central_meridian(32) == 9
    assert central_meridian(33) == 15
