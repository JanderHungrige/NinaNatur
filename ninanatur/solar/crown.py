"""A crown as an ellipsoid on a trunk — Wave 26, feature 6 (doc 121).

A crown was a cylinder from the ground to its top, passing a fixed share of
the sun whenever a ray touched it. It is an ellipsoid on a trunk instead, and
it passes light by the depth of the crossing (Beer–Lambert, doc 121):

    T = exp(−k·L),   k = −ln(T₀) / (2·max(r_h, r_v))

so its longest chord passes exactly the share the model used before, and
every other chord more. The chord is solved as a quadratic along the same ray
the raster cuts its parts with: by horizontal distance t towards the sun,
rising 1/cot a metre (`raster.covered`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Crown:
    """A crown in its tree's own datum, the ground it stands on being zero."""

    #: Where the trunk stands, in garden metres.
    x: float
    y: float
    #: The crown's horizontal radius.
    radius: float
    #: Where the canopy starts and where it ends, above the tree's ground.
    base: float
    top: float


@dataclass(frozen=True)
class CrownSolid:
    """A crown standing where its tree stands: the ellipsoid in absolute heights."""

    cx: float
    cy: float
    #: The horizontal and vertical semi-axes.
    rh: float
    rv: float
    #: The height of its centre.
    cz: float

    @property
    def longest(self) -> float:
        """Its longest chord, which passes exactly the old share."""
        return 2.0 * max(self.rh, self.rv)


def standing(crown: Crown, ground: float) -> CrownSolid:
    """The crown as the raster reads it, on ground at this height. A crown
    with no depth is given two centimetres of it, so it still exists."""
    rv = max(crown.top - crown.base, 0.02) / 2.0
    return CrownSolid(cx=crown.x, cy=crown.y, rh=max(crown.radius, 0.01), rv=rv,
                      cz=ground + crown.top - rv)


def chord(solid: CrownSolid, x: np.ndarray | float, y: np.ndarray | float,
          z: np.ndarray | float, sun_x: np.ndarray | float, sun_y: np.ndarray | float,
          cot: np.ndarray | float) -> np.ndarray:
    """How far the ray from each point towards the sun runs inside the crown,
    in metres — zero where it misses it. The points may be a grid (one sun)
    or one point (many suns): the arithmetic broadcasts either way.

    Written for the grid, which asks it once a crown and a moment: the
    quadratic in its half-coefficient form, and no test for a ray that
    misses — its two roots are then one, and the run between them nothing.
    """
    rise = 1.0 / cot
    inv_h, inv_v = 1.0 / (solid.rh * solid.rh), 1.0 / (solid.rv * solid.rv)
    dx, dy, dz = x - solid.cx, y - solid.cy, z - solid.cz
    a = (sun_x * sun_x + sun_y * sun_y) * inv_h + rise * rise * inv_v
    half_b = (dx * sun_x + dy * sun_y) * inv_h + dz * (rise * inv_v)
    c = (dx * dx + dy * dy) * inv_h + dz * dz * inv_v - 1.0
    root = np.sqrt(np.maximum(half_b * half_b - a * c, 0.0))
    far = (root - half_b) / a
    near = np.maximum(-(half_b + root) / a, 0.0)
    # Horizontal distance along the ground; the crossing itself is longer.
    length: np.ndarray = np.maximum(far - near, 0.0) * np.sqrt(1.0 + rise * rise)
    return length


def passing(share: np.ndarray | float, solid: CrownSolid, length: np.ndarray) -> np.ndarray:
    """What passes a crossing this long, for a crown whose longest chord
    passes `share`: exp(−k·L). A crown that passes nothing blocks any crossing."""
    if np.ndim(share) == 0:
        # The grid's case: one month, one share.
        if float(share) <= 0.0:
            blocked: np.ndarray = np.where(length > 0.0, 0.0, 1.0)
            return blocked
        passed: np.ndarray = np.exp(length * (math.log(float(share)) / solid.longest))
        return passed
    shares = np.asarray(share, dtype=float)
    with np.errstate(divide="ignore"):
        k = np.where(shares > 0.0, -np.log(np.maximum(shares, 1e-300)) / solid.longest, np.inf)
    through: np.ndarray = np.where(length > 0.0, np.exp(-k * length), 1.0)
    return through


def outline(solid: CrownSolid, ground: float, per_metre: tuple[float, float],
            points: int = 96) -> list[tuple[float, float]]:
    """The ground a crown shades at this moment: its shadow on ground at this
    height, an ellipse — the ellipsoid is a sphere stretched, and so is its
    shadow. Anticlockwise, as the drawing's other outlines are.

    `per_metre` is how far a metre of height throws. The ellipse's points are
    pushed out by the angle between them, so the drawn ring holds the shadow
    rather than cutting its rim (the counted shadow is the exact ellipse).
    """
    ox, oy = per_metre
    # The projection of a point (X, Y, Z) is (X + ox·(Z − ground), Y + oy·(Z − ground));
    # of the stretched sphere, the image of the unit disc under Q·M.
    q = np.array([[solid.rh, 0.0, ox * solid.rv], [0.0, solid.rh, oy * solid.rv]])
    shape = q @ q.T
    root = np.linalg.cholesky(shape)
    centre = (solid.cx + ox * (solid.cz - ground), solid.cy + oy * (solid.cz - ground))
    grow = 1.0 / math.cos(math.pi / points)
    ring = []
    for step in range(points):
        angle = 2.0 * math.pi * step / points
        px, py = root @ np.array([math.cos(angle), math.sin(angle)]) * grow
        ring.append((centre[0] + float(px), centre[1] + float(py)))
    return ring


__all__ = ["Crown", "CrownSolid", "chord", "outline", "passing", "standing"]
