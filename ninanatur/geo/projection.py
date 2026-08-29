"""Latitude and longitude to the metres a garden plan is drawn in.

Equirectangular around an anchor point, which is exact enough here and wrong at
any larger scale: over the hundred metres a garden and its surroundings occupy,
the error against a proper projection is millimetres. Over a country it would be
kilometres, so this must not escape the garden.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Metres per degree of latitude. Constant enough at garden scale; longitude
# shrinks with the cosine of the latitude, which is the whole reason this
# function takes an anchor.
METRES_PER_DEGREE_LAT = 111_320.0


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


@dataclass(frozen=True)
class Metres:
    """Garden coordinates: x east, y north, both in metres from the anchor."""

    x: float
    y: float


def metres_per_degree_lon(anchor_lat: float) -> float:
    return METRES_PER_DEGREE_LAT * math.cos(math.radians(anchor_lat))


def to_metres(point: LatLon, anchor: LatLon) -> Metres:
    return Metres(
        x=(point.lon - anchor.lon) * metres_per_degree_lon(anchor.lat),
        y=(point.lat - anchor.lat) * METRES_PER_DEGREE_LAT,
    )


def to_latlon(point: Metres, anchor: LatLon) -> LatLon:
    return LatLon(
        lat=anchor.lat + point.y / METRES_PER_DEGREE_LAT,
        lon=anchor.lon + point.x / metres_per_degree_lon(anchor.lat),
    )


def bounding_box(anchor: LatLon, radius_m: float) -> tuple[float, float, float, float]:
    """(south, west, north, east) for a square of `radius_m` around the anchor."""
    dlat = radius_m / METRES_PER_DEGREE_LAT
    dlon = radius_m / metres_per_degree_lon(anchor.lat)
    return (anchor.lat - dlat, anchor.lon - dlon, anchor.lat + dlat, anchor.lon + dlon)


def centroid(points: list[LatLon]) -> LatLon:
    if not points:
        raise ValueError("a polygon with no points has no centroid")
    return LatLon(
        lat=sum(p.lat for p in points) / len(points),
        lon=sum(p.lon for p in points) / len(points),
    )
