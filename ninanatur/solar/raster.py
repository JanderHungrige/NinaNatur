"""Every cell's sun at once — Wave 26, feature 2 (doc 117).

`field.ShadowField` asked, for one point after another, whether each obstacle's
shadow covered it at each moment: pure Python per moment × obstacle × cell,
which held the grid to 3 m cells at forty houses and left no room for finer
sampling. This asks the same question of every cell under a shadow at once,
with numpy.

Each obstacle is its convex parts (`convex_parts`). A cell at height z is in a
part's shadow when the ray from it towards the sun enters the part within the
shadow's reach there, (top - z) / tan(altitude): a Cyrus–Beck interval against
the part's few walls, exact at any height and for any outline. Only the cells
under the part's swept box are asked. `field.py` stays as the slow reference
the raster is tested against (`tests/test_raster.py`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np

from ninanatur.solar.convex_parts import SAME_M, convex_parts
from ninanatur.solar.light import MINUTE_STEP, season_days
from ninanatur.solar.position import Location, sun_position
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle, passes

#: A wall this nearly parallel to the sun's direction is parallel to it.
PARALLEL = 1e-12


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


@dataclass(frozen=True)
class Incidence:
    """What each direction's beam brings, beside what it is worth (doc 119):
    for the sun, the clear-sky beam at its altitude (`solar.beam`), added —
    times what passes and the cosine of its incidence on each cell's surface —
    to the energy sum named by `group`."""

    beam: np.ndarray
    group: np.ndarray
    groups: int


#: A surface as the sweep reads it: (cos s, −sin s·cos a, −sin s·sin a), which
#: dotted with the sun's (sin h, cos h·cos A, cos h·sin A) is the cosine of
#: incidence. Level ground is (1, 0, 0).
Plane = tuple[float, float, float]
LEVEL: Plane = (1.0, 0.0, 0.0)


def plane_of(slope_deg: float, aspect_deg: float) -> Plane:
    """A surface of this slope, its aspect uphill clockwise from north as every
    aspect here is (`slopes.slope_at`): it faces the other way, downhill."""
    s, a = np.radians(slope_deg), np.radians(aspect_deg)
    return (float(np.cos(s)), float(-np.sin(s) * np.cos(a)), float(-np.sin(s) * np.sin(a)))


def cos_incidence(altitude_deg: np.ndarray, azimuth_deg: np.ndarray,
                  plane: tuple[np.ndarray | float, ...]) -> np.ndarray:
    """The cosine of each direction's incidence on a surface (`Plane`), which
    may be a cell's arrays: sin h cos s − cos h sin s cos(A − a)."""
    h, az = np.radians(altitude_deg), np.radians(azimuth_deg)
    cos_i: np.ndarray = (np.sin(h) * plane[0] + np.cos(h) * np.cos(az) * plane[1]
                         + np.cos(h) * np.sin(az) * plane[2])
    return cos_i


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


@dataclass(frozen=True)
class Part:
    """One convex part of something that casts: its corners anticlockwise, its
    walls' outward normals, and each wall's offset along its normal."""

    corners: np.ndarray
    normals: np.ndarray
    offsets: np.ndarray
    top: float
    transmission: float
    bare_transmission: float | None
    owner: int | None

    def through(self, month: int) -> float:
        return passes(self.transmission, self.bare_transmission, month)


def parts_of(obstacles: list[Obstacle]) -> list[Part]:
    """Every obstacle as its convex parts, each standing to its absolute top."""
    parts: list[Part] = []
    for obstacle in obstacles:
        for ring in convex_parts(list(obstacle.footprint)):
            corners = np.array(ring, dtype=float)
            edges = np.roll(corners, -1, axis=0) - corners
            lengths = np.hypot(edges[:, 0], edges[:, 1])
            # Unit normals, so "parallel to the sun" is an angle and not an
            # edge's length; an edge too short to have a direction has none.
            keep = lengths > SAME_M
            corners, edges, lengths = corners[keep], edges[keep], lengths[keep]
            if len(corners) < 3:
                continue
            normals = np.column_stack([edges[:, 1], -edges[:, 0]]) / lengths[:, None]
            parts.append(Part(
                corners=corners, normals=normals,
                offsets=np.einsum("ij,ij->i", normals, corners), top=obstacle.top,
                transmission=obstacle.transmission,
                bare_transmission=obstacle.bare_transmission, owner=obstacle.owner,
            ))
    return parts


def covered(part: Part, x: np.ndarray, y: np.ndarray, z: np.ndarray,
            sun_x: float, sun_y: float, cot: float) -> np.ndarray:
    """Which of these points the part's shadow covers, the sun lying towards
    (sun_x, sun_y) at a cotangent `cot`: the ray from each towards the sun
    enters the part within (top - z) * cot.

    `x` is a row of columns and `y` a column of rows, so each wall's distance
    along the ray is divided through before the two are broadcast into the
    grid: one addition of the grid's size per wall, not three.
    """
    t_hi = np.where(z < part.top, (part.top - z) * cot, -1.0)
    t_lo = np.zeros(t_hi.shape)
    for (nx, ny), offset in zip(part.normals, part.offsets, strict=True):
        toward = nx * sun_x + ny * sun_y
        if abs(toward) <= PARALLEL:
            t_hi = np.where(offset - (nx * x + ny * y) >= 0, t_hi, -1.0)
            continue
        along = (-nx / toward) * x + (offset - ny * y) / toward
        if toward > 0:
            np.minimum(t_hi, along, out=t_hi)
        else:
            np.maximum(t_lo, along, out=t_lo)
    covering: np.ndarray = t_lo <= t_hi
    return covering


