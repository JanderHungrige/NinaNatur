"""The shadows of one day, hour by hour.

The season grid says how much sun a spot gets over a year. It cannot say *when*,
and "when" is what somebody watching a shadow cross their garden is asking. This
is that: one middling day, the shadows at each half hour.

Computed rather than stored. It is one day rather than a season — a fraction of
the grid's work — and nobody watches the same day twice in a row.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ninanatur.garden.models import Garden
from ninanatur.garden.objects import ObjectKind, casts_shadow
from ninanatur.garden.roofs import Roof, shading_height
from ninanatur.solar.light import MINUTE_STEP
from ninanatur.solar.position import Location, sun_position
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle, shadow_polygon

#: The months a garden is watched in. The same window the light model uses, and
#: for the same reason: December says nothing about where a plant can live.
MONTHS: tuple[int, ...] = tuple(range(3, 11))

#: The 15th. A month's first and last day differ by a fortnight of sun, and the
#: middle is the one that represents the month rather than either edge.
MID_MONTH_DAY = 15


@dataclass(frozen=True)
class Frame:
    """Every shadow in the garden at one moment."""

    minute: int
    altitude: float
    azimuth: float
    polygons: list[list[tuple[float, float]]]


@dataclass(frozen=True)
class Day:
    month: int
    day: int
    frames: list[Frame]


def shadow_day(conn: object, garden: Garden, month: int, year: int = 2026) -> Day:
    """The shadows across a middling day of this month.

    `conn` is accepted and unused: the plantings are already on the garden, and
    taking it keeps the signature honest for the day a woody planting's canopy
    has to be looked up here rather than passed in.
    """
    del conn
    obstacles = _casting(garden)
    location = Location(latitude=garden.latitude, longitude=garden.longitude)
    start = datetime(year, month, MID_MONTH_DAY, tzinfo=UTC)
    step = timedelta(minutes=MINUTE_STEP)

    frames: list[Frame] = []
    moment = start
    while moment < start + timedelta(days=1):
        sun = sun_position(location, moment)
        if sun.altitude > MIN_ALTITUDE:
            frames.append(
                Frame(
                    minute=moment.hour * 60 + moment.minute,
                    altitude=sun.altitude,
                    azimuth=sun.azimuth,
                    polygons=[shadow_polygon(o, sun) for o in obstacles],
                )
            )
        moment += step

    return Day(month=month, day=MID_MONTH_DAY, frames=frames)


def _casting(garden: Garden) -> list[Obstacle]:
    """Everything in the garden that throws a shadow, at its shading height.

    The same rule the light model applies, and deliberately not a second copy of
    it: a height of None is an element nobody has measured, and treating it as
    zero would be a claim.
    """
    return [
        Obstacle(
            footprint=element.footprint,
            height=shading_height(
                element.height, Roof(element.roof), element.eaves_m
            ),
        )
        for element in garden.obstacles
        if element.height is not None and casts_shadow(ObjectKind(element.kind))
    ]
