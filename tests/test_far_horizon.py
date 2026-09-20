"""A horizon from Copernicus, for the states that have no service — doc 104.

No network: the degree cell is built here, with a hill in a known direction, so
the test can say where the land rises and then check that the ring says so too.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from tiff_builders import _tiled

from ninanatur.geo.far_horizon import cells_across, far_ring
from ninanatur.geo.projection import LatLon
from ninanatur.geo.tile_cache import TileCache

#: Munich: Bayern has no coverage service anybody may use, which is the point.
MUNICH = LatLon(lat=48.137, lon=11.575)
#: A GLO-30 cell at this latitude: 3,600 rows of one arcsecond, fewer columns.
ROWS, COLS = 360, 240


def _cell(build) -> bytes:
    """One degree of the earth, coarse enough to keep the test quick: the code
    reads the step from the raster rather than assuming an arcsecond."""
    values = np.zeros((ROWS, COLS), dtype="<f4")
    build(values)
    return _tiled(values, tile=128, compression=8)


def _flat(_values: np.ndarray) -> None:
    return None


def _hill_in_the_south_west(values: np.ndarray) -> None:
    """A hill about two kilometres south-west of Munich — inside the ring's
    five, which is the whole point: a hill thirteen kilometres away is a hill
    the ring is right to ignore.

    The cell runs 48–49°N and 11–12°E, rows from the north, so the garden sits
    at row (49 − 48.137) × 360 and column (11.575 − 11) × 240.
    """
    values[314:322, 128:136] = 900.0


def _cache(tmp_path: Path) -> TileCache:
    return TileCache(tmp_path, cap_bytes=50_000_000)


def test_the_cells_a_five_kilometre_ring_reaches_into() -> None:
    """One in the middle of a degree, more near its edge — a ring is 5 km and a
    garden does not know it is near a line on the map."""
    assert cells_across(LatLon(lat=48.5, lon=11.5)) == [(48, 11)]
    corner = cells_across(LatLon(lat=48.999, lon=11.999))
    assert sorted(corner) == [(48, 11), (48, 12), (49, 11), (49, 12)]


def test_flat_country_gets_a_flat_ring(tmp_path: Path) -> None:
    """Measured at Potsdam while Wave 17 was planned: 2.4° at most. A ring of
    zeros is the right answer in the North German Plain, not a broken one."""
    ring = far_ring(MUNICH, cache=_cache(tmp_path), fetch=lambda _u: _cell(_flat))
    assert ring is not None
    assert len(ring) == 360
    assert max(ring) == pytest.approx(0.0)


def test_a_hill_shows_up_in_the_direction_it_stands(tmp_path: Path) -> None:
    ring = far_ring(MUNICH, cache=_cache(tmp_path),
                    fetch=lambda _u: _cell(_hill_in_the_south_west))
    assert ring is not None
    # South-west is 225°; north-east, away from the hill, is 45°.
    assert ring[225] > 1.0, ring[225]
    assert ring[45] == pytest.approx(0.0)


def test_nothing_arrives_and_the_answer_is_none(tmp_path: Path) -> None:
    """None is "no ring", which the sync already knows how to leave alone —
    unlike a ring of zeros, which claims the horizon is flat."""
    def gone(_url: str) -> bytes:
        raise FileNotFoundError("s3")

    assert far_ring(MUNICH, cache=_cache(tmp_path), fetch=gone) is None


def test_a_cell_is_fetched_once_for_every_garden_in_it(tmp_path: Path) -> None:
    """A degree cell is seventy kilometres across. Two gardens in one are one
    request, which is what makes a 32 MB tile a reasonable thing to fetch."""
    asked: list[str] = []

    def counted(url: str) -> bytes:
        asked.append(url)
        return _cell(_flat)

    cache = _cache(tmp_path)
    far_ring(MUNICH, cache=cache, fetch=counted)
    far_ring(LatLon(lat=48.21, lon=11.62), cache=cache, fetch=counted)
    assert len(asked) == 1, asked
