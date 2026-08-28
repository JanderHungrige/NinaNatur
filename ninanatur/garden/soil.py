"""What the gardener can see, translated into what the data uses.

The user is never asked for an Ellenberg value. They pick a soil type and a
moisture level from what they can observe in their own garden, and the mapping
lives here — one table, arguable in one place.

Like the sun-hours conversion, this is a **convention**: a stated starting point
derived from how these soils typically behave, not a measurement.
"""
from __future__ import annotations


class SoilTypeError(ValueError):
    """An unrecognised soil type.

    Raised rather than defaulted: silently treating a typo as loam would produce
    confident and wrong plant suggestions with nothing to indicate why.
    """


class MoistureError(ValueError):
    """An unrecognised moisture level. Raised for the same reason."""


# soil type -> (reaction R, nutrients N)
SOIL_TO_RN: dict[str, tuple[float, float]] = {
    "sand": (4.0, 2.5),
    "loam": (6.5, 5.5),
    "clay": (7.0, 6.0),
    "humus": (6.0, 7.5),
}

# moisture -> M
MOISTURE_TO_M: dict[str, float] = {
    "dry": 2.5,
    "fresh": 5.0,
    "moist": 7.0,
    "wet": 8.5,
}


def site_axes_from_soil(soil_type: str, moisture: str) -> dict[str, float]:
    """Turn a gardener's description into the R, N and M axes."""
    if soil_type not in SOIL_TO_RN:
        raise SoilTypeError(
            f"unknown soil type {soil_type!r}; expected one of {sorted(SOIL_TO_RN)}"
        )
    if moisture not in MOISTURE_TO_M:
        raise MoistureError(
            f"unknown moisture {moisture!r}; expected one of {sorted(MOISTURE_TO_M)}"
        )
    reaction, nutrients = SOIL_TO_RN[soil_type]
    return {
        "ellenberg_r": reaction,
        "ellenberg_n": nutrients,
        "ellenberg_m": MOISTURE_TO_M[moisture],
    }
