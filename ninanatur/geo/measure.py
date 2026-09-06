"""How tall is that building, according to the laser rather than to a tag.

The naive version is to average the surface model inside a footprint. It does not
work, and the way it fails was measured while Wave 19 was planned:

- a 30 m² outbuilding read **17.0 m**, because a tree hangs over it
- a 60 m² kindergarten read 6.5 m as a median against 12.8 m at the 95th
  percentile, for the same reason

Both are the same defect. An OSM footprint is the building's ground plan; the
surface model records whatever is *above* that ground plan, which on a small
building is often somebody's beech. So the footprint is eroded before it is
sampled, and the statistic is chosen rather than defaulted.
"""
from __future__ import annotations

import math

from ninanatur.geo.surface import SurfaceWindow

#: How far in from the outline to step before sampling.
#:
#: Two metres. A crown overhangs a roof edge by more than that often enough, and
#: eroding further would eat a garage whole — which is why a footprint that
#: survives erosion is required to keep a minimum number of cells rather than a
#: minimum area.
ERODE_M = 2.0

#: Fewest cells an eroded footprint must keep to be worth measuring.
#:
#: Twelve. Below that the median is a handful of numbers and the answer swings
#: on which of them a tree touched — and a garage measured from four cells is
#: exactly the case that produced 17 m.
MIN_CELLS = 12

#: Where in the distribution the roof is.
#:
#: The 75th percentile, not the median and not the maximum. A pitched roof spans
#: eaves to ridge across its own footprint, so the median sits halfway up it and
#: understates what casts the shadow; the maximum is an aerial, a chimney or the
#: one cell a branch reached.
ROOF_PERCENTILE = 75

#: Below this a footprint is not a building anybody needs modelled — a bin
#: store, a porch, the covered bit by the door.
MIN_HEIGHT_M = 2.0


def height_of(
    window: SurfaceWindow, footprint: list[tuple[float, float]]
) -> float | None:
    """The building's height above its own ground, or None if it cannot be said.

    None is common and is not a failure: a footprint outside the window, one too
    small to survive erosion, one over unsurveyed ground, or one whose sampled
    height is too low to be a building.
    """
    samples = _core_samples(window, footprint)
    if len(samples) < MIN_CELLS:
        return None
    samples.sort()
    height = samples[min(len(samples) - 1, len(samples) * ROOF_PERCENTILE // 100)]
    return None if height < MIN_HEIGHT_M else round(height, 1)


def looks_contaminated(
    window: SurfaceWindow, footprint: list[tuple[float, float]]
) -> bool:
    """Whether something is standing over this footprint that is not the roof.

    A roof is flat or evenly pitched, so its samples cluster. A tree over one
    corner does not: the gap between the top of the distribution and its middle
    opens up. Reported rather than corrected — the honest response to "something
    is over this building" is to keep the assumed height and say why, not to
    guess which half of the numbers is the roof.
    """
    samples = _core_samples(window, footprint)
    if len(samples) < MIN_CELLS:
        return False
    samples.sort()
    middle = samples[len(samples) // 2]
    top = samples[int(len(samples) * 0.95)]
    return top - middle > max(3.0, middle * 0.5)


def _core_samples(
    window: SurfaceWindow, footprint: list[tuple[float, float]]
) -> list[float]:
    """Surveyed heights strictly inside the eroded footprint."""
    if len(footprint) < 3:
        return []
    inset = _erode(footprint, ERODE_M)
    if inset is None:
        return []

    xs = [p[0] for p in inset]
    ys = [p[1] for p in inset]
    step = window.cell_m
    out: list[float] = []
    y = min(ys)
    while y <= max(ys):
        x = min(xs)
        while x <= max(xs):
            if _inside(inset, x, y):
                value = window.at(x, y)
                if value is not None:
                    out.append(value)
            x += step
        y += step
    return out


def _erode(footprint: list[tuple[float, float]], by_m: float) -> list[tuple[float, float]] | None:
    """Shrink a footprint towards its own centre by roughly `by_m`.

    Towards the centroid rather than along edge normals: a proper polygon offset
    is a great deal of code for a shape that is nearly always a rectangle, and
    the failure mode of the cheap version — over-eroding a long thin building —
    is caught by the cell count rather than producing a wrong answer.

    None when there is nothing left, which is the answer for a shed.
    """
    n = len(footprint)
    cx = sum(p[0] for p in footprint) / n
    cy = sum(p[1] for p in footprint) / n
    out: list[tuple[float, float]] = []
    for x, y in footprint:
        dx, dy = x - cx, y - cy
        span = math.hypot(dx, dy)
        if span <= by_m:
            return None
        keep = (span - by_m) / span
        out.append((cx + dx * keep, cy + dy * keep))
    return out


def _inside(polygon: list[tuple[float, float]], x: float, y: float) -> bool:
    """Ray casting, the same rule `footprint.covers` uses."""
    inside = False
    n = len(polygon)
    for i in range(n):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % n]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


__all__ = [
    "ERODE_M",
    "MIN_CELLS",
    "MIN_HEIGHT_M",
    "ROOF_PERCENTILE",
    "height_of",
    "looks_contaminated",
]
