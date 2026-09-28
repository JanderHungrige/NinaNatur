"""The ground a footprint shades, drawn exactly — Wave 26, feature 1 (doc 116).

A footprint swept along its shadow is the union of three kinds of piece: the
footprint, its copy moved by the shadow's offset, and the band each wall sweeps
between the two. Only the walls that face along the shadow are needed: a point
of the footprint travelling with the shadow leaves it through one of those, and
that wall's band carries it the rest of the way. For a convex outline the union
is the hull of the footprint and its copy, which is what every shadow in this
project was until 2026-09-22. For a concave one the hull fills the open corner
of an L-shaped house, so the union is taken instead.

The light model has counted concave shadows exactly since the review of
2026-09-22 (`reach.near_edge`, doc 38). This is the same shadow as a drawing, so
the plan can show what the sun map counts.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import shapely
from shapely.affinity import translate
from shapely.errors import GEOSException
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from ninanatur.solar.convex_parts import convex_parts, solid_of
from ninanatur.solar.reach import is_convex

log = logging.getLogger(__name__)

Ring = list[tuple[float, float]]

#: Grids the union is snap-rounded to when GEOS throws on it. It can, on valid
#: input ("side location conflict"): a tangled shed failed the whole day's
#: shadows with it (review, 2026-09-22). A micrometre moves nothing anybody
#: draws. Tried only after the plain union fails, which is rare, because
#: snap-rounding makes every union about 70 % dearer.
GRIDS_M = (1e-6, 1e-3)
#: A ring smaller than a square centimetre is a sliver, not a shadow or a hole.
SLIVER_M2 = 1e-4


@dataclass(frozen=True)
class RoofSolid:
    """A roof as the shadow model needs it (doc 120), in its building's own
    datum, the base being zero: the planes it falls on, where their ridge
    runs, and the eaves below which the walls carry the shadow.

    `garden.roofshape.RoofSurface` builds it; the light model and the drawn
    shadow read this one shape. The roof's own cells stand on the surface it
    was built from (`lightcells.surface_at`), whose height is the same lower
    envelope — `test_roof_cells` holds the two to each other.
    """

    planes: tuple[tuple[float, float, float, float], ...]
    ridge: tuple[tuple[float, float], tuple[float, float]]
    eaves: float

    def height_at(self, x: float, y: float) -> float:
        """The roof over this point, never below the eaves — the lower
        envelope of its planes, as `RoofSurface.height_at` reads it."""
        under = min(d - nx * x - ny * y for nx, ny, _nz, d in self.planes)
        return max(self.eaves, under)


def convex_hull(points: Ring) -> Ring:
    """Andrew's monotone chain, anticlockwise. Small inputs — a rectangle's
    shadow is eight points before the hull and four to six after."""
    unique = sorted(set(points))
    if len(unique) < 3:
        return unique

    def half(source: Ring) -> Ring:
        chain: Ring = []
        for p in source:
            while len(chain) >= 2 and _turn(chain[-2], chain[-1], p) <= 0:
                chain.pop()
            chain.append(p)
        return chain[:-1]

    return half(unique) + half(unique[::-1])


def shadow_shape(footprint: Ring, dx: float, dy: float) -> list[Ring]:
    """The footprint swept by (dx, dy), as rings: outlines anticlockwise, holes
    clockwise, so a path of the rings of many shapes fills their union once
    under the non-zero rule.

    One ring for a convex, simple outline — its hull, the same points as ever,
    so a rectangle draws as it always did. Anything else goes through shapely,
    and a shadow can then have a hole: a courtyard whose opening faces along
    the shadow is closed by its own swept wall, and the sun still reaches its
    far side. An outline that crosses itself is repaired into the shapes it
    encloses and each is swept, never dropped.
    """
    ring = tuple(_distinct(footprint))
    parts = _parts(ring)
    if parts is None:
        return [convex_hull(list(ring) + [(x + dx, y + dy) for x, y in ring])] if ring else []
    pieces: list[BaseGeometry] = []
    for part in parts:
        pieces += [part, translate(part, dx, dy)]
        pieces += _bands(part, dx, dy)
    return _rings(_union(pieces))


def roof_shadow(footprint: Ring, roof: RoofSolid,
                per_metre: tuple[float, float]) -> list[Ring]:
    """The ground a roofed building shades, drawn as the model counts it
    (doc 120): the solid under the roof's planes, cast by the sun.

    Over each of the footprint's **convex parts** — the very pieces the light
    model casts from (`convex_parts`) — the solid is convex, so its shadow is
    the hull of its corners' own shadows, and each corner casts by its own
    height: the eaves where the roof has come down, the ridge where it has
    not. The ridge is cut to the part it crosses; a wing that has none is
    shaded by its eaves alone. Taken over the whole outline instead, an L's
    hull filled the open corner the sun still reaches — the defect feature 1
    removed for blocks (review, 2026-09-22).

    `per_metre` is how far a metre of height throws at this moment. Outlines
    anticlockwise, holes clockwise, as `shadow_shape` returns them, so both
    draw into one path.
    """
    ox, oy = per_metre
    rings: list[Ring] = []
    for ring in convex_parts(list(footprint)):
        ground = [(float(x), float(y)) for x, y in ring]
        if len(ground) < 3:
            continue
        over = [_cast(x, y, roof, ox, oy) for x, y in ground]
        crest = [_cast(x, y, roof, ox, oy) for x, y in _crests(ring, roof)]
        rings.append(convex_hull(ground + over + crest))
    if len(rings) < 2:
        return rings
    return _rings(_union([Polygon(r) for r in rings]))


def _cast(x: float, y: float, roof: RoofSolid, ox: float, oy: float) -> tuple[float, float]:
    """Where this point of the roof throws its own shadow."""
    height = roof.height_at(x, y)
    return (x + height * ox, y + height * oy)


def _crests(ring: tuple[tuple[float, float], ...], roof: RoofSolid,
            ) -> list[tuple[float, float]]:
    """Every line where two of the roof's planes meet, cut to this part, as
    the points its shadow turns at — its ridge and its hips.

    Over a wall the roof's height is the lowest of its planes, which bends
    where the governing plane changes: a hip line crossing the wall stands
    higher than either corner beside it, and a hull of the corners alone left
    it out (review, 2026-09-22). A point that is not really on the roof there
    is harmless: it is cast at the roof's own height, so it lies inside the
    solid whose shadow this is.
    """
    points: list[tuple[float, float]] = []
    planes = roof.planes
    for first in range(len(planes)):
        for second in range(first + 1, len(planes)):
            ax, ay, _az, ad = planes[first]
            bx, by, _bz, bd = planes[second]
            # Equal heights: (bx − ax)·x + (by − ay)·y = bd − ad.
            nx, ny, offset = bx - ax, by - ay, bd - ad
            length = math.hypot(nx, ny)
            if length <= 1e-12:
                continue
            on = (nx * offset / length**2, ny * offset / length**2)
            points += _line_across(ring, on, (-ny / length, nx / length))
    # The ridge itself, cut to the part: a hip's ridge ends — where three of
    # its planes meet — lie inside the walls, and they are the highest points
    # the part has. Cast only where lines cross the walls, every hip was drawn
    # at its eaves, a sixth of its shadow short (review, 2026-09-28). A ridge
    # that is a point, a pyramid's apex, is its own segment.
    (rx, ry), (sx, sy) = roof.ridge
    run = math.hypot(sx - rx, sy - ry)
    way = ((sx - rx) / run, (sy - ry) / run) if run > 1e-12 else (1.0, 0.0)
    points += _line_across(ring, (rx, ry), way, 0.0, run)
    return points


def _line_across(ring: tuple[tuple[float, float], ...], through: tuple[float, float],
                 direction: tuple[float, float], start: float = -math.inf,
                 end: float = math.inf) -> list[tuple[float, float]]:
    """Where a line — or its stretch from `start` to `end` along `direction`
    — lies in this convex part, as its two ends there; empty if it misses.

    Cut to the part rather than asked whether its ends are inside it: a
    ridge's ends are the roof's *rectangle's*, so they sit on the wall or a
    millionth of a metre outside, and an oblique surveyed fall (doc 94) then
    dropped the ridge and six metres of a house's shadow with it.
    """
    (ax, ay), (dx, dy) = through, direction
    low, high = start, end
    for (px, py), (qx, qy) in zip(ring, ring[1:] + ring[:1], strict=True):
        # Each wall of an anticlockwise part, inside being to its left.
        nx, ny = (qy - py), -(qx - px)
        along = nx * dx + ny * dy
        room = nx * (px - ax) + ny * (py - ay)
        if abs(along) <= 1e-12:
            if room < 0:
                return []
            continue
        cut = room / along
        if along > 0:
            high = min(high, cut)
        else:
            low = max(low, cut)
    if low > high or not math.isfinite(low) or not math.isfinite(high):
        return []
    return [(ax + dx * low, ay + dy * low), (ax + dx * high, ay + dy * high)]


@lru_cache(maxsize=4096)
def _parts(ring: tuple[tuple[float, float], ...]) -> tuple[Polygon, ...] | None:
    """The shapes the outline encloses, each outline anticlockwise and each
    hole clockwise — or None for a convex, simple outline, whose hull is its
    shadow. The same for every frame of a day, so worked out once."""
    if len(ring) >= 3 and Polygon(ring).is_valid and is_convex(list(ring)):
        return None
    return tuple(shapely.orient_polygons(p) for p in solid_of(list(ring)))


def _bands(part: Polygon, dx: float, dy: float) -> list[BaseGeometry]:
    """The band each wall facing along the shadow sweeps. With the solid on
    the left of every edge (outlines anticlockwise, holes clockwise), a wall's
    outward normal is its edge turned right."""
    shift = np.array([dx, dy])
    quads: list[np.ndarray] = []
    for boundary in (part.exterior, *part.interiors):
        coords = np.asarray(boundary.coords)
        a, b = coords[:-1], coords[1:]
        facing = (b[:, 1] - a[:, 1]) * dx - (b[:, 0] - a[:, 0]) * dy > 0
        quads.append(np.stack([a, b, b + shift, a + shift], axis=1)[facing])
    stacked = np.concatenate(quads)
    if not len(stacked):
        return []
    made: np.ndarray = np.asarray(shapely.polygons(stacked), dtype=object)
    return list(made.ravel())


def _union(pieces: list[BaseGeometry]) -> BaseGeometry:
    """The pieces' union; snap-rounded, and logged, only where GEOS throws."""
    try:
        return shapely.union_all(pieces)
    except GEOSException:
        log.warning("shadow union of %d pieces failed; snap-rounding it", len(pieces),
                    exc_info=True)
    for grid in GRIDS_M[:-1]:
        try:
            return shapely.union_all(pieces, grid_size=grid)
        except GEOSException:
            log.warning("shadow union failed at a %g m grid", grid, exc_info=True)
    return shapely.union_all(pieces, grid_size=GRIDS_M[-1])


