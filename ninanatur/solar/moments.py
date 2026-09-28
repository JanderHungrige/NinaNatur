"""The directions light comes from, and what each is worth — split out of
`raster.py` (docs 117, 118) when it passed the 300 lines a module may have.

The sun at its sampled moments (`Moments`, `moments_for`) and any set of
directions the raster sums — the sun's, or the sky's patches (`Directions`).
`raster` still exports every name here, so nothing that imports them from it
has to change.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np

from ninanatur.solar.light import MINUTE_STEP, season_days
from ninanatur.solar.position import Location, sun_position
from ninanatur.solar.shading import MIN_ALTITUDE


@dataclass(frozen=True)
class Moments:
    """The sun at every sampled moment it is above `MIN_ALTITUDE`."""

    azimuth: np.ndarray
    altitude: np.ndarray
    month: np.ndarray
    #: East of due south: the morning half of a day.
    morning: np.ndarray
    #: Days sampled, for turning lit samples into a daily mean.
    days: int
    minute_step: int = MINUTE_STEP
    #: Days sampled in each month, indexed by the month (0 unused), for a
    #: month's own mean within the season (`solar.relative`).
    month_days: tuple[int, ...] = ()


@dataclass(frozen=True)
class Directions:
    """Where light comes from, and what each direction is worth: the sun at
    its sampled moments, or the patches of an overcast sky (`solar.sky`).

    Each direction that reaches a cell adds its `weight`, times what passes, to
    the sum named by its `group` — morning and afternoon for the sun, one sum
    for the sky. `month` says which leaves the crowns have."""

    azimuth: np.ndarray
    altitude: np.ndarray
    month: np.ndarray
    weight: np.ndarray
    group: np.ndarray
    groups: int


def sun_directions(moments: Moments) -> Directions:
    """The sun's moments as directions: each a sample's share of a daily mean
    hour, in the morning sum or the afternoon one."""
    share = moments.minute_step / 60 / moments.days if moments.days else 0.0
    return Directions(azimuth=moments.azimuth, altitude=moments.altitude, month=moments.month,
                      weight=np.full(moments.azimuth.shape, share),
                      group=np.where(moments.morning, 0, 1), groups=2)


def moments_for(location: Location, year: int = 2026, month: int | None = None) -> Moments:
    """The season's moments, or one month's, at the model's sampling."""
    days = season_days(year, month)
    found: list[tuple[float, float, int, bool]] = []
    for day in days:
        for minute in range(0, 24 * 60, MINUTE_STEP):
            sun = sun_position(location, day + timedelta(minutes=minute))
            if sun.altitude > MIN_ALTITUDE:
                found.append((sun.azimuth, sun.altitude, day.month, sun.azimuth < 180.0))
    month_days = tuple(sum(1 for day in days if day.month == m) for m in range(13))
    return moments_from(found, len(days), month_days=month_days)


def moments_from(found: list[tuple[float, float, int, bool]], days: int,
                 minute_step: int = MINUTE_STEP, month_days: tuple[int, ...] = ()) -> Moments:
    rows = np.array(found, dtype=float).reshape(-1, 4)
    return Moments(azimuth=rows[:, 0], altitude=rows[:, 1], month=rows[:, 2].astype(int),
                   morning=rows[:, 3].astype(bool), days=days, minute_step=minute_step,
                   month_days=month_days)


__all__ = ["Directions", "Moments", "moments_for", "moments_from", "sun_directions"]
