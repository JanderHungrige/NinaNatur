"""Print doc 121's "What moved" table: a crown cast as an ellipsoid on a trunk,
against the cylinder from the ground a planted tree was, and the opaque block
a drawn one was, until Wave 26.

    python -m scripts.measure_crowns

A lime of 12 m, its crown 8 m across and starting at 4 m (a third of its
height, the assumption), standing at the origin; points at its foot and 3, 6
and 10 m north of it; Wuppertal, the whole season, through the path the app
computes light by (`relative.point_sky_light`) — sun hours, the sky seen in
leaf, and the light value.
"""
from __future__ import annotations

import math

from ninanatur.garden.canopies import FIRST_LEAF_MONTH, transmission
from ninanatur.solar import light
from ninanatur.solar.climate import climate_at
from ninanatur.solar.crown import Crown
from ninanatur.solar.position import Location
from ninanatur.solar.raster import moments_for, parts_of
from ninanatur.solar.relative import point_sky_light
from ninanatur.solar.shading import Obstacle

RING = [(4.0 * math.cos(math.tau * i / 24), 4.0 * math.sin(math.tau * i / 24))
        for i in range(24)]
LEAF, BARE = transmission(None, FIRST_LEAF_MONTH), transmission(None, 1)
CASTERS = {
    "block (a drawn tree)": Obstacle(footprint=RING, height=12.0),
    "cylinder (a planted tree)": Obstacle(footprint=RING, height=12.0, transmission=LEAF,
                                          bare_transmission=BARE),
    "crown": Obstacle(footprint=RING, height=12.0, transmission=LEAF, bare_transmission=BARE,
                      crown=Crown(x=0.0, y=0.0, radius=4.0, base=4.0, top=12.0)),
}


def main() -> None:
    wuppertal = Location(51.25, 7.15)
    moments, climate = moments_for(wuppertal), climate_at(51.25, 7.15)
    for north in (0.0, 3.0, 6.0, 10.0):
        print(f"{north:.0f} m north of the trunk:")
        for name, caster in CASTERS.items():
            got = point_sky_light(parts_of([caster]), moments, climate, 0.0, north)
            hours, sky = float(got.morning[0] + got.afternoon[0]), float(got.sky[0])
            value = light.light_value(round(hours, 2), round(sky, 3))
            print(f"  {name:26s} {hours:5.2f} h, sky {sky:.3f}, L {value:.2f}")


if __name__ == "__main__":
    main()
