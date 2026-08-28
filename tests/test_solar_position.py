"""Solar position, checked against physics rather than another implementation.

A wrong sun position produces plausible, confidently wrong light values rather
than an error — so every anchor here is derivable from first principles.
"""
from datetime import UTC, datetime

import pytest

from ninanatur.solar.position import Location, sun_position

BERLIN = Location(latitude=52.52, longitude=13.40)
EQUATOR = Location(latitude=0.0, longitude=0.0)
AXIAL_TILT = 23.44


def test_equator_equinox_noon_has_the_sun_overhead() -> None:
    """The defining case: equinox, equator, solar noon."""
    pos = sun_position(EQUATOR, datetime(2026, 3, 20, 12, 7, tzinfo=UTC))
    assert pos.altitude == pytest.approx(90.0, abs=1.0)


def test_berlin_summer_solstice_noon_matches_90_minus_lat_plus_tilt() -> None:
    pos = sun_position(BERLIN, datetime(2026, 6, 21, 11, 0, tzinfo=UTC))
    assert pos.altitude == pytest.approx(90 - BERLIN.latitude + AXIAL_TILT, abs=1.0)


def test_berlin_winter_solstice_noon_matches_90_minus_lat_minus_tilt() -> None:
    pos = sun_position(BERLIN, datetime(2026, 12, 21, 11, 0, tzinfo=UTC))
    assert pos.altitude == pytest.approx(90 - BERLIN.latitude - AXIAL_TILT, abs=1.0)


def test_the_sun_is_due_south_at_its_daily_highest_point() -> None:
    """Northern hemisphere: the day's highest sun is due south.

    Found by searching for the maximum rather than assuming a clock time — solar
    noon in Berlin is around 11:08 UTC, not 11:00, because 13.4°E shifts it and
    the equation of time shifts it again.
    """
    samples = [
        sun_position(BERLIN, datetime(2026, 6, 21, m // 60, m % 60, tzinfo=UTC))
        for m in range(9 * 60, 13 * 60)
    ]
    highest = max(samples, key=lambda p: p.altitude)
    assert highest.azimuth == pytest.approx(180.0, abs=1.0)


def test_the_sun_climbs_to_noon_and_falls_after() -> None:
    """The arc has one maximum — a sign error in the hour angle would break this."""
    def altitude_at(hour: int) -> float:
        return sun_position(BERLIN, datetime(2026, 6, 21, hour, 0, tzinfo=UTC)).altitude

    assert altitude_at(6) < altitude_at(9) < altitude_at(11)
    assert altitude_at(11) > altitude_at(14) > altitude_at(17)


def test_azimuth_travels_east_to_south_to_west() -> None:
    """Catches the convention error that put the noon sun in the north."""
    def azimuth_at(hour: int) -> float:
        return sun_position(BERLIN, datetime(2026, 6, 21, hour, 0, tzinfo=UTC)).azimuth

    assert azimuth_at(4) < azimuth_at(8) < azimuth_at(11) < azimuth_at(14) < azimuth_at(18)
    assert azimuth_at(4) < 90, "early morning sun is north-east"
    assert azimuth_at(18) > 270, "late evening sun is north-west"


def test_the_sun_is_below_the_horizon_at_midnight() -> None:
    pos = sun_position(BERLIN, datetime(2026, 12, 21, 23, 0, tzinfo=UTC))
    assert pos.altitude < 0


def test_the_sun_rises_in_the_east_and_sets_in_the_west() -> None:
    morning = sun_position(BERLIN, datetime(2026, 6, 21, 4, 0, tzinfo=UTC))
    evening = sun_position(BERLIN, datetime(2026, 6, 21, 18, 0, tzinfo=UTC))
    assert 30 < morning.azimuth < 120, "morning sun is in the eastern half"
    assert 240 < evening.azimuth < 330, "evening sun is in the western half"


def test_summer_days_are_longer_than_winter_days() -> None:
    """Integrates the whole calculation rather than one instant."""
    def daylight_hours(day: datetime) -> float:
        return sum(
            0.5
            for h in range(0, 48)
            if sun_position(BERLIN, day.replace(hour=h // 2, minute=(h % 2) * 30)).altitude > 0
        )

    summer = daylight_hours(datetime(2026, 6, 21, tzinfo=UTC))
    winter = daylight_hours(datetime(2026, 12, 21, tzinfo=UTC))
    assert summer > 15, "Berlin midsummer has ~16.5 h of daylight"
    assert winter < 9, "Berlin midwinter has ~7.5 h of daylight"


def test_location_is_rounded_to_a_tenth_of_a_degree() -> None:
    """~11 km. Solar angles do not care; a garden's exact coordinates are personal."""
    precise = Location(latitude=52.5170365, longitude=13.3888599)
    assert precise.latitude == 52.5
    assert precise.longitude == 13.4


def test_rounding_does_not_meaningfully_change_the_answer() -> None:
    """The justification for rounding, asserted rather than assumed."""
    when = datetime(2026, 6, 21, 11, 0, tzinfo=UTC)
    rounded = sun_position(Location(52.5, 13.4), when)
    nearby = sun_position(Location(52.55, 13.44), when)
    assert rounded.altitude == pytest.approx(nearby.altitude, abs=0.2)
