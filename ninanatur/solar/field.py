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

import math
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
    #: The receiving height the polygon was swept for — the **lowest** ground in
    #: the garden, so the polygon is a superset of every real shadow. A point
    #: standing higher than this needs the exact check below; on flat ground
    #: nothing ever does, and the fast path is the only path.
    floor: float = 0.0
    #: The absolute height of the thing casting this, and the sun's tangent at
    #: this moment. Together they say how far the shadow reaches onto a point at
    #: any height: (top - z) / tan(altitude).
    top: float = 0.0
    tan_altitude: float = 1.0
    #: The footprint turned so the shadow runs along -y, and the rotation that
    #: put it there. Then "how far must the shadow reach to arrive here" is one
    #: interval comparison rather than a second polygon.
    aligned: tuple[tuple[float, float], ...] = ()
    sin_azimuth: float = 0.0
    cos_azimuth: float = 1.0
    #: True while the sun is east of due south. The two halves of a day are not
    #: interchangeable: afternoon sun is hotter and harsher, and a great many
    #: species sold as *Halbschatten* want the morning specifically.
    morning: bool = True

    def covers_point(self, x: float, y: float, z: float = 0.0) -> bool:
        """Is this point in this shadow, standing at this height?

        Three tests, cheapest first, and on flat ground the third never runs:
        the box rejects most shadows in four comparisons, the polygon rejects
        the rest, and only a point standing **above** the height the polygon was
        swept for needs asking how far the shadow actually reaches.
        """
        if not (self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y):
            return False
        if not covers(self.polygon, (x, y)):
            return False
        if z >= self.top:
            # Level with the roof or above it. Nothing that is entirely below a
            # point can shade it, whatever the geometry says — and without this
            # a point standing inside a footprint at its own ridge height came
            # back shaded, because the distance it needed the shadow to travel
            # was negative and so was the reach.
            return False
        if z <= self.floor or not self.aligned:
            return True
        return self._reaches(x, y, z)

    def _reaches(self, x: float, y: float, z: float) -> bool:
        """Does the shadow still arrive here once the point is raised to z?

        The swept hull of a footprint is that footprint plus a segment, so a
        point is inside it exactly when the ray back towards the sun meets the
        footprint within the shadow's length. Turned into the frame where the
        shadow runs along -y, that is: does the vertical line through the point
        cross the footprint, and is its near edge within reach?
        """
        ax = x * self.cos_azimuth - y * self.sin_azimuth
        ay = x * self.sin_azimuth + y * self.cos_azimuth
        near = _near_edge(self.aligned, ax, ay)
        if near is None:
            return False
        return (self.top - z) / self.tan_altitude >= near


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

    def sun_hours_at(self, x: float, y: float, z: float = 0.0) -> float:
        """Mean daily hours of direct sun at this point."""
        morning, afternoon = self.halves_at(x, y, z)
        return morning + afternoon

    def halves_at(self, x: float, y: float, z: float = 0.0) -> tuple[float, float]:
        """Mean daily sun hours before and after the sun crosses due south.

        Due south rather than a computed solar noon: in the northern hemisphere
        the sun is east of south all morning and west of it all afternoon, so
        the azimuth already says which half a sample is in — exactly, and
        without a second calculation per day.

        `z` is the ground this point stands on. Zero is the flat world every
        shadow in this project was computed in until Wave 17: a point uphill of
        a house sees over it, and a point below it does not.
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
                if shadow.covers_point(x, y, z):
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


def _near_edge(
    aligned: tuple[tuple[float, float], ...], x: float, y: float
) -> float | None:
    """How far the shadow must reach from the footprint to arrive at (x, y).

    Both coordinates are in the aligned frame, where the shadow runs along -y,
    so the footprint's near edge above the point is the distance the shadow has
    to cover. Returns None when the line through the point misses the footprint
    entirely, or when the point is beyond its far edge — sunward of the thing
    casting, where no shadow of it ever falls.
    """
    lo: float | None = None
    hi: float | None = None
    n = len(aligned)
    for i in range(n):
        ax, ay = aligned[i]
        bx, by = aligned[(i + 1) % n]
        if (ax > x) == (bx > x):
            continue
        cut = ay + (by - ay) * (x - ax) / (bx - ax)
        lo = cut if lo is None or cut < lo else lo
        hi = cut if hi is None or cut > hi else hi
    if lo is None or hi is None or y > hi:
        return None
    return lo - y


def shadow_field(
    location: Location,
    obstacles: list[Obstacle],
    year: int = 2026,
    height_above_ground: float = 0.0,
    ground_floor: float = 0.0,
) -> ShadowField:
    """Build the season's shadows for one garden.

    `height_above_ground` belongs here rather than at the point, because it
    changes each obstacle's effective height and therefore every polygon. A
    garden with beds at two different heights needs two fields, which is still
    two rather than one per point.

    `ground_floor` is the **lowest** ground in the garden. Every polygon is swept
    onto that height, which makes it a superset of the shadow that reaches any
    real point — so the box and polygon tests stay exactly as fast as they were,
    and only a point standing higher pays for the exact check. On flat ground
    the floor is zero, every point is at zero, and nothing ever does.
    """
    days = _season_days(year)
    step = timedelta(minutes=MINUTE_STEP)
    receiver = ground_floor + height_above_ground
    lifted = [
        Obstacle(
            footprint=o.footprint,
            height=o.top - receiver,
            base=receiver,
            transmission=o.transmission,
            bare_transmission=o.bare_transmission,
        )
        for o in obstacles
        if o.top - receiver > 0
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
    azimuth = math.radians(sun.azimuth)
    sin_a, cos_a = math.sin(azimuth), math.cos(azimuth)
    return ShadowAt(
        floor=obstacle.base,
        top=obstacle.top,
        tan_altitude=math.tan(math.radians(sun.altitude)),
        aligned=tuple(
            (px * cos_a - py * sin_a, px * sin_a + py * cos_a)
            for px, py in obstacle.footprint
        ),
        sin_azimuth=sin_a,
        cos_azimuth=cos_a,
        min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys), polygon=polygon,
        transmission=obstacle.transmission_in(month),
    )




