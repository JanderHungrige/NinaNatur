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

from dataclasses import dataclass, field

import numpy as np

from ninanatur.solar.convex_parts import SAME_M, convex_parts
from ninanatur.solar.crown import Crown, CrownSolid, chord, passing, standing
from ninanatur.solar.incidence import LEVEL, Incidence, Plane, cos_incidence
from ninanatur.solar.moments import Directions, Moments, moments_for, moments_from, sun_directions
from ninanatur.solar.shading import Obstacle, passes

#: A wall this nearly parallel to the sun's direction is parallel to it.
PARALLEL = 1e-12


@dataclass(frozen=True)
class Part:
    """One convex part of something that casts: its corners anticlockwise, its
    walls' outward normals, each wall's offset along its normal, and the roof
    planes over it, if it has any (doc 120).

    A convex solid, cut against the ray by the same interval either way: a
    wall bounds it sideways, the flat top at `top` bounds it above, and a
    roof's plane leans between the two. `roof` holds those as rows of
    (n_x, n_y, n_z, d) in absolute heights, inside being n·X ≤ d.
    """

    corners: np.ndarray
    normals: np.ndarray
    offsets: np.ndarray
    top: float
    transmission: float
    bare_transmission: float | None
    owner: int | None
    roof: np.ndarray = field(default_factory=lambda: np.empty((0, 4)))
    #: The crown it is (doc 121): then the walls are its bounding box's, and
    #: what passes is decided by the depth of the crossing, not by the walls.
    crown: CrownSolid | None = None

    def through(self, month: int) -> float:
        return passes(self.transmission, self.bare_transmission, month)


def parts_of(obstacles: list[Obstacle]) -> list[Part]:
    """Every obstacle as its convex parts, each standing to its absolute top."""
    parts: list[Part] = []
    for obstacle in obstacles:
        if obstacle.crown is not None:
            parts.append(_crown_part(obstacle, obstacle.crown))
            continue
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
            # The roof's planes are given in the obstacle's own datum, its
            # base being zero, and stand where the obstacle stands (doc 120).
            roof = np.array([[nx, ny, nz, d + nz * obstacle.base]
                             for nx, ny, nz, d in
                             (obstacle.roof.planes if obstacle.roof else ())],
                            dtype=float).reshape(-1, 4)
            parts.append(Part(
                corners=corners, normals=normals,
                offsets=np.einsum("ij,ij->i", normals, corners), top=obstacle.top,
                transmission=obstacle.transmission,
                bare_transmission=obstacle.bare_transmission, owner=obstacle.owner,
                roof=roof,
            ))
    return parts


def _crown_part(obstacle: Obstacle, crown: Crown) -> Part:
    """A crown as a part: the square round it, which is what the sweep's
    boxes and reach read, and the ellipsoid, which is what it casts."""
    solid = standing(crown, obstacle.base)
    x0, x1 = solid.cx - solid.rh, solid.cx + solid.rh
    y0, y1 = solid.cy - solid.rh, solid.cy + solid.rh
    corners = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    normals = np.array([[0.0, -1.0], [1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])
    return Part(corners=corners, normals=normals,
                offsets=np.einsum("ij,ij->i", normals, corners), top=solid.cz + solid.rv,
                transmission=obstacle.transmission, bare_transmission=obstacle.bare_transmission,
                owner=obstacle.owner, crown=solid)


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
    for nx, ny, nz, d in part.roof.tolist():
        # The same interval, cut by a plane that leans: along the ray the
        # height rises by 1/cot for every metre travelled (doc 120). One plane
        # at a time, as floats: cut all at once or read as numpy's scalars, a
        # plane cost more than the arithmetic (review, 2026-09-28).
        along = nx * sun_x + ny * sun_y + nz / cot
        room = d - (nx * x + ny * y + nz * z)
        if abs(along) <= PARALLEL:
            t_hi = np.where(room >= 0, t_hi, -1.0)
            continue
        if along > 0:
            np.minimum(t_hi, room / along, out=t_hi)
        else:
            np.maximum(t_lo, room / along, out=t_lo)
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
        for nx, ny, nz, d in part.roof.tolist():
            room = d - (nx * x + ny * y + nz * z)
            along = nx * sun_x + ny * sun_y + nz / cot
            limit = room / along
            t_hi = np.where(along > PARALLEL, np.minimum(t_hi, limit), t_hi)
            t_lo = np.where(along < -PARALLEL, np.maximum(t_lo, limit), t_lo)
            if room < 0:
                t_hi = np.where(np.abs(along) <= PARALLEL, -1.0, t_hi)
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
        if part.crown is not None:
            az = np.radians(directions.azimuth)
            depth = chord(part.crown, x, y, z, np.sin(az), np.cos(az),
                          1.0 / np.tan(np.radians(directions.altitude)))
            through *= passing(passes, part.crown, depth)
            continue
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


__all__ = ["Directions", "Moments", "Part", "covered", "covered_over_moments", "moments_for",
           "moments_from", "parts_of", "point_hours", "point_sums", "point_sweep",
           "sun_directions", "visible"]
