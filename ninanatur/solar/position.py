"""Where the sun is, for a place and a moment.

The NOAA solar position algorithm, which is plain arithmetic — no dependency, no
network, no key. Accurate to well under a degree, which is far beyond what a
garden light estimate needs.

Conventions, stated once because getting them wrong yields plausible but
confidently wrong numbers rather than an error:
  * azimuth  — degrees clockwise from north (0 N, 90 E, 180 S, 270 W)
  * altitude — degrees above the horizon, negative below
  * times    — UTC; the garden's local clock is irrelevant to the geometry
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

# ~11 km. Solar angles do not measurably change over that distance, so the extra
# precision buys nothing and a garden's exact coordinates are personal data.
LOCATION_PRECISION = 1


@dataclass(frozen=True)
class Location:
    """A garden's position, deliberately coarse."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "latitude", round(self.latitude, LOCATION_PRECISION))
        object.__setattr__(self, "longitude", round(self.longitude, LOCATION_PRECISION))


@dataclass(frozen=True)
class SunPosition:
    """The sun's place in the sky."""

    altitude: float
    azimuth: float

    @property
    def is_up(self) -> bool:
        return self.altitude > 0


def _julian_day(when: datetime) -> float:
    """Julian day number, including the fractional day."""
    year, month = when.year, when.month
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    day = (
        when.day
        + (when.hour + when.minute / 60 + when.second / 3600) / 24
    )
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )


def sun_position(location: Location, when: datetime) -> SunPosition:
    """Sun altitude and azimuth at a location and moment (UTC)."""
    jd = _julian_day(when)
    t = (jd - 2451545.0) / 36525.0

    # Mean longitude and anomaly of the sun.
    mean_long = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    mean_anom = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    eccentricity = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)

    # Equation of the centre, and from it the true and apparent longitude.
    m = math.radians(mean_anom)
    centre = (
        math.sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + math.sin(2 * m) * (0.019993 - 0.000101 * t)
        + math.sin(3 * m) * 0.000289
    )
    true_long = mean_long + centre
    omega = 125.04 - 1934.136 * t
    apparent_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))

    # Obliquity of the ecliptic, corrected for nutation.
    seconds = 21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))
    obliquity = 23.0 + (26.0 + seconds / 60.0) / 60.0
    obliquity_corr = obliquity + 0.00256 * math.cos(math.radians(omega))

    declination = math.degrees(
        math.asin(
            math.sin(math.radians(obliquity_corr)) * math.sin(math.radians(apparent_long))
        )
    )

    # Equation of time, in minutes.
    y = math.tan(math.radians(obliquity_corr / 2)) ** 2
    l0 = math.radians(mean_long)
    eq_time = 4 * math.degrees(
        y * math.sin(2 * l0)
        - 2 * eccentricity * math.sin(m)
        + 4 * eccentricity * y * math.sin(m) * math.cos(2 * l0)
        - 0.5 * y * y * math.sin(4 * l0)
        - 1.25 * eccentricity * eccentricity * math.sin(2 * m)
    )

    minutes_utc = when.hour * 60 + when.minute + when.second / 60
    true_solar_time = (minutes_utc + eq_time + 4 * location.longitude) % 1440
    # true_solar_time is already reduced mod 1440, so this always maps into
    # -180..180 — negative before local solar noon, positive after.
    hour_angle = true_solar_time / 4 - 180

    lat = math.radians(location.latitude)
    dec = math.radians(declination)
    ha = math.radians(hour_angle)

    cos_zenith = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith = math.degrees(math.acos(cos_zenith))
    altitude = 90.0 - zenith

    # Azimuth from north, clockwise. The acos gives an angle measured from due
    # south, so it needs NOAA's half-day correction — afternoon and morning fold
    # in opposite directions. Using 360 - az instead puts the noon sun in the
    # north, which is wrong in a way the altitude tests cannot catch.
    denominator = math.cos(lat) * math.sin(math.radians(zenith))
    if abs(denominator) < 1e-9:
        return SunPosition(altitude=altitude, azimuth=180.0)

    cos_az = (math.sin(lat) * cos_zenith - math.sin(dec)) / denominator
    cos_az = max(-1.0, min(1.0, cos_az))
    az = math.degrees(math.acos(cos_az))
    azimuth = (az + 180.0) % 360.0 if hour_angle > 0 else (540.0 - az) % 360.0
    return SunPosition(altitude=altitude, azimuth=azimuth)
