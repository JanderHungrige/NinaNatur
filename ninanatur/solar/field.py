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
    #: What passes through this shadow. Zero for anything built.
    transmission: float = 0.0
    #: True while the sun is east of due south. The two halves of a day are not
    #: interchangeable: afternoon sun is hotter and harsher, and a great many
    #: species sold as *Halbschatten* want the morning specifically.
    morning: bool = True

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
    #: Whether each moment is a morning one, in step with `moments`.
    halves: list[bool]
    #: Days sampled, for turning lit samples into a daily mean.
    days: int
    year: int

    def sun_hours_at(self, x: float, y: float) -> float:
        """Mean daily hours of direct sun at this point."""
        morning, afternoon = self.halves_at(x, y)
        return morning + afternoon

    def halves_at(self, x: float, y: float) -> tuple[float, float]:
        """Mean daily sun hours before and after the sun crosses due south.

        Due south rather than a computed solar noon: in the northern hemisphere
        the sun is east of south all morning and west of it all afternoon, so
        the azimuth already says which half a sample is in — exactly, and
        without a second calculation per day.
        """
        if self.days == 0:
            return (0.0, 0.0)
        before = 0.0
        after = 0.0
        for moment, morning in zip(self.moments, self.halves, strict=True):
            # Multiplied, not counted: two crowns over one spot each take their
            # share, and a wall takes all of it whatever else is in the way.
            through = 1.0
            for shadow in moment:
                if shadow.covers_point(x, y):
                    through *= shadow.transmission
                    if through == 0.0:
                        break
            if through == 0.0:
                continue
            if morning:
                before += through
            else:
                after += through
        hours = MINUTE_STEP / 60 / self.days
        return (before * hours, after * hours)


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
        Obstacle(
            footprint=o.footprint,
            height=o.height - height_above_ground,
            transmission=o.transmission,
            bare_transmission=o.bare_transmission,
        )
        for o in obstacles
        if o.height - height_above_ground > 0
    ]

    moments: list[list[ShadowAt]] = []
    halves: list[bool] = []
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
            moments.append([_shadow_at(o, sun, day.month) for o in lifted])
            halves.append(sun.azimuth < 180.0)

    return ShadowField(moments=moments, halves=halves, days=len(days), year=year)


def _shadow_at(obstacle: Obstacle, sun: SunPosition, month: int) -> ShadowAt:
    polygon = shadow_polygon(obstacle, sun)
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return ShadowAt(
        min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys), polygon=polygon,
        transmission=obstacle.transmission_in(month),
    )




