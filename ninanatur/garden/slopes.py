"""What the ground underfoot does to the sun, direction by direction.

The horizon ring answers the far field: hills beyond the plot. It cannot answer
the near field, because five kilometres of terrain measured at 20 m says nothing
about the bank at the end of the garden.

The near field is the slope. A cell sitting on ground that rises towards the
south loses the low sun to its own hillside long before any hill does — and the
angle is not one number but a shape: looking uphill the land stands at the full
slope, looking along the contour it stands at nothing, looking downhill it falls
away.

Combining the two into one ring per cell is what keeps this cheap. A per-cell
horizon computed properly would be 600 cells × 360 azimuths × 1,200 moments,
which is not a computation this app is going to do. A ring is 360 cosines per
cell, built once, and then every one of the 1,200 moments is an array index.
"""
from __future__ import annotations

import math
from functools import lru_cache

from ninanatur.geo.terrain import TerrainWindow

#: Below this the slope is inside the terrain model's own noise. A DGM1 states
#: ± 0.3 m, and across the few metres a slope is measured over that is more than
#: a degree — so a gentler reading than this is not a gentle slope, it is the
#: error bar.
MIN_SLOPE_DEG = 2.0


def slope_at(ground: TerrainWindow, x: float, y: float) -> tuple[float, float]:
    """The slope and the direction it climbs, in degrees.

    Aspect is measured the way every azimuth in this project is: clockwise from
    true north, pointing **uphill**. Returns (0, 0) where the ground is flat, is
    unsurveyed, or is gentler than the model can honestly distinguish.
    """
    step = ground.cell_m
    here = ground.at(x, y)
    east = ground.at(x + step, y)
    west = ground.at(x - step, y)
    north = ground.at(x, y + step)
    south = ground.at(x, y - step)
    if here is None or None in (east, west, north, south):
        return (0.0, 0.0)

    # Central differences: less sensitive to a single noisy cell than a forward
    # difference, and the terrain here is interpolated in places.
    rise_east = (east - west) / (2 * step)  # type: ignore[operator]
    rise_north = (north - south) / (2 * step)  # type: ignore[operator]
    gradient = math.hypot(rise_east, rise_north)
    slope = math.degrees(math.atan(gradient))
    if slope < MIN_SLOPE_DEG:
        return (0.0, 0.0)
    return (slope, math.degrees(math.atan2(rise_east, rise_north)) % 360.0)


#: How finely slope and aspect are rounded before a local ring is looked up.
#:
#: Not an approximation so much as an admission: a DGM1 states ± 0.3 m, so half
#: a degree of slope is well inside its noise. Rounding is what lets a garden on
#: a uniform hillside build **one** ring instead of six hundred identical ones.
SLOPE_STEP_DEG = 0.5
ASPECT_STEP_DEG = 1.0


@lru_cache(maxsize=4096)
def _local_ring(slope: float, aspect: float, azimuths: int) -> tuple[float, ...]:
    """The ground's own angle in each direction, for a plane.

    For a plane of slope `s` climbing towards `aspect`, the angle in direction θ
    is `atan(tan(s) · cos(θ − aspect))` — the full slope looking straight uphill,
    nothing along the contour, and negative downhill, which is clamped away
    because ground below a point does not shade it.
    """
    tan_slope = math.tan(math.radians(slope))
    ring: list[float] = []
    for azimuth in range(azimuths):
        uphill = math.cos(math.radians(azimuth - aspect))
        ring.append(math.degrees(math.atan(tan_slope * uphill)) if uphill > 0 else 0.0)
    return tuple(ring)


def ring_for(
    horizon: list[float] | None, slope: float, aspect: float, azimuths: int = 360
) -> tuple[float, ...]:
    """How high the land stands in each direction, as seen from one cell.

    The far horizon and the ground underfoot, whichever blocks the sun first.
    A tuple because callers key a cache on it: on a uniform hillside every cell
    in the garden produces the same ring, and the work behind it should happen
    once.
    """
    if slope <= 0.0:
        return tuple(horizon or ())
    local = _local_ring(
        round(slope / SLOPE_STEP_DEG) * SLOPE_STEP_DEG,
        round(aspect / ASPECT_STEP_DEG) * ASPECT_STEP_DEG,
        azimuths,
    )
    if not horizon:
        return local
    return tuple(
        max(local[a], horizon[a] if a < len(horizon) else 0.0) for a in range(azimuths)
    )


__all__ = ["MIN_SLOPE_DEG", "ring_for", "slope_at"]
