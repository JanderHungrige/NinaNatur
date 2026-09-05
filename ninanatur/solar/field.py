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
from dataclasses import dataclass, field
from datetime import timedelta

from ninanatur.garden.footprint import covers
from ninanatur.solar.light import MINUTE_STEP, _season_days
from ninanatur.solar.position import Location, SunPosition, sun_position
from ninanatur.solar.reach import near_edge
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
        near = near_edge(self.aligned, ax, ay)
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
    #: Each moment's sun azimuth and altitude, in step with `moments`. Kept so a
    #: horizon can be consulted without the sun being recomputed — the whole
    #: reason this field exists is that sun positions are expensive.
    sun: list[tuple[float, float]] = field(default_factory=list)
    #: How high the land stands in each degree of azimuth, for the garden as a
    #: whole. Five kilometres of terrain does not change across twenty metres of
    #: plot, so this is measured once — but it is *combined* with each cell's own
    #: slope before being consulted, which is why the query takes a ring rather
    #: than reading this one.
    horizon: list[float] = field(default_factory=list)

    def sun_hours_at(
        self, x: float, y: float, z: float = 0.0, ring: list[float] | None = None
    ) -> float:
        """Mean daily hours of direct sun at this point."""
        morning, afternoon = self.halves_at(x, y, z, ring)
        return morning + afternoon

    def moments_under(
        self, ring: tuple[float, ...] | None
    ) -> list[tuple[list[ShadowAt], bool]]:
        """The moments the sun actually clears the land in, for one sky.

        Dropping them here rather than testing per point is what keeps the ring
        from costing anything: a garden in a valley ends up iterating *fewer*
        moments than a flat one, so the feature with the largest effect in hill
        country is also the only one in this model that makes it faster.
        """
        pairs = list(zip(self.moments, self.halves, strict=True))
        if not ring:
            return pairs
        return [
            pair
            for index, pair in enumerate(pairs)
            if index >= len(self.sun)
            or self.sun[index][1] >= ring[int(round(self.sun[index][0])) % len(ring)]
        ]

    def halves_at(
        self,
        x: float,
        y: float,
        z: float = 0.0,
        ring: list[float] | None = None,
        under: list[tuple[list[ShadowAt], bool]] | None = None,
    ) -> tuple[float, float]:
        """Mean daily sun hours before and after the sun crosses due south.

        Due south rather than a computed solar noon: in the northern hemisphere
        the sun is east of south all morning and west of it all afternoon, so
        the azimuth already says which half a sample is in — exactly, and
        without a second calculation per day.

        `z` is the ground this point stands on. Zero is the flat world every
        shadow in this project was computed in until Wave 17: a point uphill of
        a house sees over it, and a point below it does not.

        `ring` is how high the land stands in each degree of azimuth as seen
        from **this** point — the hills beyond the plot and the slope underfoot,
        whichever blocks the sun first. `under` is the same thing already
        applied, for a caller with many points sharing one sky; on a uniform
        hillside that is every cell in the garden.
        """
        if self.days == 0:
            return (0.0, 0.0)
        before = 0.0
        after = 0.0
        if under is None:
            under = self.moments_under(tuple(ring) if ring else None)
        for moment, morning in under:
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



def shadow_field(
    location: Location,
    obstacles: list[Obstacle],
    year: int = 2026,
    height_above_ground: float = 0.0,
    ground_floor: float = 0.0,
    horizon: list[float] | None = None,
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
    suns: list[tuple[float, float]] = []
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
            suns.append((sun.azimuth, sun.altitude))

    return ShadowField(
        moments=moments,
        halves=halves,
        days=len(days),
        year=year,
        sun=suns,
        horizon=list(horizon or []),
    )


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




