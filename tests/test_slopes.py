"""The ground underfoot, and the hills beyond it.

Two scales, one answer: the near field is the slope of the cell, the far field
is the ring from five kilometres out, and the sun is blocked by whichever
reaches higher in its direction.
"""
from __future__ import annotations

import pytest

from ninanatur.garden.slopes import MIN_SLOPE_DEG, ring_for, slope_at
from ninanatur.geo.terrain import TerrainWindow


def _plane(rise_north: float = 0.0, rise_east: float = 0.0, size: int = 60) -> TerrainWindow:
    heights = [
        100.0 + (row - size / 2) * rise_north + (col - size / 2) * rise_east
        for row in range(size)
        for col in range(size)
    ]
    return TerrainWindow(
        min_x=-size / 2, min_y=-size / 2, cell_m=1.0, cols=size, rows=size,
        heights=heights, source="Test", licence="—", attribution="—",
        vertical_step_m=0.01,
    )


# --- reading the slope ------------------------------------------------------

def test_a_slope_climbing_north_points_north() -> None:
    slope, aspect = slope_at(_plane(rise_north=0.10), 0.0, 0.0)
    assert slope == pytest.approx(5.7, abs=0.3)
    assert aspect == pytest.approx(0.0, abs=1.0)


def test_a_slope_climbing_south_points_south() -> None:
    """The sign, which is the thing most easily got backwards — and getting it
    backwards would put every shadow on the sunny side."""
    _, aspect = slope_at(_plane(rise_north=-0.10), 0.0, 0.0)
    assert aspect == pytest.approx(180.0, abs=1.0)


def test_a_slope_climbing_east_points_east() -> None:
    _, aspect = slope_at(_plane(rise_east=0.10), 0.0, 0.0)
    assert aspect == pytest.approx(90.0, abs=1.0)


def test_flat_ground_has_no_slope_and_no_direction() -> None:
    assert slope_at(_plane(), 0.0, 0.0) == (0.0, 0.0)


def test_a_slope_inside_the_models_own_noise_is_not_reported() -> None:
    """± 0.3 m over a few metres is more than a degree. A gentler reading than
    the threshold is not a gentle slope, it is the error bar."""
    gentle = _plane(rise_north=0.005)  # 0.3°
    assert slope_at(gentle, 0.0, 0.0) == (0.0, 0.0)
    assert MIN_SLOPE_DEG > 0.3


def test_unsurveyed_ground_has_no_slope_rather_than_a_wrong_one() -> None:
    assert slope_at(_plane(rise_north=0.10), 5000.0, 5000.0) == (0.0, 0.0)


# --- turning it into a sky --------------------------------------------------

def test_the_ring_peaks_looking_straight_uphill() -> None:
    ring = ring_for(None, slope=10.0, aspect=180.0)
    assert ring[180] == pytest.approx(10.0, abs=0.01)
    assert ring[0] == pytest.approx(0.0, abs=0.01)


def test_looking_along_the_contour_the_ground_stands_at_nothing() -> None:
    ring = ring_for(None, slope=20.0, aspect=180.0)
    assert ring[90] == pytest.approx(0.0, abs=0.01)
    assert ring[270] == pytest.approx(0.0, abs=0.01)


def test_ground_falling_away_does_not_shade() -> None:
    """Downhill the land is below the point. A negative horizon would say the
    sun arrives from underneath."""
    assert min(ring_for(None, slope=30.0, aspect=180.0)) >= 0.0


def test_the_higher_of_the_two_wins_in_each_direction() -> None:
    """Near and far are not added. Whichever blocks the sun first is the one
    that blocks it."""
    far = [0.0] * 360
    far[90] = 15.0
    ring = ring_for(far, slope=10.0, aspect=180.0)

    assert ring[90] == pytest.approx(15.0, abs=0.01), "the hill to the east wins there"
    assert ring[180] == pytest.approx(10.0, abs=0.01), "the slope wins to the south"


def test_flat_ground_leaves_the_far_horizon_alone() -> None:
    far = [3.0] * 360
    assert list(ring_for(far, slope=0.0, aspect=0.0)) == far


# --- through the light grid ------------------------------------------------

