"""The sun's share weighted by what it brings — Wave 26, feature 4 (doc 119).

Checked by what the weighting must be: the beam in its closed form, the
incidence on a tilted surface against the formula done by hand, grid and point
agreeing on tilted cells, and the two errors docs 71 and 72 named — a lost low
sun costing as much as a lost high one, a slope turned away gaining — gone.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from ninanatur.solar.beam import beam
from ninanatur.solar.climate import climate_at
from ninanatur.solar.position import Location
from ninanatur.solar.raster import (
    Incidence,
    moments_for,
    parts_of,
    plane_of,
    point_sweep,
    sun_directions,
)
from ninanatur.solar.raster_grid import Cells, grid_sweep
from ninanatur.solar.relative import point_sky_light
from ninanatur.solar.shading import Obstacle

WUPPERTAL = Location(51.25, 7.15)
CLIMATE = climate_at(51.25, 7.15)


def test_the_beam_is_kasten_and_youngs_air_mass_through_meinels_atmosphere() -> None:
    for h in (5.0, 20.0, 45.0, 90.0):
        mass = 1 / (math.sin(math.radians(h)) + 0.50572 * (h + 6.07995) ** -1.6364)
        assert float(beam(np.array([h]))[0]) == pytest.approx(0.7 ** (mass ** 0.678))
    values = beam(np.linspace(1.0, 90.0, 200))
    assert np.all(np.diff(values) > 0), "a higher sun brings more"
    assert float(beam(np.array([3.0]))[0]) < 0.25 < 0.7 < float(beam(np.array([90.0]))[0]) + 0.01


def _energy(parts: list, x: float, y: float, plane: tuple[float, float, float] = (1.0, 0.0, 0.0),
            ring: list[float] | None = None) -> tuple[float, float]:
    """(lit hours, lit energy) over a season, one group each."""
    moments = moments_for(WUPPERTAL)
    directions = sun_directions(moments)
    one = np.zeros(len(moments.azimuth), dtype=int)
    incidence = Incidence(beam=beam(moments.altitude), group=one, groups=1)
    sums, energy = point_sweep(parts, directions, x, y, ring=ring, incidence=incidence,
                               plane=plane)
    return float(sums.sum()), float(energy[0])


def test_a_lost_low_sun_costs_less_than_a_lost_high_one() -> None:
    """A fence takes the low sun, a mast right beside the bed the noon sun. By
    hours both cost what they cost; by energy the fence's loss is the smaller."""
    open_hours, open_energy = _energy([], 0.0, 0.0)
    fence = parts_of([Obstacle(footprint=[(-20, -1.5), (20, -1.5), (20, -1.3), (-20, -1.3)],
                               height=1.8)])
    mast = parts_of([Obstacle(footprint=[(-0.6, -2.0), (0.6, -2.0), (0.6, -1.4), (-0.6, -1.4)],
                              height=30.0)])
    for parts, darker in ((fence, "hours"), (mast, "energy")):
        hours, energy = _energy(parts, 0.0, 0.0)
        by_hours, by_energy = hours / open_hours, energy / open_energy
        assert (by_hours < by_energy) if darker == "hours" else (by_energy < by_hours), \
            (darker, by_hours, by_energy)


def test_the_incidence_on_a_slope_is_the_formula() -> None:
    """cos i = sin h cos s − cos h sin s cos(A − a), aspect uphill; the sun
    behind the surface brings nothing. Done by hand over the season."""
    moments = moments_for(WUPPERTAL)
    h, az = np.radians(moments.altitude), np.radians(moments.azimuth)
    for slope, aspect in ((30.0, 0.0), (30.0, 180.0), (20.0, 90.0)):
        s, a = math.radians(slope), math.radians(aspect)
        cos_i = np.sin(h) * math.cos(s) - np.cos(h) * math.sin(s) * np.cos(az - a)
        expected = float(np.sum(beam(moments.altitude) * np.maximum(cos_i, 0.0)))
        _, energy = _energy([], 0.0, 0.0, plane_of(slope, aspect))
        assert energy == pytest.approx(expected)


def test_a_slope_facing_the_sun_takes_more_than_level_ground_and_one_facing_away_less() -> None:
    """Uphill to the north is a south face. The north face 'gained' hours by
    seeing over what stood below it; it gains no energy (docs 71, 72)."""
    level = point_sky_light([], moments_for(WUPPERTAL), CLIMATE, 0.0, 0.0)
    south = point_sky_light([], moments_for(WUPPERTAL), CLIMATE, 0.0, 0.0,
                            plane=plane_of(25.0, 0.0))
    north = point_sky_light([], moments_for(WUPPERTAL), CLIMATE, 0.0, 0.0,
                            plane=plane_of(25.0, 180.0))
    assert float(level.relative[0]) == pytest.approx(1.0)
    assert float(south.relative[0]) > 1.05 > 0.95 > float(north.relative[0])
    for light in (south, north):  # the hours are hours
        assert float(light.morning[0] + light.afternoon[0]) == pytest.approx(
            float(level.morning[0] + level.afternoon[0]))


