"""ETRS89 geographic coordinates to UTM and back.

The state coverage services speak ETRS89/UTM — zone 32 or 33, EPSG 25832 or
25833. This app speaks metres east and north of a garden's anchor. Something has
to convert, and it is fifty lines of Krüger series rather than a dependency:
`pyproj` is a compiled wheel per platform for exactly these two formulas, and
this project ships a 10 MB image on purpose.

**The inverse is not optional, and the reason is orientation.** UTM's grid north
is not true north — the meridian convergence between them reaches about 2° at a
zone's edges, which is where a great deal of Germany sits. Pasting a UTM raster
into the garden's frame without going back through latitude and longitude would
turn a south-facing slope into one facing 2° off south, and rotate every hill in
the horizon ring by two of its one-degree bins. Cheap to avoid: convert each cell
centre back to lat/lon and then into garden metres, which is what the existing
`projection.to_metres` already does correctly.

Checked against control points in `tests/test_utm.py`: longitude 9° — zone 32's
central meridian — must return easting 500000.000 exactly, and Köln Dom must
land where Köln Dom is.
"""
from __future__ import annotations

import math

#: GRS80, which is what ETRS89 uses. Not WGS84's ellipsoid — they differ in the
#: flattening at the eleventh decimal, far below anything here, but naming the
#: right one costs nothing and saves the next reader the doubt.
SEMI_MAJOR_M = 6378137.0
FLATTENING = 1 / 298.257222101

#: Scale on the central meridian. 0.9996 is UTM's by definition.
SCALE = 0.9996

#: False easting. UTM puts the central meridian at 500 km so eastings stay
#: positive across the zone.
FALSE_EASTING_M = 500000.0

_N = FLATTENING / (2 - FLATTENING)
_E2 = FLATTENING * (2 - FLATTENING)
_RADIUS = SEMI_MAJOR_M / (1 + _N) * (1 + _N**2 / 4 + _N**4 / 64)

#: Krüger series coefficients, forward and inverse. Three terms is millimetres
#: at this latitude — far past what a ± 0.3 m terrain model can use.
_ALPHA = (
    _N / 2 - 2 * _N**2 / 3 + 5 * _N**3 / 16,
    13 * _N**2 / 48 - 3 * _N**3 / 5,
    61 * _N**3 / 240,
)
_BETA = (
    _N / 2 - 2 * _N**2 / 3 + 37 * _N**3 / 96,
    _N**2 / 48 + _N**3 / 15,
    17 * _N**3 / 480,
)


def zone_for(longitude: float) -> int:
    """The UTM zone a longitude falls in.

    Germany spans zones 32 and 33, and which one a service wants is recorded in
    the registry rather than derived — a garden near 12°E is in zone 33 by this
    rule while its state's service publishes in 32, and the service wins.
    """
    return int((longitude + 180) // 6) + 1


def central_meridian(zone: int) -> float:
    return zone * 6 - 183


def to_utm(latitude: float, longitude: float, zone: int) -> tuple[float, float]:
    """Easting and northing in metres, in the given zone."""
    lam = math.radians(longitude - central_meridian(zone))
    phi = math.radians(latitude)
    t = math.sinh(
        math.atanh(math.sin(phi))
        - math.sqrt(_E2) * math.atanh(math.sqrt(_E2) * math.sin(phi))
    )
    xi = math.atan(t / math.cos(lam))
    eta = math.atanh(math.sin(lam) / math.hypot(1, t))

    easting = eta
    northing = xi
    for j, alpha in enumerate(_ALPHA, start=1):
        easting += alpha * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
        northing += alpha * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
    return (
        SCALE * _RADIUS * easting + FALSE_EASTING_M,
        SCALE * _RADIUS * northing,
    )


def to_latlon(easting: float, northing: float, zone: int) -> tuple[float, float]:
    """Back to latitude and longitude. The half that keeps north pointing north."""
    xi = northing / (SCALE * _RADIUS)
    eta = (easting - FALSE_EASTING_M) / (SCALE * _RADIUS)

    xi_p = xi
    eta_p = eta
    for j, beta in enumerate(_BETA, start=1):
        xi_p -= beta * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
        eta_p -= beta * math.cos(2 * j * xi) * math.sinh(2 * j * eta)

    chi = math.asin(math.sin(xi_p) / math.cosh(eta_p))
    phi = chi
    # Three Newton steps on the isometric latitude. Converges far faster than
    # the tolerance of anything downstream.
    for _ in range(3):
        phi = math.asin(
            math.tanh(
                math.atanh(math.sin(chi))
                + math.sqrt(_E2) * math.atanh(math.sqrt(_E2) * math.sin(phi))
            )
        )
    lam = math.atan2(math.sinh(eta_p), math.cos(xi_p))
    return (math.degrees(phi), central_meridian(zone) + math.degrees(lam))


__all__ = ["central_meridian", "to_latlon", "to_utm", "zone_for"]
