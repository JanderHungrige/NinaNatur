"""From sun hours to a bed's light value.

Samples the sun across the growing season, asks the shading model whether each
sample reaches the bed, and converts the resulting daily average into an
Ellenberg light value.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ninanatur.solar.position import Location, sun_position
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle, Point, is_shaded

# March to October. A plant's light experience in December does not decide where
# it can live, and including winter would drag every German garden into shade.
SEASON_START = (3, 1)
SEASON_END = (10, 31)

# One day every ten, sampled every half hour. Fine enough that the answer stops
# moving, coarse enough to stay well under a second per bed.
DAY_STEP = 10
MINUTE_STEP = 30

# Mean daily direct sun (hours) -> Ellenberg L, best-first.
#
# THIS IS A CONVENTION, NOT A MEASUREMENT. Sun hours are physical; Ellenberg L is
# an ecological indicator derived from where plants are found growing. It is a
# table so it can be argued with and adjusted in one place, and so nobody mistakes
# it for physics.
SUN_HOUR_BANDS: tuple[tuple[float, float], ...] = (
    (8.0, 8.0),   # full sun
    (6.0, 7.0),   # sunny
    (4.0, 6.0),   # light shade
    (2.5, 5.0),   # semi-shade
    (1.5, 4.0),   # shade
    (0.0, 3.0),   # deep shade
)


@dataclass(frozen=True)
class BedLight:
    """A bed's light value, with the evidence that produced it."""

    ellenberg_l: float
    sun_hours: float
    samples: int
    year: int


def ellenberg_from_sun_hours(sun_hours: float) -> float:
    """Apply the documented convention. See `SUN_HOUR_BANDS`."""
    for lower, value in SUN_HOUR_BANDS:
        if sun_hours >= lower:
            return value
    return SUN_HOUR_BANDS[-1][1]


def _season_days(year: int) -> list[datetime]:
    start = datetime(year, *SEASON_START, tzinfo=UTC)
    end = datetime(year, *SEASON_END, tzinfo=UTC)
    days: list[datetime] = []
    day = start
    while day <= end:
        days.append(day)
        day += timedelta(days=DAY_STEP)
    return days


def bed_light_value(
    location: Location,
    bed: Point,
    obstacles: list[Obstacle],
    year: int = 2026,
    height_above_ground: float = 0.0,
) -> BedLight:
    """Mean daily hours of direct sun on a bed, and the light value it implies.

    Returns the sun hours alongside the value: a bare number the user cannot
    trace back to their own obstacles is not explainable, and this one will
    surprise people.
    """
    days = _season_days(year)
    lit_minutes = 0
    samples = 0
    step = timedelta(minutes=MINUTE_STEP)

    for day in days:
        moment = day
        end_of_day = day + timedelta(days=1)
        while moment < end_of_day:
            samples += 1
            sun = sun_position(location, moment)
            if sun.altitude > MIN_ALTITUDE and not any(
                is_shaded(bed, obstacle, sun, height_above_ground)
                for obstacle in obstacles
            ):
                lit_minutes += MINUTE_STEP
            moment += step

    sun_hours = (lit_minutes / 60) / len(days) if days else 0.0
    return BedLight(
        ellenberg_l=ellenberg_from_sun_hours(sun_hours),
        sun_hours=round(sun_hours, 2),
        samples=samples,
        year=year,
    )
