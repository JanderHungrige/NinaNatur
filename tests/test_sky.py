"""The sky a cell sees (doc 118).

Checked where the answer is known in closed form: beside an infinitely long
wall seen at elevation β, the share of an isotropic sky that reaches level
ground is (1 + cos β) / 2 — to within what a patch tested at its centre can
say, which Reinhart's finer sky halves. The CIE overcast sky is three times as bright at the
zenith as at the horizon, so a wall — which hides the low sky — takes less of
it.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from ninanatur.solar.raster import parts_of, point_sums
from ninanatur.solar.shading import Obstacle
from ninanatur.solar.sky import REINHART, TREGENZA, TREGENZA_BANDS, sky_directions


def _wall(height: float, distance: float) -> list[Obstacle]:
    return [Obstacle(footprint=[(-5000.0, distance), (5000.0, distance), (5000.0, distance + 0.3),
                                (-5000.0, distance + 0.3)], height=height)]


@pytest.mark.parametrize(("split", "patches"), [(TREGENZA, 145), (REINHART, 577)])
def test_tregenzas_and_reinharts_patches_and_an_open_sky_is_whole(split: int,
                                                                  patches: int) -> None:
    assert sum(count for _, count in TREGENZA_BANDS) == 145
    for overcast in (True, False):
        directions = sky_directions(7, overcast, split)
        assert len(directions.azimuth) == patches
        assert directions.weight.sum() == pytest.approx(1.0)
        assert point_sums([], directions, 0.0, 0.0)[0] == pytest.approx(1.0)


@pytest.mark.parametrize(("split", "bound"), [(TREGENZA, 0.032), (REINHART, 0.013)])
def test_beside_a_long_wall_the_isotropic_sky_is_the_closed_form(split: int,
                                                                 bound: float) -> None:
    """Swept densely: three angles once passed a bound the sky broke at 58°
    (review, 2026-09-22). A patch tested at its centre counts wholly in or
    out, so the error peaks where a band's centre crosses the wall's top."""
    directions = sky_directions(7, overcast=False, split=split)
    worst = 0.0
    for beta in np.arange(1.0, 86.0, 0.25):
        height = 2.0 * math.tan(math.radians(beta))
        seen = point_sums(parts_of(_wall(height, 2.0)), directions, 0.0, 0.0)[0]
        worst = max(worst, abs(seen - (1 + math.cos(math.radians(beta))) / 2))
    assert bound - 0.005 < worst <= bound


@pytest.mark.parametrize(("split", "tolerance"), [(TREGENZA, 0.003), (REINHART, 0.001)])
def test_the_overcast_sky_is_moon_and_spencers(split: int, tolerance: float) -> None:
    """Luminance (1 + 2 sin a) / 3, the zenith three times the horizon: of its
    light on level ground, the share from below 24° is F(sin 24°) / F(1) with
    F(s) = (s²/2 + 2s³/3) / 3 — 0.109. Any sky that merely brightens upwards
    passed the test below; a 2:1 sky gives 0.126, an even one 0.165."""
    def f(s: float) -> float:
        return (s * s / 2 + 2 * s ** 3 / 3) / 3

    low = sky_directions(7, overcast=True, split=split)
    share = float(low.weight[low.altitude < 24.0].sum())
    assert share == pytest.approx(f(math.sin(math.radians(24.0))) / f(1.0), abs=tolerance)
    even = sky_directions(7, overcast=False, split=split)
    assert float(even.weight[even.altitude < 24.0].sum()) == pytest.approx(
        math.sin(math.radians(24.0)) ** 2, abs=tolerance)


def test_a_wall_takes_less_of_an_overcast_sky_than_of_an_even_one() -> None:
    parts = parts_of(_wall(5.0, 5.0))
    overcast = point_sums(parts, sky_directions(7), 0.0, 0.0)[0]
    even = point_sums(parts, sky_directions(7, overcast=False), 0.0, 0.0)[0]
    assert overcast > even


def test_a_crown_passes_more_of_the_sky_when_it_is_bare() -> None:
    crown = [Obstacle(footprint=[(3 * math.cos(a), 3 * math.sin(a))
                                 for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)],
                      height=10.0, transmission=0.2, bare_transmission=0.75)]
    parts = parts_of(crown)
    in_leaf = point_sums(parts, sky_directions(7), 0.0, 0.0)[0]
    bare = point_sums(parts, sky_directions(3), 0.0, 0.0)[0]
    assert in_leaf < bare < 1.0
