"""The shape of a roof, as a surface the sun can be asked about.

`roofs.py` answers what a roof does to the shadow a building casts *on other
things* — one averaged height, because that is all a shadow polygon needs. This
module answers the other question: what the sun does to the roof itself.

They are different questions and they need different geometry. A gable roof
shades its neighbours as if it were a block about halfway up its own rise; its
own two pitches face opposite ways, and at 51°N a north pitch and a south pitch
are not remotely the same place. One number cannot say that.

**What is assumed, stated once.** The stored data is a footprint, a ridge
height, an eaves height and a roof *type* — never a ridge direction. So the
ridge is taken to run along the long axis of the footprint's smallest enclosing
rectangle, which is what German houses overwhelmingly do and what anyone drawing
a plan would expect. Where that assumption cannot be made honestly it is not
made: a pent roof has one pitch and nothing in the data says which way it falls,
so it is left unpitched rather than guessed at, and so are the shapes nobody has
identified.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ninanatur.garden.roofs import DEFAULT_EAVES_FRACTION, Roof

#: Below this a pitch is not worth distinguishing from a flat roof: it changes
#: the sun by minutes, and the ridge direction it would be applied in is an
#: assumption rather than a measurement.
MIN_PITCH_DEG = 5.0


@dataclass(frozen=True)
class RoofSurface:
    """One roof, as a height and a slope over every point of its footprint.

    Two pitches falling from a ridge *segment*. The segment is what makes one
    shape serve both roofs that need it: a gable's ridge runs the full length of
    the building, so only the two long faces slope; a hip's is shortened by the
    span at each end, so the ends slope too, at the same pitch. Distance to a
    segment handles both without a second formula.
    """

    #: Where the ridge runs, as its two endpoints in garden metres.
    ridge: tuple[tuple[float, float], tuple[float, float]]
    #: Horizontal distance from ridge to eaves. Zero for an unpitched roof.
    span_m: float
    eaves_m: float
    ridge_m: float

    @property
    def pitched(self) -> bool:
        return self.span_m > 0 and self.ridge_m > self.eaves_m

    @property
    def pitch_deg(self) -> float:
        if not self.pitched:
            return 0.0
        return math.degrees(math.atan((self.ridge_m - self.eaves_m) / self.span_m))

    def height_at(self, x: float, y: float) -> float:
        """The roof's height above the same datum the building's height is in."""
        if not self.pitched:
            return self.ridge_m
        share = min(1.0, _distance_to_segment((x, y), *self.ridge) / self.span_m)
        return self.ridge_m - share * (self.ridge_m - self.eaves_m)

    def slope_aspect_at(self, x: float, y: float) -> tuple[float, float]:
        """The pitch and the direction it climbs, degrees clockwise from north.

        Uphill, the way every aspect in this project is measured — which for a
        roof means *towards the ridge*. A point on the north pitch climbs
        southward, so it is the southern sky its own roof stands in front of,
        and that is precisely why a north pitch is darker.
        """
        if not self.pitched:
            return (0.0, 0.0)
        nearest = _nearest_on_segment((x, y), *self.ridge)
        dx, dy = nearest[0] - x, nearest[1] - y
        if math.hypot(dx, dy) < 1e-9:
            # Standing on the ridge itself: the roof falls away on both sides
            # and blocks nothing. Flat is the honest answer at a single line.
            return (0.0, 0.0)
        return (self.pitch_deg, math.degrees(math.atan2(dx, dy)) % 360.0)


def surface_of(
    footprint: list[tuple[float, float]],
    roof: Roof,
    height_m: float | None,
    eaves_m: float | None = None,
) -> RoofSurface | None:
    """The roof over this footprint, or None when its height is unknown.

    None rather than a guess: a building nobody has said the height of has been
    skipped by the shading model since Wave 8, and inventing a roof for it here
    would put a confident number on the map for the one building the model knows
    least about.
    """
    if height_m is None or len(footprint) < 3:
        return None
    box = _oriented_box(footprint)
    if box is None:
        return None
    centre, along, long_half, short_half = box

    if roof not in (Roof.GABLE, Roof.HIP):
        # Flat, pent, mixed, other, unknown. Only the first is genuinely a
        # plane at one height; the rest are shapes whose fall this model cannot
        # place, and an unpitched surface at the ridge is the same conservative
        # answer `RISE_KEPT` already gives them for their shadow.
        return RoofSurface(ridge=(centre, centre), span_m=0.0,
                           eaves_m=height_m, ridge_m=height_m)

    eaves = DEFAULT_EAVES_FRACTION * height_m if eaves_m is None else eaves_m
    eaves = max(0.0, min(eaves, height_m))
    # A hip's ridge stops one span short of each end, which is what makes its
    # ends slope. A gable's runs to the wall.
    half = long_half if roof is Roof.GABLE else max(0.0, long_half - short_half)
    ridge = (
        (centre[0] - along[0] * half, centre[1] - along[1] * half),
        (centre[0] + along[0] * half, centre[1] + along[1] * half),
    )
    surface = RoofSurface(ridge=ridge, span_m=short_half, eaves_m=eaves,
                          ridge_m=height_m)
    if surface.pitch_deg < MIN_PITCH_DEG:
        return RoofSurface(ridge=(centre, centre), span_m=0.0,
                           eaves_m=height_m, ridge_m=height_m)
    return surface


def _oriented_box(
    footprint: list[tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float], float, float] | None:
    """Centre, long-axis unit vector, and the two half-extents.

    The smallest enclosing rectangle, found by trying each edge direction — a
    minimum-area rectangle always has a side flush with an edge of the hull, and
    a footprint here has a handful of points, so trying all of them is cheaper
    than being clever about it.
    """
    best: tuple[float, tuple[float, float], float, float, float, float] | None = None
    for index, (x0, y0) in enumerate(footprint):
        x1, y1 = footprint[(index + 1) % len(footprint)]
        length = math.hypot(x1 - x0, y1 - y0)
        if length < 1e-9:
            continue
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        along = [p[0] * ux + p[1] * uy for p in footprint]
        across = [-p[0] * uy + p[1] * ux for p in footprint]
        width, depth = max(along) - min(along), max(across) - min(across)
        area = width * depth
        if best is None or area < best[0]:
            best = (area, (ux, uy), (min(along) + max(along)) / 2,
                    (min(across) + max(across)) / 2, width / 2, depth / 2)
    if best is None:
        return None
    _area, (ux, uy), mid_along, mid_across, half_w, half_d = best
    centre = (mid_along * ux - mid_across * uy, mid_along * uy + mid_across * ux)
    # The ridge runs along the longer side, so swap the axis when the edge that
    # won happens to be the short one.
    if half_w >= half_d:
        return (centre, (ux, uy), half_w, half_d)
    return (centre, (-uy, ux), half_d, half_w)


def _nearest_on_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> tuple[float, float]:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-12:
        return start
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    return (start[0] + t * dx, start[1] + t * dy)


def _distance_to_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    near = _nearest_on_segment(point, start, end)
    return math.hypot(point[0] - near[0], point[1] - near[1])


__all__ = ["MIN_PITCH_DEG", "RoofSurface", "surface_of"]
