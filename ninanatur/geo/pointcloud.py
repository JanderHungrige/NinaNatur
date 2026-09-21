"""What the laser saw — Wave 25, feature 4 (doc 107).

A surface raster says how tall the thing standing here is. It cannot say what
the thing is, and it cannot see under it: doc 84's complaint that "a marquee and
a tree read the same" is a property of the product, not of the reading. The
laser points the raster was made from can do better, because a tree lets light
through and a roof does not — a crown returns at its top, in its middle and on
the ground beneath it, and a roof returns once.

So this reads the points, and three layers come out of them, each on the
garden's own axes:

- **ground** — the lowest return classified as ground in each cell;
- **surface** — the highest return of any kind;
- **crown base** — for a cell with vegetation in it, the lowest return that is
  properly above the ground, which is where the canopy starts. Nothing else in
  this project knows it, and the shading model needs it: a crown is not a
  cylinder standing on the soil, it is a lamp on a stick.

**Which returns are vegetation is not a question the classification answers.**
Doc 107 has the measurement: Nordrhein-Westfalen's tile is 76 % ground, and
everything standing is class 1 or class 20 with no building or vegetation code
anywhere. Buildings are told apart by the building model instead (doc 105) —
their footprints come in as polygons, and what stands inside one is a roof.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from geokachel.utm import to_utm

from ninanatur.geo.projection import LatLon
from ninanatur.geo.terrain import frame_map

log = logging.getLogger(__name__)

#: How far out the cloud is read, in metres: the garden, the fifty metres of
#: neighbours the obstacle model already reaches (`surroundings.MARGIN_M`), and
#: room for a tall tree's shadow to come from.
REACH_M = 150.0
#: Ground, in every state's classification and in the standard's.
GROUND_CLASS = 2
#: Points this far above the ground are a thing rather than the ground's own
#: roughness: kerbs, cars and hedges start here.
STANDING_M = 1.0
#: Below this the returns in a cell are one measurement, not a canopy.
CROWN_RETURNS = 3
#: Half a metre needs about eight points a square metre to have one per cell.
#: Below that the honest raster is a metre, and the window says which it is.
DENSE_ENOUGH = 8.0
FINE_CELL_M = 0.5
COARSE_CELL_M = 1.0
#: How far a hole in the ground may be closed from its rim, in cells: fifty
#: metres of building at the coarse cell, a hundred at the fine one.
MAX_FILL_PASSES = 50
#: Points the reader hands over at a time. Measured (doc 107): a million costs
#: 226 MB of peak memory for a 35 MB tile, a quarter of a million costs a
#: quarter of that, and the reading is no slower. The tile itself is never held
#: — it is read from the file on the volume.
CHUNK_POINTS = 250_000


@dataclass(frozen=True)
class CloudWindow:
    """What the laser saw around one garden, on the garden's own axes.

    Row-major from the south-west corner, like `TerrainWindow`, so the two can
    be indexed the same way. NaN is a cell the laser did not reach.
    """

    min_x: float
    min_y: float
    cell_m: float
    cols: int
    rows: int
    #: Metres above sea level: the lowest ground return in the cell.
    ground: list[float]
    #: Metres above sea level: the highest return of any kind.
    surface: list[float]
    #: Metres above the ground: where a canopy starts, in the cells that have
    #: one. NaN everywhere else, including over roofs.
    crown_base: list[float]
    source: str
    licence: str
    attribution: str
    points_per_m2: float

    def height_at(self, x: float, y: float) -> float | None:
        """How tall the thing standing here is, or None outside the window."""
        index = self._index(x, y)
        if index is None:
            return None
        above = self.surface[index] - self.ground[index]
        return None if math.isnan(above) else above

    def crown_at(self, x: float, y: float) -> float | None:
        """Where the canopy starts here, in metres above the ground."""
        index = self._index(x, y)
        if index is None:
            return None
        value = self.crown_base[index]
        return None if math.isnan(value) else value

    def _index(self, x: float, y: float) -> int | None:
        col = int((x - self.min_x) // self.cell_m)
        row = int((y - self.min_y) // self.cell_m)
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return None
        return row * self.cols + col


def cell_for(points_per_m2: float) -> float:
    """The honest cell size for this density (doc 107).

    At four points a square metre a half-metre cell holds one point on average,
    and a raster whose cells are mostly one measurement is a picture of the
    sampling rather than of the garden.
    """
    return FINE_CELL_M if points_per_m2 >= DENSE_ENOUGH else COARSE_CELL_M


def _to_garden(anchor: LatLon, zone: int, east: np.ndarray,
               north: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Every point in the garden's frame.

    The inverse of `frame_map`, which is a rotation and a scale over this
    distance — UTM grid north is up to 2.3° off true north here, and binning on
    the grid's axes would turn every shadow by two degrees (doc 17).
    """
    origin, per_x, per_y = frame_map(anchor, zone)
    determinant = per_x[0] * per_y[1] - per_y[0] * per_x[1]
    de, dn = east - origin[0], north - origin[1]
    x = (de * per_y[1] - dn * per_y[0]) / determinant
    y = (dn * per_x[0] - de * per_x[1]) / determinant
    return x, y


