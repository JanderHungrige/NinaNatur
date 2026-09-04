"""What a roof does to the shadow a building casts.

OSM's `height` is the **ridge**, so a building modelled as a prism at that height
is a building whose gable ends are solid to the ridge. It shades too much,
everywhere, all season — and the taller the roof, the further the error reaches.

A roof shape is one of the few things somebody can answer by looking out of the
window, which is the test this project applies to every question it asks. So it
is asked, and where it is not answered the model says what it assumed.
"""
from __future__ import annotations

from enum import StrEnum


class Roof(StrEnum):
    """The shapes a house in Germany actually has.

    Stored as text, so a renamed member orphans saved rows — the values are part
    of the data.
    """

    FLAT = "flat"
    GABLE = "gable"
    HIP = "hip"
    PENT = "pent"
    #: Nobody has said. The model then treats the recorded height as solid,
    #: which is what it did for every building before this existed.
    UNKNOWN = "unknown"


#: How much of the roof's own rise still shades, as a fraction.
#:
#: A flat roof is the whole building at one height. A gable is a wedge: the
#: ridge is a line and the eaves are the edges, so averaged across the footprint
#: about half of the rise stands. A hip slopes on all four sides and stands for
#: less. A pent is a single slope and keeps more than a gable, because one whole
#: edge is at full height.
#:
#: These are ratios of a shape, not measurements of a building. They are here
#: rather than inline so that somebody who disagrees has one place to argue.
RISE_KEPT: dict[Roof, float] = {
    Roof.FLAT: 1.0,
    Roof.GABLE: 0.5,
    Roof.HIP: 0.4,
    Roof.PENT: 0.6,
    Roof.UNKNOWN: 1.0,
}

#: Where the eaves are when nothing says: three quarters of the way up.
#:
#: A two-storey German house is roughly 6 m to the eaves and 8 to the ridge.
#: `building:levels x 3 m` is the better answer wherever OSM carries it, and
#: this is what stands in when it does not — an assumption, and labelled as one
#: beside the assumed heights that are already there.
DEFAULT_EAVES_FRACTION = 0.75


def shading_height(
    height_m: float, roof: Roof = Roof.UNKNOWN, eaves_m: float | None = None
) -> float:
    """The height to shade with, given the ridge height and the roof.

    Never above the recorded height and never below the eaves: a roof takes
    something off the top and cannot take off the building.
    """
    if roof is Roof.UNKNOWN or roof is Roof.FLAT:
        return height_m
    eaves = DEFAULT_EAVES_FRACTION * height_m if eaves_m is None else eaves_m
    eaves = max(0.0, min(eaves, height_m))
    return eaves + RISE_KEPT[roof] * (height_m - eaves)


def eaves_from_levels(levels: float | None, storey_m: float = 3.0) -> float | None:
    """Eaves height from `building:levels`, or None.

    Floor to floor, which is what a storey count means. It is the one input here
    that is a measurement rather than a shape ratio, so it wins wherever OSM
    carries it.
    """
    if levels is None or levels <= 0:
        return None
    return levels * storey_m