def _garden() -> tuple[object, list[object]]:
    import sqlite3

    from ninanatur.garden.elements import insert_element
    from ninanatur.garden.models import PLANTING_KIND
    from ninanatur.garden.store import create_garden, load_garden
    from ninanatur.ingest.db import connect, init_schema

    conn: sqlite3.Connection = connect(":memory:")
    init_schema(conn)
    garden_id = create_garden(conn, name="G", latitude=52.0, longitude=10.0)
    insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
                   name="Beet", points=[[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]])
    conn.commit()
    return load_garden(conn, garden_id), []


def _mean(grid: object) -> float:
    hours = grid.hours  # type: ignore[attr-defined]
    return sum(hours) / len(hours)


def test_a_ring_below_the_models_own_floor_changes_nothing() -> None:
    """Potsdam's horizon is 4.8°, and the model already stops counting the sun
    below 5°. In the North German Plain this feature is correctly inert — and a
    feature that appears to do nothing must be shown to be doing nothing on
    purpose."""
    from ninanatur.garden.lightgrid import compute_grid

    garden, obstacles = _garden()
    without = compute_grid(garden, obstacles)  # type: ignore[arg-type]
    with_low_hills = compute_grid(garden, obstacles, horizon=[4.0] * 360)  # type: ignore[arg-type]

    assert without is not None and with_low_hills is not None
    assert _mean(with_low_hills) == pytest.approx(_mean(without), abs=0.001)


def test_a_valley_takes_hours_off_the_whole_garden() -> None:
    from ninanatur.garden.lightgrid import compute_grid

    garden, obstacles = _garden()
    open_sky = compute_grid(garden, obstacles)  # type: ignore[arg-type]
    in_a_valley = compute_grid(garden, obstacles, horizon=[20.0] * 360)  # type: ignore[arg-type]

    assert open_sky is not None and in_a_valley is not None
    assert _mean(in_a_valley) < _mean(open_sky) - 2.0


def test_a_slope_rising_to_the_south_takes_the_low_southern_sun() -> None:
    """The near field, which no horizon measured at 20 m over five kilometres
    could see: the bank at the end of the garden."""
    from ninanatur.garden.lightgrid import compute_grid

    garden, obstacles = _garden()
    flat = compute_grid(garden, obstacles, ground=_plane(size=120))  # type: ignore[arg-type]
    into_the_hill = compute_grid(  # type: ignore[arg-type]
        garden, obstacles, ground=_plane(rise_north=-0.30, size=120)
    )

    assert flat is not None and into_the_hill is not None
    assert _mean(into_the_hill) < _mean(flat)


def test_a_slope_changes_the_hours_far_less_than_it_changes_a_garden() -> None:
    """The honest limit of this whole wave, measured rather than asserted.

    A 17° slope at 52°N barely moves the **hours**: the noon sun runs from 38°
    at the equinox to 61° at midsummer and clears a 17° southern skyline easily,
    and the low sun that a slope does block is largely below the 5° the model
    already stops counting at.

    Flat gives 12.58 h. Falling to the south — the sunny aspect — gives 12.38,
    and rising to the south gives 12.50. **Both slopes lose a little, and the
    sunny one loses slightly more**, because the ground behind it blocks the low
    northern sun of a midsummer morning.

    None of that means the two are alike to plant in. A north-facing bank
    receives far less energy per square metre than a south-facing one at the
    same number of hours, and this model reports hours. That is why feature 5
    names the slope on the page instead of folding it into the light score, and
    why nobody should read "12.5 h" on a north bank as "as good as flat".
    """
    from ninanatur.garden.lightgrid import compute_grid

    garden, obstacles = _garden()
    flat = compute_grid(garden, obstacles, ground=_plane(size=120))  # type: ignore[arg-type]
    sunny = compute_grid(  # type: ignore[arg-type]
        garden, obstacles, ground=_plane(rise_north=0.30, size=120)
    )
    shady = compute_grid(  # type: ignore[arg-type]
        garden, obstacles, ground=_plane(rise_north=-0.30, size=120)
    )

    assert flat is not None and sunny is not None and shady is not None
    assert abs(_mean(sunny) - _mean(flat)) < 0.5
    assert abs(_mean(shady) - _mean(flat)) < 0.5
