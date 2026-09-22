"""Is the sampling fine enough? Measured against a converged answer (doc 115).

`solar/light.py` said of its one day in ten, every half hour: "fine enough that
the answer stops moving". Nobody had checked. Here each scene is answered
twice: by the model at its own sampling, and by the same shading test asked
every five minutes of every day, which has stopped moving — the first test
below shows it. The difference is what the sampling costs.

Measured when this was written (Wuppertal): the season up to 0.22 h low beside
a house (0.13 h in the open), a month up to 0.46 h (April, beside the house).
Most of it is the days skipped, not the half-hour steps. The bars are 0.1 h
for the season and 0.2 h for a month.

The two tests over the model's own sampling fail today, on purpose and
strictly, each naming what makes it pass: feature 2's season sampling (10 min,
every 5th day) measured 0.04 h; a month needs every 2nd day at 10 min (0.10 h;
every 5th day, which a month already has, leaves 0.34 h). A strict expected
failure turns red the day it starts passing, so its mark comes off with the
change that earns it. Until then the last test pins every number both of them
compute, so neither can go on failing for some other reason.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import cache

import pytest

from ninanatur.solar.field import shadow_field
from ninanatur.solar.light import bed_light_value
from ninanatur.solar.position import Location, SunPosition, sun_position
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle, Point, is_shaded

WUPPERTAL = Location(51.25, 7.15)
SEASON_BAR_H = 0.1
MONTH_BAR_H = 0.2
MONTHS = (4, 6)
SEASON_NEEDS = "Wave 26 feature 2: the season sampled every 10 min, every 5th day (doc 115)"
MONTH_NEEDS = "Wave 26 feature 2: a month sampled every 10 min, every 2nd day (doc 115)"

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

#: What today's sampling misses by, in hours (model minus converged): the
#: season, April and June, measured 2026-09-22.
MEASURED: dict[str, tuple[float, float, float]] = {
    "open": (-0.131, -0.172, -0.142),
    "house south, clear": (-0.219, -0.458, -0.142),
    "house south, behind": (-0.217, -0.339, -0.278),
    "corner of an L": (-0.137, -0.169, -0.269),
    "hedge east": (-0.021, -0.114, 0.150),
}


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
    return {(month, name): shadow_field(WUPPERTAL, obstacles, month=month).sun_hours_at(*at)
            - _converged(obstacles, at, month)
            for month in MONTHS for name, obstacles, at in SCENES}


def test_the_ruler_has_stopped_moving() -> None:
    """Five minutes against two, where the model's error was largest."""
    _, obstacles, at = SCENES[1]
    assert abs(_converged(obstacles, at) - _converged(obstacles, at, minutes=2)) < 0.02


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=SEASON_NEEDS)
def test_the_season_is_sampled_within_a_tenth_of_an_hour() -> None:
    off = _season_off()
    assert max(abs(v) for v in off.values()) < SEASON_BAR_H, off


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=MONTH_NEEDS)
def test_a_month_is_sampled_within_a_fifth_of_an_hour() -> None:
    off = _month_off()
    assert max(abs(v) for v in off.values()) < MONTH_BAR_H, off


def test_the_errors_are_the_ones_measured() -> None:
    """Every number the two expected failures compute, pinned, so a change
    that made them fail for another reason — a concave corner read wrong in
    June, say — cannot pass for the known one. Each value goes when its mark
    goes."""
    season, month = _season_off(), _month_off()
    for name, (whole, april, june) in MEASURED.items():
        assert season[name] == pytest.approx(whole, abs=0.03), (name, "season")
        assert month[(4, name)] == pytest.approx(april, abs=0.03), (name, "April")
        assert month[(6, name)] == pytest.approx(june, abs=0.03), (name, "June")
