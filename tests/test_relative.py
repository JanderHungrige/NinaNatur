"""Relative illuminance and the sunshine to expect (doc 118).

Checked by what they must be: open ground has all of open ground's light and
exactly the sunshine the DWD measured there; a spot's relative illuminance is
the climate's months mixing its own direct share and sky share, recomputed here
from the pieces; and the grid says of a cell what the point path says of it.
"""
from __future__ import annotations

import calendar
import math

import numpy as np
import pytest

from ninanatur.solar.climate import climate_at
from ninanatur.solar.position import Location
from ninanatur.solar.raster import Directions, Moments, Part, moments_for, parts_of, point_sums
from ninanatur.solar.raster_grid import Cells
from ninanatur.solar.relative import grid_sky_light, point_sky_light
from ninanatur.solar.shading import Obstacle
from ninanatur.solar.sky import sky_directions

WUPPERTAL = Location(51.25, 7.15)
CLIMATE = climate_at(51.25, 7.15)
HOUSE = Obstacle(footprint=[(-6.0, 0.0), (6.0, 0.0), (6.0, 8.0), (-6.0, 8.0)], height=8.0)


def test_open_ground_has_all_its_light_and_the_sunshine_the_dwd_measured() -> None:
    light = point_sky_light([], moments_for(WUPPERTAL), CLIMATE, 0.0, 0.0)
    assert float(light.sky[0]) == pytest.approx(1.0)
    assert float(light.relative[0]) == pytest.approx(1.0)
    days = sum(calendar.monthrange(2026, m)[1] for m in CLIMATE.months)
    assert float(light.expected[0]) == pytest.approx(sum(CLIMATE.sunshine_h) / days)


def test_relative_light_is_the_months_mixing_direct_and_sky_light() -> None:
    """North of a house: its own sun hours by month over open ground's, and
    its share of the sky, mixed by the climate's diffuse fraction and weighted
    by each month's light."""
    moments = moments_for(WUPPERTAL)
    parts = parts_of([HOUSE])
    x, y = 0.0, 9.0
    sky = point_sums(parts, sky_directions(7), x, y)[0]
    light = open_light = 0.0
    for k, month in enumerate(CLIMATE.months):
        mine = _month_hours(parts, moments, month, x, y)
        possible = _month_hours([], moments, month, x, y)
        radiation, diffuse = CLIMATE.global_kwh_m2[k], CLIMATE.diffuse_fraction[k]
        light += radiation * ((1 - diffuse) * mine / possible + diffuse * sky)
        open_light += radiation
    got = point_sky_light(parts, moments, CLIMATE, x, y)
    assert float(got.sky[0]) == pytest.approx(sky)
    assert float(got.relative[0]) == pytest.approx(light / open_light)
    assert 0.3 < float(got.relative[0]) < 0.7, "a north bed is lighter than its hours"


def _month_hours(parts: list[Part], moments: Moments, month: int, x: float, y: float) -> float:
    """The month's sun samples that reach (x, y), each weighing one."""
    chosen = moments.month == month
    count = int(chosen.sum())
    directions = Directions(azimuth=moments.azimuth[chosen], altitude=moments.altitude[chosen],
                            month=moments.month[chosen], weight=np.ones(count),
                            group=np.zeros(count, dtype=int), groups=1)
    return float(point_sums(parts, directions, x, y)[0])


@pytest.mark.parametrize("month", [None, 3, 5])
def test_the_grid_says_of_a_cell_what_the_point_says(month: int | None) -> None:
    crown = Obstacle(footprint=[(12 + 3 * math.cos(a), 3 * math.sin(a))
                                for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)],
                     height=10.0, transmission=0.2, bare_transmission=0.75)
    parts, moments = parts_of([HOUSE, crown]), moments_for(WUPPERTAL, month=month)
    xs = np.arange(-9.5, 16.0, 1.5)
    n = len(xs)
    cells = Cells(xs=xs, ys=xs.copy(), cell_m=1.5, z=np.zeros((n, n)),
                  owner=np.full((n, n), -1), sky=np.full((n, n), -1), rings=np.empty((0, 360)))
    grid = grid_sky_light(parts, moments, cells, CLIMATE)
    for r, c in ((0, 0), (3, 7), (6, 14), (12, 3), (16, 16)):
        point = point_sky_light(parts, moments, CLIMATE, float(xs[c]), float(xs[r]))
        for name in ("sky", "relative", "expected", "morning", "afternoon"):
            assert float(getattr(grid, name)[r, c]) == pytest.approx(
                float(getattr(point, name)[0]), abs=1e-9), (name, r, c)


def test_a_bed_under_a_crown_is_darker_in_leaf_than_bare() -> None:
    crown = [Obstacle(footprint=[(3 * math.cos(a), 3 * math.sin(a))
                                 for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)],
                      height=10.0, transmission=0.2, bare_transmission=0.75)]
    parts = parts_of(crown)
    june = point_sky_light(parts, moments_for(WUPPERTAL, month=6), CLIMATE, 0.0, 0.0)
    march = point_sky_light(parts, moments_for(WUPPERTAL, month=3), CLIMATE, 0.0, 0.0)
    assert float(june.relative[0]) < float(march.relative[0])


def test_a_month_map_sees_the_sky_through_the_crowns_as_they_are_that_month() -> None:
    """March's map under a bare crown said it saw a fifth of the sky while
    counting three quarters of the light through it (review, 2026-09-22). A
    month shows its own sky; the season, the sky in leaf."""
    crown = [Obstacle(footprint=[(3 * math.cos(a), 3 * math.sin(a))
                                 for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)],
                      height=10.0, transmission=0.2, bare_transmission=0.75)]
    parts = parts_of(crown)
    bare = point_sums(parts, sky_directions(3), 0.0, 0.0)[0]
    leafy = point_sums(parts, sky_directions(7), 0.0, 0.0)[0]
    assert leafy < bare

    def sky(month: int | None) -> float:
        light = point_sky_light(parts, moments_for(WUPPERTAL, month=month), CLIMATE, 0.0, 0.0)
        return float(light.sky[0])

    assert sky(3) == pytest.approx(bare)
    assert sky(4) == pytest.approx(bare)
    assert sky(7) == pytest.approx(leafy)
    assert sky(None) == pytest.approx(leafy)
