"""Finding trees nobody drew, and refusing to find chimneys.

Windows are built here, because the whole feature is a set of judgements about
what a blob of tall cells is — and a real window contains every case at once,
which is no way to test any of them.
"""
from __future__ import annotations

import pytest

from ninanatur.geo.canopy import (
    BUILDING_MARGIN_M,
    MAX_AREA_M2,
    MIN_HEIGHT_M,
    SLENDER_RATIO,
    canopies_in,
)
from ninanatur.geo.surface import SurfaceWindow

SIDE = 200
CELL = 0.5


def _window() -> SurfaceWindow:
    return SurfaceWindow(
        min_x=-50.0, min_y=-50.0, cell_m=CELL, cols=SIDE, rows=SIDE,
        heights=[0.0] * (SIDE * SIDE), source="T", licence="—", attribution="—",
    )


def _blob(window: SurfaceWindow, cx: float, cy: float, radius: float,
          height: float) -> SurfaceWindow:
    values = list(window.heights)
    for row in range(window.rows):
        y = window.min_y + (row + 0.5) * CELL
        for col in range(window.cols):
            x = window.min_x + (col + 0.5) * CELL
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius:
                values[row * window.cols + col] = height
    return SurfaceWindow(**{**vars(window), "heights": values})


def _square(cx: float, cy: float, half: float) -> list[tuple[float, float]]:
    return [(cx - half, cy - half), (cx + half, cy - half),
            (cx + half, cy + half), (cx - half, cy + half)]


def test_a_tree_is_found_with_its_height_and_its_spread() -> None:
    [tree] = canopies_in(_blob(_window(), 10.0, 10.0, 4.0, 18.0), [])

    assert tree.x == pytest.approx(10.0, abs=0.5)
    assert tree.y == pytest.approx(10.0, abs=0.5)
    assert tree.height_m == pytest.approx(18.0)
    assert tree.radius_m == pytest.approx(4.0, abs=0.3)


def test_a_hedge_is_not_a_tree() -> None:
    """Below three metres it is a hedge, a car, a shed or a washing line — and
    it shades almost nothing at the sun angles this model counts."""
    assert canopies_in(_blob(_window(), 10.0, 10.0, 4.0, 2.0), []) == []
    assert MIN_HEIGHT_M == 3.0


def test_a_chimney_is_not_a_tree() -> None:
    """Twenty metres tall and a metre across. Measured in Cologne, where exactly
    these appeared: a mast, a chimney, or the corner of a building the mask did
    not cover."""
    tall_and_thin = _blob(_window(), 10.0, 10.0, 1.4, 20.0)

    assert canopies_in(tall_and_thin, []) == []
    assert SLENDER_RATIO == 8.0


def test_a_building_does_not_become_a_tree() -> None:
    window = _blob(_window(), 10.0, 10.0, 5.0, 9.0)

    assert canopies_in(window, []) != [], "without the footprint it is a tree"
    assert canopies_in(window, [_square(10.0, 10.0, 5.0)]) == []


def test_and_neither_does_the_edge_of_one() -> None:
    """A roof and the tree beside it touch in a surface model. Without a margin
    every building grows a small tree along its northern edge."""
    window = _blob(_window(), 10.0, 10.0, 5.0, 9.0)
    exactly = _square(10.0, 10.0, 4.6)          # a shade smaller than the blob

    assert canopies_in(window, [exactly]) == []
    assert BUILDING_MARGIN_M == 2.0


def test_a_wood_is_not_a_tree() -> None:
    """Beyond three hundred square metres it is a row, a copse or a building —
    and one trunk position for a fifty-metre blob would be a fiction."""
    assert canopies_in(_blob(_window(), 0.0, 0.0, 12.0, 15.0), []) == []
    assert MAX_AREA_M2 == 300.0


def test_only_the_trees_that_can_reach_the_garden_are_offered() -> None:
    """A leafy suburb yields 46 crowns in a 200 m window, and confirming 46
    suggestions one at a time is not a feature."""
    window = _blob(_blob(_window(), 5.0, 5.0, 4.0, 20.0), 45.0, 45.0, 4.0, 22.0)

    near = canopies_in(window, [], within_m=20.0)

    assert len(near) == 1
    assert near[0].x == pytest.approx(5.0, abs=0.5)


def test_the_tallest_comes_first() -> None:
    """The order somebody wants to answer them in: the tree that matters most is
    the one that shades most."""
    window = _blob(_blob(_window(), -10.0, 0.0, 4.0, 8.0), 10.0, 0.0, 4.0, 20.0)

    found = canopies_in(window, [])

    assert [c.height_m for c in found] == sorted(
        [c.height_m for c in found], reverse=True
    )
    assert found[0].height_m == pytest.approx(20.0)


def test_two_crowns_touching_at_a_corner_are_two_trees() -> None:
    """Four-connected, not eight. Joining them would put one trunk between
    them, which is where neither tree is."""
    window = _blob(_blob(_window(), -3.0, -3.0, 2.5, 12.0), 3.0, 3.0, 2.5, 14.0)

    assert len(canopies_in(window, [])) == 2


def test_unsurveyed_ground_grows_nothing() -> None:
    window = _window()
    window = SurfaceWindow(**{**vars(window), "heights": [float("nan")] * (SIDE * SIDE)})

    assert canopies_in(window, []) == []
