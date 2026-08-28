"""How much room a plant needs, and how much shade it casts once it has it.

A bed is a marked area, not a category — whether a tree or a flower stands in it
is a fact about the planting, not about the bed. What actually follows from
planting a tree is spatial: it needs room, and it changes the light for
everything near it, including itself.

Both numbers here are **estimates from height**, because the catalogue records
no crown width — GIFT gives `height_max_m` and nothing about spread. They are
marked as estimates everywhere they surface, for the same reason every trait
value carries provenance: a derived number that looks measured is worse than no
number.
"""
from __future__ import annotations

from dataclasses import dataclass

# Crown radius as a fraction of height. Open-grown trees are roughly as wide as
# a third of their height; shrubs are proportionally much broader, and anything
# herbaceous occupies about its own height in width.
#
# Rules of thumb, not measurements. They decide whether a plant is flagged as
# too large for a bed, never whether it is hidden.
CROWN_RATIO: dict[str, float] = {
    "tree": 1 / 3,
    "shrub": 0.5,
    "subshrub": 0.5,
}
DEFAULT_CROWN_RATIO = 0.4

# Below this a plant does not meaningfully shade its neighbours: the shadow of a
# 1 m perennial at a usable sun altitude falls inside its own footprint.
MIN_SHADING_HEIGHT_M = 1.5

WOODY_FORMS = frozenset({"tree", "shrub", "subshrub"})


@dataclass(frozen=True)
class Canopy:
    """A plant's mature extent, estimated. `estimated` is never False today —
    the field exists so a measured source can be added without changing callers,
    and so the UI cannot forget which kind of number it is holding."""

    radius_m: float
    area_m2: float
    height_m: float
    estimated: bool = True


def crown_radius(height_m: float, growth_form: str | None) -> float:
    """Estimated crown radius in metres."""
    ratio = CROWN_RATIO.get((growth_form or "").lower(), DEFAULT_CROWN_RATIO)
    return max(height_m * ratio, 0.05)


def canopy_of(height_m: float | None, growth_form: str | None) -> Canopy | None:
    """What this plant will occupy, or None when its height was never recorded.

    None rather than a default: height is recorded for 44% of the catalogue, and
    inventing a size for the rest would put a confident number where there is no
    data — the same rule the height filter follows.
    """
    if height_m is None or height_m <= 0:
        return None
    radius = crown_radius(height_m, growth_form)
    return Canopy(
        radius_m=round(radius, 2),
        area_m2=round(3.141592653589793 * radius * radius, 2),
        height_m=height_m,
    )


def shades(canopy: Canopy | None) -> bool:
    """Whether planting this changes the light for what is near it."""
    return canopy is not None and canopy.height_m >= MIN_SHADING_HEIGHT_M


def polygon_area(polygon: list[list[float]]) -> float:
    """Area of a bed's polygon in square metres, by the shoelace formula.

    Absolute value, so a polygon wound either way gives the same area — the
    drawing tool in Wave 7 will not guarantee a winding direction.
    """
    if len(polygon) < 3:
        return 0.0
    total = 0.0
    for i, point in enumerate(polygon):
        nxt = polygon[(i + 1) % len(polygon)]
        total += point[0] * nxt[1] - nxt[0] * point[1]
    return abs(total) / 2.0