def _bin(values: np.ndarray, flat: np.ndarray, size: int, how: object) -> np.ndarray:
    """One value per cell, by the rule given, NaN where nothing landed."""
    start = np.inf if how is np.minimum else -np.inf
    out = np.full(size, start, dtype="float64")
    how.at(out, flat, values)  # type: ignore[attr-defined]
    out[np.isinf(out)] = np.nan
    return out


def _filled(ground: np.ndarray, side: int) -> np.ndarray:
    """The ground under the things standing on it.

    A laser sees no ground beneath a roof, so the cells a building covers have
    no ground return at all — in the verified NRW tile, 4 % of them. Without
    this a house has no height, because its height is measured against a cell
    that is empty by construction.

    Filled by spreading the ground inwards from the edges of each hole: each
    pass gives an empty cell the mean of the neighbours that have a value, so
    a hole closes from its rim at one cell a pass. Enough passes to close a
    fifty-metre building, and it stops early when nothing changes.
    """
    filled = ground.reshape(side, side).copy()
    for _ in range(MAX_FILL_PASSES):
        empty = np.isnan(filled)
        if not empty.any():
            break
        padded = np.pad(filled, 1, constant_values=np.nan)
        stack = np.stack([padded[:-2, 1:-1], padded[2:, 1:-1],
                          padded[1:-1, :-2], padded[1:-1, 2:]])
        # The mean of the neighbours that have a value, counted rather than
        # `nanmean`-ed: most cells in a pass have no filled neighbour at all,
        # and the mean of nothing is a warning on every one of them.
        known = np.isfinite(stack)
        how_many = known.sum(axis=0)
        neighbours = np.where(how_many > 0,
                              np.where(known, stack, 0.0).sum(axis=0) / np.maximum(how_many, 1),
                              np.nan)
        spreading = empty & np.isfinite(neighbours)
        if not spreading.any():
            break
        filled[spreading] = neighbours[spreading]
    return filled.reshape(-1)


def _crown_bases(above: np.ndarray, flat: np.ndarray, size: int,
                 standing: np.ndarray) -> np.ndarray:
    """Where the canopy starts in each cell that has one.

    The lowest *standing* return, taken as the fifth percentile rather than the
    minimum so one stray return under a crown does not put the canopy on the
    ground — and only where a cell has enough returns to be a canopy rather
    than a single measurement.
    """
    out = np.full(size, np.nan)
    if not standing.any():
        return out
    cells, heights = flat[standing], above[standing]
    order = np.argsort(cells, kind="stable")
    cells, heights = cells[order], heights[order]
    edges = np.flatnonzero(np.diff(cells)) + 1
    for part_cells, part_heights in zip(np.split(cells, edges), np.split(heights, edges),
                                        strict=True):
        if len(part_heights) >= CROWN_RETURNS:
            out[part_cells[0]] = float(np.percentile(part_heights, 5))
    return out


