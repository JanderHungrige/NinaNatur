"""The one light a drawing has — Wave 24, feature 4 (doc 99).

The plan's day playback moves the sun through the 15th of a month (doc 38).
A *drawing* does not: it is made at one moment, and everything standing in it
throws its shadow the same way. This is that moment, and the offset it gives a
thing of a given height.

Mid-June, three hours after solar noon. Solar rather than clock time because
the clock is a political line — Vigo and Wuppertal share a time zone and an
hour and a half of sun — and because the drawing only wants "a high afternoon
sun", which is the same thing everywhere at that hour angle. The sun is then
high, so the shadow is short, and in the west, so it falls to the east: the
plan reads as afternoon at a glance.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from ninanatur.solar.position import Location, SunPosition, sun_position
from ninanatur.solar.shading import shadow_length

#: The drawing's date. A year is needed for the arithmetic and nothing turns on
#: which one: the sun of mid-June repeats.
REFERENCE_YEAR = 2026
REFERENCE_MONTH = 6
REFERENCE_DAY = 15
#: Hours after midnight, in the garden's own solar time.
REFERENCE_SOLAR_HOUR = 15.0
#: Degrees of longitude the earth turns in an hour.
DEGREES_AN_HOUR = 15.0


def drawing_moment(longitude: float) -> datetime:
    """The reference moment in UTC, for a garden at this longitude."""
    noon = datetime(REFERENCE_YEAR, REFERENCE_MONTH, REFERENCE_DAY, tzinfo=UTC)
    return noon + timedelta(hours=REFERENCE_SOLAR_HOUR - longitude / DEGREES_AN_HOUR)


def drawing_sun(location: Location) -> SunPosition:
    """Where the sun stands over this garden when its plan is drawn."""
    return sun_position(location, drawing_moment(location.longitude))


def drawing_shadow(height_m: float | None, sun: SunPosition) -> tuple[float, float] | None:
    """How far and which way a thing of this height throws its shadow, in
    metres, x east and y north — or None when there is nothing to draw.

    None rather than a zero offset, so a drawing leaves the mark out instead of
    laying a shadow exactly under the thing that casts it.
    """
    if height_m is None or height_m <= 0:
        return None
    length = shadow_length(height_m, sun.altitude)
    if length <= 0:
        return None
    # Away from the sun, as `shading.shadow_polygon` sweeps a footprint.
    azimuth = math.radians(sun.azimuth)
    return -math.sin(azimuth) * length, -math.cos(azimuth) * length


__all__ = [
    "REFERENCE_DAY",
    "REFERENCE_MONTH",
    "REFERENCE_SOLAR_HOUR",
    "REFERENCE_YEAR",
    "drawing_moment",
    "drawing_shadow",
    "drawing_sun",
]
