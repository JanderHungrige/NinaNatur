"""Measuring a building from a surface model, and refusing to when it cannot.

Windows are built here rather than fetched, so a tree can be put over a corner
on purpose. That case is the reason this module exists: measured while Wave 19
was planned, a 30 m² outbuilding read 17.0 m because a beech hangs over it.
"""
from __future__ import annotations

import pytest

from ninanatur.geo.measure import (
    ERODE_M,
    MIN_HEIGHT_M,
    height_of,
    looks_contaminated,
)
from ninanatur.geo.surface import SurfaceWindow

SIDE = 60
CELL = 0.5


def _window(fill: float = 0.0) -> SurfaceWindow:
    return SurfaceWindow(
        min_x=-15.0, min_y=-15.0, cell_m=CELL, cols=SIDE, rows=SIDE,
        heights=[fill] * (SIDE * SIDE),
        source="Test", licence="—", attribution="—",
    )


def _put(window: SurfaceWindow, x0: float, y0: float, x1: float, y1: float,
         height: float) -> SurfaceWindow:
    """Stand something rectangular on the window."""
    values = list(window.heights)
    for row in range(window.rows):
        y = window.min_y + (row + 0.5) * window.cell_m
        for col in range(window.cols):
            x = window.min_x + (col + 0.5) * window.cell_m
            if x0 <= x <= x1 and y0 <= y <= y1:
                values[row * window.cols + col] = height
    return SurfaceWindow(**{**vars(window), "heights": values})


def _square(half: float) -> list[tuple[float, float]]:
    return [(-half, -half), (half, -half), (half, half), (-half, half)]


def test_a_flat_roof_measures_its_own_height() -> None:
    window = _put(_window(), -6.0, -6.0, 6.0, 6.0, 9.0)
    assert height_of(window, _square(6.0)) == pytest.approx(9.0, abs=0.2)


def test_a_pitched_roof_is_measured_nearer_its_ridge_than_its_middle() -> None:
    """The median sits halfway up a pitch, and halfway up is not what casts the
    shadow. The 75th percentile is."""
    window = _window()
    values = list(window.heights)
    for row in range(window.rows):
        y = window.min_y + (row + 0.5) * CELL
        for col in range(window.cols):
            x = window.min_x + (col + 0.5) * CELL
            if -6.0 <= x <= 6.0 and -6.0 <= y <= 6.0:
                # Eaves at 6 m, ridge at 12 m along the middle.
                values[row * window.cols + col] = 12.0 - abs(x)
    window = SurfaceWindow(**{**vars(window), "heights": values})

    measured = height_of(window, _square(6.0))

    assert measured is not None
    assert measured > 9.0, "a median would land here"
    assert measured < 12.0, "and the ridge is not the whole roof either"


def test_a_tree_over_a_corner_does_not_become_the_building() -> None:
    """The failure this module exists for. A 20 m crown over one corner of a
    9 m house must not make it a 20 m house."""
    window = _put(_window(), -6.0, -6.0, 6.0, 6.0, 9.0)
    window = _put(window, 3.0, 3.0, 9.0, 9.0, 20.0)

    measured = height_of(window, _square(6.0))

    assert measured is not None
    assert measured < 12.0, f"the crown took over: {measured} m"


def test_and_it_is_reported_rather_than_silently_corrected() -> None:
    """Knowing something is over the roof is worth more than a corrected number:
    the honest answer is to keep the assumption and say why."""
    clean = _put(_window(), -6.0, -6.0, 6.0, 6.0, 9.0)
    overhung = _put(clean, 2.0, 2.0, 9.0, 9.0, 22.0)

    assert looks_contaminated(clean, _square(6.0)) is False
    assert looks_contaminated(overhung, _square(6.0)) is True


def test_a_footprint_too_small_to_erode_is_not_measured() -> None:
    """A shed is smaller than the overhang it would need protecting from, so it
    gets no answer rather than a bad one."""
    window = _put(_window(), -1.5, -1.5, 1.5, 1.5, 3.0)

    assert height_of(window, _square(1.5)) is None
    assert ERODE_M == 2.0


def test_a_footprint_that_erodes_to_a_handful_of_cells_is_not_measured() -> None:
    """Below a dozen cells the answer swings on which of them a branch touched.

    A 2.1 m half-square erodes to 0.69 m and keeps nine cells; 2.2 m erodes to
    0.79 m and keeps sixteen. The threshold sits between them, which is a garage
    of roughly four metres across — measured rather than reasoned about, because
    the first version of this test guessed 2.6 m and was wrong by a factor of
    two in area."""
    small = _put(_window(), -2.1, -2.1, 2.1, 2.1, 8.0)
    assert height_of(small, _square(2.1)) is None

    just_big_enough = _put(_window(), -2.2, -2.2, 2.2, 2.2, 8.0)
    assert height_of(just_big_enough, _square(2.2)) is not None


def test_something_too_low_to_be_a_building_is_not_one() -> None:
    """A bin store, a porch, the covered bit by the door."""
    window = _put(_window(), -6.0, -6.0, 6.0, 6.0, 1.2)

    assert height_of(window, _square(6.0)) is None
    assert MIN_HEIGHT_M == 2.0


def test_a_footprint_outside_the_window_gets_nothing() -> None:
    window = _put(_window(), -6.0, -6.0, 6.0, 6.0, 9.0)
    far = [(200.0, 200.0), (210.0, 200.0), (210.0, 210.0), (200.0, 210.0)]

    assert height_of(window, far) is None


def test_unsurveyed_ground_under_a_building_gives_nothing_not_zero() -> None:
    """NaN is absence. Averaging it in as zero would halve a real building."""
    window = _window(float("nan"))
    assert height_of(window, _square(6.0)) is None


def test_a_degenerate_outline_is_refused_rather_than_indexed() -> None:
    window = _put(_window(), -6.0, -6.0, 6.0, 6.0, 9.0)
    assert height_of(window, [(0.0, 0.0), (1.0, 1.0)]) is None
