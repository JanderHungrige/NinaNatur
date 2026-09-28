"""Print doc 120's "What moved" table: a roof cast as its planes, against the
block of `RISE_KEPT`'s averaged height it was cast as until Wave 26.

    python -m scripts.measure_roofs

A house 12 × 8 m, ridge 9 m and eaves 5 m, running east–west, its north wall at
y = −5; points on the house's axis 1, 3, 5 and 8 m north of that wall;
Wuppertal, the whole season, through the path the app computes light by
(`relative.point_sky_light`). Written because the table's first version named
the wrong distances and nobody could reproduce it (review, 2026-09-28).
"""
from __future__ import annotations

from ninanatur.garden.casting import casting
from ninanatur.garden.models import Element
from ninanatur.garden.roofs import Roof, shading_height
from ninanatur.solar.climate import climate_at
from ninanatur.solar.position import Location
from ninanatur.solar.raster import moments_for, parts_of
from ninanatur.solar.relative import point_sky_light
from ninanatur.solar.shading import Obstacle

HOUSE = [[-6.0, -13.0], [6.0, -13.0], [6.0, -5.0], [-6.0, -5.0]]
NORTH_WALL = -5.0
ROOFS: tuple[tuple[str, str, float | None], ...] = (
    ("gable", "gable", None), ("hip", "hip", None),
    ("pent falling north", "pent", 0.0), ("pent falling south", "pent", 180.0))


def _light(obstacle: Obstacle, y: float) -> tuple[float, float]:
    """(hours, sky) at the point on the house's axis at this y."""
    got = point_sky_light(parts_of([obstacle]), moments_for(Location(51.25, 7.15)),
                          climate_at(51.25, 7.15), 0.0, y)
    return float(got.morning[0] + got.afternoon[0]), float(got.sky[0])


def main() -> None:
    for name, roof, fall in ROOFS:
        element = Element(element_id=1, kind="house", shape="polygon", x=0.0, y=0.0,
                          points=HOUSE, height=9.0, roof=roof, eaves_m=5.0, roof_fall_deg=fall)
        block = Obstacle(footprint=element.footprint,
                         height=shading_height(9.0, Roof(roof), 5.0))
        print(f"{name} (the block stood at {block.height:.1f} m)")
        for north in (1.0, 3.0, 5.0, 8.0):
            (was, sky_was), (now, sky_now) = (_light(block, NORTH_WALL + north),
                                              _light(casting(element), NORTH_WALL + north))
            print(f"  {north:.0f} m north of the wall: {was:5.2f} h -> {now:5.2f} h, "
                  f"sky {sky_was:.3f} -> {sky_now:.3f}")


if __name__ == "__main__":
    main()
