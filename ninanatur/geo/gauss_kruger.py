"""Gauss–Krüger coordinates, for the DWD's climate grids (doc 118).

The Deutscher Wetterdienst publishes its 1 km grids of Germany in the old
Gauss–Krüger system, third meridian strip: Bessel's 1841 ellipsoid, central
meridian 9° E, scale 1, false easting 3,500 km. A garden is in WGS84. This is
Krüger's series for a transverse Mercator on any ellipsoid — the series
`geokachel.utm` uses for GRS80, which the test holds this to.

No datum shift: Potsdam datum and WGS84 differ by some hundred metres here,
and the grid this reads is 10 km (`solar.climate`).
"""
from __future__ import annotations

import math

#: Bessel 1841, the ellipsoid of the Potsdam datum.
BESSEL_A_M = 6377397.155
BESSEL_F = 1 / 299.1528128
#: The third meridian strip.
GK3_MERIDIAN = 9.0
GK3_FALSE_EASTING_M = 3_500_000.0


def transverse_mercator(latitude: float, longitude: float, *, a: float, f: float,
                        meridian: float, scale: float, false_easting: float,
                        ) -> tuple[float, float]:
    """Easting and northing in metres."""
    n = f / (2 - f)
    radius = a / (1 + n) * (1 + n**2 / 4 + n**4 / 64)
    alpha = (n / 2 - 2 * n**2 / 3 + 5 * n**3 / 16,
             13 * n**2 / 48 - 3 * n**3 / 5,
             61 * n**3 / 240)
    e = math.sqrt(f * (2 - f))
    phi = math.radians(latitude)
    lam = math.radians(longitude - meridian)
    t = math.sinh(math.atanh(math.sin(phi)) - e * math.atanh(e * math.sin(phi)))
    xi = math.atan(t / math.cos(lam))
    eta = math.atanh(math.sin(lam) / math.hypot(1, t))
    easting, northing = eta, xi
    for j, coefficient in enumerate(alpha, start=1):
        easting += coefficient * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
        northing += coefficient * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
    return scale * radius * easting + false_easting, scale * radius * northing


def to_gauss_kruger(latitude: float, longitude: float) -> tuple[float, float]:
    """Right and height values (Rechtswert, Hochwert) in the third strip."""
    return transverse_mercator(latitude, longitude, a=BESSEL_A_M, f=BESSEL_F,
                               meridian=GK3_MERIDIAN, scale=1.0,
                               false_easting=GK3_FALSE_EASTING_M)


__all__ = ["to_gauss_kruger", "transverse_mercator"]