def _inside_any(x: np.ndarray, y: np.ndarray,
                footprints: list[list[tuple[float, float]]]) -> np.ndarray:
    """Which points stand inside a surveyed building (doc 105).

    The classification cannot say — NRW's tile has no building code at all — so
    the building model does. A ray cast along +x, as everywhere else here.
    """
    inside = np.zeros(len(x), dtype=bool)
    for outline in footprints:
        if len(outline) < 3:
            continue
        crossings = np.zeros(len(x), dtype=bool)
        for (ax, ay), (bx, by) in zip(outline, [*outline[1:], outline[0]], strict=True):
            straddles = (ay > y) != (by > y)
            with np.errstate(divide="ignore", invalid="ignore"):
                at = ax + (y - ay) * (bx - ax) / np.where(by == ay, np.nan, by - ay)
            crossings ^= straddles & (x < at)
        inside |= crossings
    return inside


def window_from(tile: Path | bytes, anchor: LatLon, *, zone: int, source: str, licence: str,
                attribution: str,
                footprints: list[list[tuple[float, float]]] | None = None) -> CloudWindow | None:
    """Read one laser tile into the three layers around this garden.

    A path, so the points are streamed off the volume rather than held: the
    largest tile in the verified index is 445 MB and the whole budget is 300
    (doc 107). Bytes are accepted for a test, which builds its own tile.

    None where the tile holds nothing near the garden — a tile whose corner the
    window only touches, and every point of it hundreds of metres away.
    """
    import laspy  # noqa: PLC0415 - heavy, and only this path needs it

    east, north = to_utm(anchor.lat, anchor.lon, zone)
    kept: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
    with laspy.open(BytesIO(tile) if isinstance(tile, bytes) else tile) as reader:
        for chunk in reader.chunk_iterator(CHUNK_POINTS):
            cx, cy = np.asarray(chunk.x), np.asarray(chunk.y)
            near = ((cx >= east - REACH_M) & (cx < east + REACH_M)
                    & (cy >= north - REACH_M) & (cy < north + REACH_M))
            if near.any():
                kept.append((cx[near], cy[near], np.asarray(chunk.z)[near],
                             np.asarray(chunk.classification)[near]))
    if not kept:
        return None

    east_m = np.concatenate([part[0] for part in kept])
    north_m = np.concatenate([part[1] for part in kept])
    z = np.concatenate([part[2] for part in kept])
    classification = np.concatenate([part[3] for part in kept])
    density = len(z) / (2 * REACH_M) ** 2
    return _layers(_to_garden(anchor, zone, east_m, north_m), z, classification, density,
                   source=source, licence=licence, attribution=attribution,
                   footprints=footprints or [])


def _layers(garden_xy: tuple[np.ndarray, np.ndarray], z: np.ndarray,
            classification: np.ndarray, density: float, *, source: str, licence: str,
            attribution: str,
            footprints: list[list[tuple[float, float]]]) -> CloudWindow | None:
    """The three layers, binned on the garden's own axes."""
    x, y = garden_xy
    cell = cell_for(density)
    side = int(2 * REACH_M / cell)
    col = ((x + REACH_M) / cell).astype(np.int64)
    row = ((y + REACH_M) / cell).astype(np.int64)
    within = (col >= 0) & (col < side) & (row >= 0) & (row < side)
    if not within.any():
        return None
    col, row, z, classification = col[within], row[within], z[within], classification[within]
    x, y = x[within], y[within]
    flat = row * side + col
    size = side * side

    is_ground = classification == GROUND_CLASS
    measured = (_bin(z[is_ground], flat[is_ground], size, np.minimum)
                if is_ground.any() else np.full(size, np.nan))
    # Under a roof there is no ground return, by construction (see `_filled`).
    ground = _filled(measured, side)
    surface = _bin(z, flat, size, np.maximum)

    above = z - ground[flat]
    # A crown is what stands and is not a roof: the building model decides which
    # is which, because the classification does not (doc 107).
    standing = np.isfinite(above) & (above > STANDING_M) & ~_inside_any(x, y, footprints)
    crown = _crown_bases(above, flat, size, standing)

    return CloudWindow(
        min_x=-REACH_M, min_y=-REACH_M, cell_m=cell, cols=side, rows=side,
        ground=[float(v) for v in ground], surface=[float(v) for v in surface],
        crown_base=[float(v) for v in crown],
        source=source, licence=licence, attribution=attribution,
        points_per_m2=round(density, 1),
    )


__all__ = [
    "CHUNK_POINTS",
    "REACH_M",
    "STANDING_M",
    "CloudWindow",
    "cell_for",
    "window_from",
]
