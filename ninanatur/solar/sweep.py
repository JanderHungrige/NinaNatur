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
from functools import lru_cache

import numpy as np
import shapely
from shapely.affinity import translate
from shapely.errors import GEOSException
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from ninanatur.solar.convex_parts import solid_of
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


__all__ = ["convex_hull", "shadow_shape"]