def _rings(shape: BaseGeometry) -> list[Ring]:
    """The union's rings, without slivers: where two pieces meet in floating
    point, the union can leave a ring of three points and no area."""
    rings: list[Ring] = []
    for polygon in _polygons(shape):
        oriented = shapely.orient_polygons(polygon)
        for boundary in (oriented.exterior, *oriented.interiors):
            coords = [(float(x), float(y)) for x, y in boundary.coords][:-1]
            if len(coords) >= 3 and abs(_area(coords)) >= SLIVER_M2:
                rings.append(coords)
    return rings


def _area(ring: Ring) -> float:
    return sum(ax * by - bx * ay
               for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True)) / 2


def _polygons(shape: BaseGeometry) -> list[Polygon]:
    if isinstance(shape, Polygon):
        return [] if shape.is_empty else [shape]
    parts = getattr(shape, "geoms", ())
    return [p for part in parts for p in _polygons(part)]


def _distinct(ring: Ring) -> Ring:
    """Without a point repeated back to back — OpenStreetMap closes every way
    on its first node, and a zero-length wall sweeps nothing."""
    kept = [p for i, p in enumerate(ring) if i == 0 or p != ring[i - 1]]
    if len(kept) > 1 and kept[0] == kept[-1]:
        kept.pop()
    return kept


def _turn(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


__all__ = ["RoofSolid", "convex_hull", "roof_shadow", "shadow_shape"]
