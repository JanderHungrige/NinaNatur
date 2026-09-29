"""What a moment of sun brings — Wave 26, feature 4 (doc 119).

The clear-sky beam at a given altitude, relative to what arrives above the
atmosphere: through Kasten and Young's air mass (1989), attenuated as Meinel
and Meinel give it (1976). Altitude only — no data, no dependency. Every ratio
this project takes of it cancels the solar constant, which is why none is
here: the model weights moments by it and reports shares, never kWh.
"""
from __future__ import annotations

import numpy as np


def air_mass(altitude_deg: np.ndarray) -> np.ndarray:
    """Kasten and Young's relative optical air mass: 1 at the zenith, about 38
    at the horizon, finite all the way down."""
    h = np.asarray(altitude_deg, dtype=float)
    mass: np.ndarray = 1.0 / (np.sin(np.radians(h)) + 0.50572 * (h + 6.07995) ** -1.6364)
    return mass


def beam(altitude_deg: np.ndarray) -> np.ndarray:
    """The clear-sky beam normal to the sun, as a share of the extraterrestrial:
    0.7 ^ (m ^ 0.678). About 0.7 at the zenith, a tenth at 2°."""
    through: np.ndarray = 0.7 ** (air_mass(altitude_deg) ** 0.678)
    return through


__all__ = ["air_mass", "beam"]
