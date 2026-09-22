"""A garden's light climate from the DWD's grids (doc 118).

The table is `ninanatur/data/climate_de.json.gz`, made by
`scripts/dwd_climate.py`; these read it as the model does and check it is
what it says it is. The projection into the grid's Gauss–Krüger coordinates is
checked against geokachel's UTM, which is the same series on another
ellipsoid.
"""
from __future__ import annotations

import random

from geokachel import utm

from ninanatur.geo.gauss_kruger import transverse_mercator
from ninanatur.solar.climate import climate_at


def test_the_projection_is_krugers_series_as_geokachel_computes_it() -> None:
    rng = random.Random(118)
    for _ in range(200):
        lat, lon = rng.uniform(47, 55.5), rng.uniform(6, 15)
        mine = transverse_mercator(lat, lon, a=utm.SEMI_MAJOR_M, f=utm.FLATTENING,
                                   meridian=9.0, scale=utm.SCALE,
                                   false_easting=utm.FALSE_EASTING_M)
        theirs = utm.to_utm(lat, lon, 32)
        assert abs(mine[0] - theirs[0]) < 1e-6 and abs(mine[1] - theirs[1]) < 1e-6


def test_a_german_garden_has_the_growing_season_from_the_dwd() -> None:
    wuppertal = climate_at(51.25, 7.15)
    assert wuppertal.months == (3, 4, 5, 6, 7, 8, 9, 10)
    assert not wuppertal.assumed
    assert wuppertal.licence == "CC-BY-4.0"
    # The DWD's own wording for values it did not publish as they stand.
    assert wuppertal.attribution == "Datenbasis: Deutscher Wetterdienst, Einzelwerte gemittelt"
    assert wuppertal.distance_km == 0.0
    assert all(40 < h < 200 for h in wuppertal.global_kwh_m2)
    assert all(0.3 < k < 0.7 for k in wuppertal.diffuse_fraction)
    assert all(80 < s < 280 for s in wuppertal.sunshine_h)
    # Summer's light is more than spring's and autumn's.
    assert max(wuppertal.global_kwh_m2) == max(wuppertal.global_kwh_m2[2:5])


def test_the_south_gets_more_light_than_the_north_in_spring_and_autumn() -> None:
    freiburg, kiel = climate_at(47.99, 7.85), climate_at(54.32, 10.14)
    for month in (3, 9, 10):
        k = freiburg.months.index(month)
        assert freiburg.global_kwh_m2[k] > kiel.global_kwh_m2[k]


def test_an_island_has_its_own_climate() -> None:
    """Helgoland's cell is three kilometre squares of land in a hundred of sea.
    A cell once needed half of them, and the island took the country's mean
    (review, 2026-09-22)."""
    for lat, lon in ((54.18, 7.89), (54.9, 8.3), (53.59, 6.67)):  # Helgoland, Sylt, Borkum
        island = climate_at(lat, lon)
        assert not island.assumed and island.distance_km == 0.0


def test_a_neighbouring_cell_stands_in_within_30_km_and_says_how_far() -> None:
    innsbruck = climate_at(47.27, 11.39)
    assert not innsbruck.assumed and 0 < innsbruck.distance_km <= 30
    rng = random.Random(30)
    for _ in range(400):
        near = climate_at(rng.uniform(46.5, 56.0), rng.uniform(4.5, 16.0))
        assert near.distance_km <= 30.0
        assert not (near.assumed and near.distance_km)


def test_beyond_the_grid_the_mean_stands_in_and_nothing_breaks() -> None:
    """A pole, or a point 90° from the grid's meridian, is where the projection
    is not defined; they were projected anyway, and POST /light answered 422."""
    for lat, lon in ((48.86, 2.35), (50.08, 14.44), (90.0, 10.0), (-90.0, 10.0),
                     (0.0, 99.0), (0.0, -81.0)):
        far = climate_at(lat, lon)
        assert far.assumed and far.distance_km == 0.0 and len(far.global_kwh_m2) == 8
