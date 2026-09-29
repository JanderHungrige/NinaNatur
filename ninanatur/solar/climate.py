"""A garden's light climate, from the DWD's grids — Wave 26, feature 3 (doc 118).

What the sky gives a garden, month by month from March to October: how much
light reaches level ground (global radiation), how much of it comes from the
sky rather than the sun (the diffuse fraction), and how long the sun shines.
A climatology rather than any year's weather — sunshine varies by 10–20 %
from one year to the next, and a planting is for years.

Read from `ninanatur/data/climate_de.json.gz`, which `scripts/dwd_climate.py`
makes from the Deutscher Wetterdienst's 1 km grids (CC BY 4.0), 10 km per
cell. A garden in a cell without values — the sea, the far side of a border —
takes the nearest cell whose centre is within 30 km of it, and says how far;
beyond that, the country's mean, and says it is assumed.
"""
from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ninanatur.geo.gauss_kruger import to_gauss_kruger

TABLE = Path(__file__).resolve().parent.parent / "data" / "climate_de.json.gz"
#: How far a neighbouring cell may stand in for a garden's own: its centre
#: within this distance of the garden.
NEAREST_M = 30_000.0
#: Where the grid can be at all. Outside it the projection is not even defined
#: everywhere (at a pole, or 90° from its meridian), so nothing is projected.
_LAT, _LON = (45.0, 57.0), (3.0, 17.0)


@dataclass(frozen=True)
class Climate:
    """One garden's months, March to October, in step."""

    months: tuple[int, ...]
    #: Light on level ground, kWh/m² in the month.
    global_kwh_m2: tuple[float, ...]
    #: Of that, the share that comes from the sky.
    diffuse_fraction: tuple[float, ...]
    #: Hours of sunshine in the month.
    sunshine_h: tuple[float, ...]
    source: str
    licence: str
    attribution: str
    #: True where the garden is beyond the grid and the country's mean stands in.
    assumed: bool = False
    #: How far the cell that stands in lies, km; 0 for the garden's own.
    distance_km: float = 0.0


@lru_cache(maxsize=1)
def _table() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(gzip.decompress(TABLE.read_bytes()))
    return loaded


def climate_at(latitude: float, longitude: float) -> Climate:
    """The light climate of the 10 km cell the garden lies in, or of the
    nearest one within 30 km that has values, or the country's mean."""
    table = _table()
    near = _nearest(table, latitude, longitude)
    values = None if near is None else _values(table, near[0])
    if near is None or values is None:
        return _climate(table, *_means(table), assumed=True)
    return _climate(table, *values, assumed=False, distance_km=round(near[1] / 1000, 1))


def _nearest(table: dict[str, Any], latitude: float, longitude: float,
             ) -> tuple[int, float] | None:
    """The garden's own cell if it has values (distance 0), else the cell with
    values whose centre is nearest and within `NEAREST_M`; None if none is."""
    if not (_LAT[0] <= latitude <= _LAT[1] and _LON[0] <= longitude <= _LON[1]):
        return None
    x, y = to_gauss_kruger(latitude, longitude)
    cell, cols, rows = float(table["cell_m"]), int(table["cols"]), int(table["rows"])
    col = math.floor((x - table["x0"]) / cell)
    row = math.floor((y - table["y0"]) / cell)
    if 0 <= col < cols and 0 <= row < rows and _values(table, row * cols + col) is not None:
        return row * cols + col, 0.0
    reach = math.ceil(NEAREST_M / cell) + 1
    found: list[tuple[float, int]] = []
    for r in range(max(row - reach, 0), min(row + reach + 1, rows)):
        for c in range(max(col - reach, 0), min(col + reach + 1, cols)):
            distance = math.hypot(table["x0"] + (c + 0.5) * cell - x,
                                  table["y0"] + (r + 0.5) * cell - y)
            if distance <= NEAREST_M and _values(table, r * cols + c) is not None:
                found.append((distance, r * cols + c))
    if not found:
        return None
    distance, index = min(found)
    return index, distance


def _values(table: dict[str, Any], index: int,
            ) -> tuple[list[float], list[float], list[float]] | None:
    months = [str(m) for m in table["months"]]
    found = [[table[key][m][index] for m in months]
             for key in ("global_kwh_m2", "diffuse_fraction", "sunshine_h")]
    if any(v is None for column in found for v in column):
        return None
    return found[0], found[1], found[2]


def _means(table: dict[str, Any]) -> tuple[list[float], list[float], list[float]]:
    def mean(key: str, month: int) -> float:
        values = [float(v) for v in table[key][str(month)] if v is not None]
        return sum(values) / len(values)
    return tuple([mean(key, m) for m in table["months"]]  # type: ignore[return-value]
                 for key in ("global_kwh_m2", "diffuse_fraction", "sunshine_h"))


def _climate(table: dict[str, Any], radiation: list[float], diffuse: list[float],
             sunshine: list[float], *, assumed: bool, distance_km: float = 0.0) -> Climate:
    return Climate(months=tuple(table["months"]), global_kwh_m2=tuple(radiation),
                   diffuse_fraction=tuple(diffuse), sunshine_h=tuple(sunshine),
                   source=table["source"], licence=table["licence"],
                   attribution=table["attribution"], assumed=assumed,
                   distance_km=distance_km)


__all__ = ["Climate", "climate_at"]