def covered_over_moments(part: Part, x: float, y: float, z: float,
                         moments: Moments | Directions) -> np.ndarray:
    """At which moments the part's shadow covers one point: `covered` turned
    round, for a single point asked about every moment at once."""
    az = np.radians(moments.azimuth)
    sun_x, sun_y = np.sin(az), np.cos(az)
    cot = 1.0 / np.tan(np.radians(moments.altitude))
    t_hi = (part.top - z) * cot if z < part.top else np.full(az.shape, -1.0)
    t_lo = np.zeros(az.shape)
    with np.errstate(divide="ignore", invalid="ignore"):
        for (nx, ny), offset in zip(part.normals, part.offsets, strict=True):
            room = offset - (nx * x + ny * y)
            toward = nx * sun_x + ny * sun_y
            limit = room / toward
            t_hi = np.where(toward > PARALLEL, np.minimum(t_hi, limit), t_hi)
            t_lo = np.where(toward < -PARALLEL, np.maximum(t_lo, limit), t_lo)
            if room < 0:
                t_hi = np.where(np.abs(toward) <= PARALLEL, -1.0, t_hi)
    covering: np.ndarray = t_lo <= t_hi
    return covering


def point_hours(parts: list[Part], moments: Moments, x: float, y: float, z: float = 0.0,
                ring: list[float] | None = None, owner: int | None = None,
                ) -> tuple[float, float]:
    """Mean daily sun hours before and after due south, at one point.

    `owner` leaves one element's parts out, for a point on that element's own
    roof; `ring` is the land's height in each degree of azimuth around it.
    """
    morning, afternoon = point_sums(parts, sun_directions(moments), x, y, z, ring, owner)
    return float(morning), float(afternoon)


def point_sums(parts: list[Part], directions: Directions, x: float, y: float, z: float = 0.0,
               ring: list[float] | None = None, owner: int | None = None) -> np.ndarray:
    """(groups,): each group's weighted sum of what reaches one point."""
    return point_sweep(parts, directions, x, y, z, ring, owner)[0]


def point_sweep(parts: list[Part], directions: Directions, x: float, y: float,
                z: float = 0.0, ring: list[float] | None = None, owner: int | None = None,
                incidence: Incidence | None = None, plane: Plane = LEVEL,
                ) -> tuple[np.ndarray, np.ndarray]:
    """(groups,) as `point_sums`, and (incidence groups,): the energy of what
    reaches the point on its surface (doc 119) — empty without `incidence`."""
    through = _point_through(parts, directions, x, y, z, ring, owner)
    sums: np.ndarray = np.bincount(directions.group, weights=through * directions.weight,
                                   minlength=directions.groups)
    if incidence is None:
        return sums, np.zeros(0)
    brings = incidence.beam * np.maximum(
        cos_incidence(directions.altitude, directions.azimuth, plane), 0.0)
    energy: np.ndarray = np.bincount(incidence.group, weights=through * brings,
                                     minlength=incidence.groups)
    return sums, energy


def _point_through(parts: list[Part], directions: Directions, x: float, y: float, z: float,
                   ring: list[float] | None, owner: int | None) -> np.ndarray:
    """(directions,): what passes to the point from each direction."""
    through = np.ones(directions.azimuth.shape)
    for part in parts:
        if owner is not None and part.owner == owner:
            continue
        passes = _through_by_month(part, directions.month)
        through *= np.where(covered_over_moments(part, x, y, z, directions), passes, 1.0)
    if ring:
        through = through * visible(np.asarray([ring], dtype=float), directions)[:, 0]
    return through


def visible(rings: np.ndarray, moments: Moments | Directions) -> np.ndarray:
    """(moments, rings): whether the sun clears each ring at each moment — as
    `field.ShadowField.moments_under` reads a ring, one entry per degree."""
    index = np.round(moments.azimuth).astype(int) % rings.shape[1]
    seen: np.ndarray = moments.altitude[:, None] >= rings[:, index].T
    return seen


def _through_by_month(part: Part, months: np.ndarray) -> np.ndarray:
    """What passes through the part in each moment's month (`Part.through`,
    asked once per month the moments span)."""
    if part.bare_transmission is None:
        return np.full(months.shape, part.transmission)
    by_month = np.array([part.through(month) for month in range(13)])
    through: np.ndarray = by_month[months]
    return through


__all__ = ["LEVEL", "Directions", "Incidence", "Moments", "Part", "Plane", "cos_incidence",
           "covered", "covered_over_moments", "moments_for", "moments_from", "parts_of",
           "plane_of", "point_hours", "point_sums", "point_sweep", "sun_directions", "visible"]