def test_the_grid_says_of_a_tilted_cell_what_the_point_says() -> None:
    house = Obstacle(footprint=[(-6.0, 0.0), (6.0, 0.0), (6.0, 8.0), (-6.0, 8.0)], height=8.0)
    parts, moments = parts_of([house]), moments_for(WUPPERTAL)
    directions = sun_directions(moments)
    incidence = Incidence(beam=beam(moments.altitude), group=np.zeros(len(moments.azimuth),
                                                                     dtype=int), groups=1)
    xs = np.arange(-9.5, 12.0, 1.5)
    n = len(xs)
    slopes = np.linspace(0.0, 35.0, n)[None, :].repeat(n, axis=0)
    aspects = np.linspace(0.0, 350.0, n)[:, None].repeat(n, axis=1)
    plane = np.array([plane_of(float(s), float(a)) for s, a in
                      zip(slopes.ravel(), aspects.ravel(), strict=True)]).T.reshape(3, n, n)
    cells = Cells(xs=xs, ys=xs.copy(), cell_m=1.5, z=np.zeros((n, n)),
                  owner=np.full((n, n), -1), sky=np.full((n, n), -1),
                  rings=np.empty((0, 360)), plane=plane)
    sums, energy = grid_sweep(parts, directions, cells, incidence)
    for r, c in ((0, 0), (3, 7), (6, 13), (12, 3), (13, 13)):
        point, lit = point_sweep(parts, directions, float(xs[c]), float(xs[r]),
                                 incidence=incidence, plane=tuple(plane[:, r, c]))
        assert float(energy[0, r, c]) == pytest.approx(float(lit[0]), abs=1e-9)
        assert float(sums[:, r, c].sum()) == pytest.approx(float(point.sum()), abs=1e-9)


def test_a_garden_on_a_south_facing_hillside_is_lighter_than_on_level_ground() -> None:
    """Through the whole path: the ground's own slope turns each cell's surface
    (`lightcells.surface_at`), and the relative light says so."""
    from ninanatur.garden.lightgrid import compute_grid
    from ninanatur.garden.models import PLANTING_KIND, Element, Garden
    from ninanatur.geo.terrain import TerrainWindow

    bed = Element(element_id=1, kind=PLANTING_KIND, shape="polygon", x=0.0, y=0.0,
                  points=[[-5.0, -5.0], [5.0, -5.0], [5.0, 5.0], [-5.0, 5.0]])
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="G", latitude=51.25,
                    longitude=7.15, created_at="", updated_at="", elements=[bed])
    size = 120

    def hill(rise_north: float) -> TerrainWindow:
        return TerrainWindow(
            min_x=-60.0, min_y=-60.0, cell_m=1.0, cols=size, rows=size,
            heights=[100.0 + (row - size / 2) * rise_north for row in range(size)
                     for _ in range(size)],
            source="Test", licence="—", attribution="—", vertical_step_m=0.01)

    means: dict[str, float] = {}
    hours: dict[str, float] = {}
    for name, rise in (("level", 0.0), ("south face", 0.4), ("north face", -0.4)):
        grid = compute_grid(garden, [], ground=hill(rise))
        assert grid is not None
        relative = grid.mean_over(bed.polygon, grid.relative)
        lit = grid.mean_over(bed.polygon)
        assert relative is not None and lit is not None
        means[name], hours[name] = relative, lit
    assert means["level"] == pytest.approx(1.0, abs=0.01)
    assert means["south face"] > means["level"] + 0.05
    assert means["north face"] < means["level"] - 0.05
    # Doc 72's complaint, in one line: at 51° N the June sun rises and sets
    # north of east and west, and a south-facing slope's own ground stands in
    # front of it then. By hours the north face is the brighter bed.
    assert hours["north face"] > hours["south face"]
    assert means["north face"] < means["south face"] - 0.2


def test_a_roofs_pitches_take_the_light_at_their_own_angles() -> None:
    """The other half of a cell's surface: a roof's pitch (doc 119). With the
    aspect flipped the two pitches simply swapped, and the whole suite stayed
    green (review, 2026-09-22)."""
    from ninanatur.garden.lightgrid import compute_grid
    from ninanatur.garden.models import Element, Garden

    house = Element(element_id=2, kind="house", shape="polygon", x=0.0, y=0.0,
                    points=[[-6.0, -5.0], [6.0, -5.0], [6.0, 5.0], [-6.0, 5.0]],
                    height=9.0, roof="gable", eaves_m=5.0)
    lawn = Element(element_id=1, kind="garden", shape="polygon", x=0.0, y=0.0,
                   points=[[-12.0, -12.0], [12.0, -12.0], [12.0, 12.0], [-12.0, 12.0]])
    garden = Garden(garden_id=1, share_token="t", owner_id=None, name="G", latitude=51.25,
                    longitude=7.15, created_at="", updated_at="", elements=[lawn, house])
    grid = compute_grid(garden, [])
    assert grid is not None

    def pitch(southward: bool) -> float:
        """The mean relative light of the roof cells on one side of the ridge,
        read straight off the grid: `mean_over` leaves roofs out, on purpose."""
        values = []
        for row in range(grid.rows):
            for col in range(grid.cols):
                index = row * grid.cols + col
                x, y = grid.centre_of(col, row)
                if not grid.is_roof(index) or abs(x) > 5.5 or abs(y) > 4.5:
                    continue
                value = grid.relative[index]
                if value is not None and ((y < -0.5) if southward else (y > 0.5)):
                    values.append(value)
        assert values, "the roof has cells"
        return sum(values) / len(values)

    south, north = pitch(southward=True), pitch(southward=False)
    assert south > 1.0 > north, (south, north)
    assert south - north > 0.25, "the two pitches are not interchangeable"
