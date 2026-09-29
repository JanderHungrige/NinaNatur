"""Is the sampling fine enough? Measured against a converged answer (doc 115).

`solar/light.py` said of its one day in ten, every half hour: "fine enough that
the answer stops moving". Nobody had checked. Here each scene is answered
twice: by the model at its own sampling, and by the same shading test asked
every five minutes of every day, which has stopped moving — the first test
below shows it. The difference is what the sampling costs.

Measured when this was written (Wuppertal): the season up to 0.22 h low beside
a house (0.13 h in the open), a month up to 0.46 h (April, beside the house).
Most of it was the days skipped, not the half-hour steps. The bars are 0.1 h
for the season and 0.2 h for a month.

Both tests over the model's own sampling failed then, marked as strict expected
failures that named what would make them pass. Wave 26's feature 2 (doc 117)
did: the season every 10 minutes on every fifth day, a month every second day,
on the raster that pays for it. The marks came off with it, and so did the
test that pinned the old errors.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import cache

from ninanatur.solar.light import bed_light_value
from ninanatur.solar.position import Location, SunPosition, sun_position
from ninanatur.solar.raster import moments_for, parts_of, point_hours
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle, Point, is_shaded

WUPPERTAL = Location(51.25, 7.15)
SEASON_BAR_H = 0.1
MONTH_BAR_H = 0.2
MONTHS = (4, 6)

HOUSE_SOUTH = [Obstacle(footprint=[(-5, -13), (5, -13), (5, -8), (-5, -8)], height=9.0)]
ELL = [Obstacle(footprint=[(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)], height=9.0)]
HEDGE_EAST = [Obstacle(footprint=[(2, -10), (3, -10), (3, 10), (2, 10)], height=2.5)]

#: Open ground, a house to the south (just clear of it, and deep in its
#: shadow), the corner of an L, and a hedge that takes the morning.
SCENES: list[tuple[str, list[Obstacle], tuple[float, float]]] = [
    ("open", [], (0.0, 0.0)),
    ("house south, clear", HOUSE_SOUTH, (0.0, 0.0)),
    ("house south, behind", HOUSE_SOUTH, (0.0, -6.0)),
    ("corner of an L", ELL, (7.5, 7.5)),
    ("hedge east", HEDGE_EAST, (0.0, 0.0)),
]


@cache
def _suns(month: int | None, minutes: int) -> tuple[int, tuple[SunPosition, ...]]:
    """Every day of the season (or the month) and every `minutes`: the days
    counted, and the suns high enough to count."""
    first = datetime(2026, month or 3, 1, tzinfo=UTC)
    last = datetime(2026, 10, 31, tzinfo=UTC) if month is None else (
        (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1))
    suns: list[SunPosition] = []
    days = 0
    day = first
    while day <= last:
        days += 1
        for step in range(0, 24 * 60, minutes):
            sun = sun_position(WUPPERTAL, day + timedelta(minutes=step))
            if sun.altitude > MIN_ALTITUDE:
                suns.append(sun)
        day += timedelta(days=1)
    return days, tuple(suns)


def _converged(obstacles: list[Obstacle], at: tuple[float, float],
               month: int | None = None, minutes: int = 5) -> float:
    days, suns = _suns(month, minutes)
    point = Point(*at)
    lit = sum(1 for sun in suns if not any(is_shaded(point, o, sun) for o in obstacles))
    return lit * minutes / 60 / days


@cache
def _season_off() -> dict[str, float]:
    return {name: bed_light_value(WUPPERTAL, Point(*at), obstacles).sun_hours
            - _converged(obstacles, at)
            for name, obstacles, at in SCENES}


@cache
def _month_off() -> dict[tuple[int, str], float]:
    """A month as the model computes one: the raster, at a month's sampling."""
    def model(obstacles: list[Obstacle], at: tuple[float, float], month: int) -> float:
        return sum(point_hours(parts_of(obstacles), moments_for(WUPPERTAL, month=month), *at))
    return {(month, name): model(obstacles, at, month) - _converged(obstacles, at, month)
            for month in MONTHS for name, obstacles, at in SCENES}


def test_the_ruler_has_stopped_moving() -> None:
    """Five minutes against two, where the model's error was largest."""
    _, obstacles, at = SCENES[1]
    assert abs(_converged(obstacles, at) - _converged(obstacles, at, minutes=2)) < 0.02


def test_the_season_is_sampled_within_a_tenth_of_an_hour() -> None:
    off = _season_off()
    assert max(abs(v) for v in off.values()) < SEASON_BAR_H, off


def test_a_month_is_sampled_within_a_fifth_of_an_hour() -> None:
    off = _month_off()
    assert max(abs(v) for v in off.values()) < MONTH_BAR_H, off
