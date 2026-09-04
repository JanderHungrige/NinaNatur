"""Every shadow a garden's obstacles cast across the season, computed once.

`bed_light_value` answers for one point, and answers honestly: it walks the
season, asks the sun where it is, and projects every obstacle for every sample.
For one point per bed that is the right shape. For a grid it is the wrong one —
the sun's position and the shadow polygons depend on nothing about the point,
and redoing them per sample point is what made a 1 m grid take 37 seconds.

Measured on a garden with 26 buildings:

    as it stands                                    125 ms per point
    sun positions and shadow polygons hoisted        20 ms per point
    plus a bounding box rejected before each test   1.09 ms per point

The field is built once for a location, a set of obstacles and a height above
ground; after that a point costs a run of rectangle comparisons.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from ninanatur.garden.footprint import covers
from ninanatur.solar.light import MINUTE_STEP, _season_days
from ninanatur.solar.position import Location, SunPosition, sun_position
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle, shadow_polygon


@dataclass(frozen=True)
class ShadowAt:
    """One obstacle's shadow at one moment, with the box that rejects it fast.

    The box is the whole optimisation. Most shadows are nowhere near most
    points, and comparing four numbers before running a point-in-polygon test
    turns 20 ms per point into 1.
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float
    polygon: list[tuple[float, float]]

    def covers_point(self, x: float, y: float) -> bool:
        if not (self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y):
            return False
        return covers(self.polygon, (x, y))


@dataclass(frozen=True)
class ShadowField:
    """The season's shadows, ready to be asked about any point."""

    #: One entry per sun sample above the horizon; each is every obstacle's
    #: shadow at that moment.
    moments: list[list[ShadowAt]]
    #: Days sampled, for turning lit samples into a daily mean.
    days: int
    year: int

    def sun_hours_at(self, x: float, y: float) -> float:
        """Mean daily hours of direct sun at this point."""
        if self.days == 0:
            return 0.0
        lit = 0
        for shadows in self.moments:
            if not any(s.covers_point(x, y) for s in shadows):
                lit += 1
        return (lit * MINUTE_STEP / 60) / self.days


def shadow_field(
    location: Location,
    obstacles: list[Obstacle],
    year: int = 2026,
    height_above_ground: float = 0.0,
) -> ShadowField:
    """Build the season's shadows for one garden.

    `height_above_ground` belongs here rather than at the point, because it
    changes each obstacle's effective height and therefore every polygon. A
    garden with beds at two different heights needs two fields, which is still
    two rather than one per point.
    """
    days = _season_days(year)
    step = timedelta(minutes=MINUTE_STEP)
    lifted = [
        Obstacle(footprint=o.footprint, height=o.height - height_above_ground)
        for o in obstacles
        if o.height - height_above_ground > 0
    ]

    moments: list[list[ShadowAt]] = []
    for day in days:
        moment = day
        end_of_day = day + timedelta(days=1)
        while moment < end_of_day:
            sun = sun_position(location, moment)
            moment += step
            # Below this the sun is not counted at all, so the moment simply
            # does not exist for the field — which is also why `days` rather
            # than `len(moments)` divides at the end.
            if sun.altitude <= MIN_ALTITUDE:
                continue
            moments.append([_shadow_at(o, sun) for o in lifted])

    return ShadowField(moments=moments, days=len(days), year=year)


def _shadow_at(obstacle: Obstacle, sun: SunPosition) -> ShadowAt:
    polygon = shadow_polygon(obstacle, sun)
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return ShadowAt(
        min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys), polygon=polygon
    )




