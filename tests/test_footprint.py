"""The ground an object covers.

One function, because the data-flow analysis found occlusion already computed
twice — agreeing only because both sides assumed a cylinder. Three answers to
"what ground does this cover" is how they drift.
"""
import math

import pytest

from ninanatur.garden.footprint import (
    Shape,
    bounding_radius,
    covers,
    footprint_of,
)


def _rect(**kw: object) -> dict[str, object]:
    base = {"shape": Shape.RECT, "x": 0.0, "y": 0.0, "width": 10.0,
            "depth": 8.0, "rotation": 0.0, "points": None}
    return {**base, **kw}


# --- rectangles ------------------------------------------------------------

def test_a_rectangle_has_four_corners_around_its_centre() -> None:
    poly = footprint_of(**_rect())  # type: ignore[arg-type]
    assert len(poly) == 4
    xs = sorted(p[0] for p in poly)
    ys = sorted(p[1] for p in poly)
    assert xs[0] == pytest.approx(-5.0)
    assert xs[-1] == pytest.approx(5.0)
    assert ys[0] == pytest.approx(-4.0)
    assert ys[-1] == pytest.approx(4.0)


def test_rotating_a_square_by_ninety_degrees_gives_the_same_square() -> None:
    # Compared as rounded sets: cos(90°) is 6e-17 rather than 0, so sorting the
    # raw corners can put two nearly-equal x values in either order, and the
    # test would then compare corner 1 against corner 2.
    def corners(**kw: object) -> set[tuple[float, float]]:
        return {(round(px, 9) + 0.0, round(py, 9) + 0.0)
                for px, py in footprint_of(**kw)}  # type: ignore[arg-type]

    assert corners(**_rect(width=4.0, depth=4.0)) == corners(
        **_rect(width=4.0, depth=4.0, rotation=90.0)
    )


def test_rotation_is_clockwise_from_north() -> None:
    """The compass convention the solar model already uses. A second angular
    convention in one drawing is a bug waiting for its first rotated house."""
    # A long thin rectangle pointing north, turned 90°, points east.
    poly = footprint_of(**_rect(width=1.0, depth=10.0, rotation=90.0))  # type: ignore[arg-type]
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    assert max(xs) - min(xs) == pytest.approx(10.0)
    assert max(ys) - min(ys) == pytest.approx(1.0)


def test_a_rectangle_is_moved_by_its_position() -> None:
    poly = footprint_of(**_rect(x=3.0, y=-2.0))  # type: ignore[arg-type]
    assert sum(p[0] for p in poly) / 4 == pytest.approx(3.0)
    assert sum(p[1] for p in poly) / 4 == pytest.approx(-2.0)


# --- circles ---------------------------------------------------------------

def test_a_circle_becomes_a_polygon_that_is_round_enough() -> None:
    poly = footprint_of(shape=Shape.CIRCLE, x=0.0, y=0.0, width=6.0,
                        depth=None, rotation=0.0, points=None)
    radii = [math.hypot(px, py) for px, py in poly]
    assert all(r == pytest.approx(3.0, rel=0.02) for r in radii)
    # Enough segments that a shadow of it does not look like a stop sign.
    assert len(poly) >= 12


def test_a_circle_ignores_rotation() -> None:
    a = footprint_of(shape=Shape.CIRCLE, x=0.0, y=0.0, width=4.0, depth=None,
                     rotation=0.0, points=None)
    b = footprint_of(shape=Shape.CIRCLE, x=0.0, y=0.0, width=4.0, depth=None,
                     rotation=37.0, points=None)
    assert bounding_radius(a) == pytest.approx(bounding_radius(b))


# --- polygons --------------------------------------------------------------

def test_a_drawn_polygon_keeps_its_points() -> None:
    points = [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0]]
    poly = footprint_of(shape=Shape.POLYGON, x=1.0, y=1.0, width=None,
                        depth=None, rotation=0.0, points=points)
    assert poly == [(1.0, 1.0), (5.0, 1.0), (5.0, 4.0)]


def test_a_polygon_with_too_few_points_is_refused() -> None:
    with pytest.raises(ValueError):
        footprint_of(shape=Shape.POLYGON, x=0.0, y=0.0, width=None, depth=None,
                     rotation=0.0, points=[[0.0, 0.0], [1.0, 1.0]])


# --- covers ----------------------------------------------------------------

def test_a_point_inside_a_rectangle_is_covered() -> None:
    poly = footprint_of(**_rect())  # type: ignore[arg-type]
    assert covers(poly, (0.0, 0.0)) is True
    assert covers(poly, (4.9, 3.9)) is True


def test_a_point_outside_is_not() -> None:
    poly = footprint_of(**_rect())  # type: ignore[arg-type]
    assert covers(poly, (5.1, 0.0)) is False
    assert covers(poly, (0.0, 4.1)) is False


def test_a_point_on_the_edge_counts_as_covered() -> None:
    # A bed exactly against a wall is touching it, not floating beside it.
    poly = footprint_of(**_rect())  # type: ignore[arg-type]
    assert covers(poly, (5.0, 0.0)) is True


def test_covering_a_rotated_rectangle_follows_the_rotation() -> None:
    poly = footprint_of(**_rect(width=10.0, depth=2.0, rotation=90.0))  # type: ignore[arg-type]
    assert covers(poly, (0.0, 4.0)) is True   # now long north-south
    assert covers(poly, (4.0, 0.0)) is False


def test_the_bounding_radius_contains_the_whole_shape() -> None:
    poly = footprint_of(**_rect())  # type: ignore[arg-type]
    r = bounding_radius(poly)
    assert all(math.hypot(px, py) <= r + 1e-9 for px, py in poly)
    assert r == pytest.approx(math.hypot(5.0, 4.0))


class TestLineShape:
    """A line is a centreline and a band width (Wave 11).

    The point of putting it here rather than beside the band arithmetic: what
    matters to the rest of the system is that a line answers the same question
    every other shape answers — what ground does this cover.
    """

    def test_a_line_covers_the_band_around_its_centreline(self) -> None:
        band = footprint_of(
            shape=Shape.LINE,
            x=10.0,
            y=5.0,
            width=2.0,
            depth=None,
            rotation=0.0,
            points=[[0.0, 0.0], [6.0, 0.0]],
        )
        # Points are relative to (x, y), like every other shape's.
        assert covers(band, (13.0, 5.0))
        assert covers(band, (13.0, 5.9))
        assert not covers(band, (13.0, 7.0))

    def test_a_bent_line_is_one_element(self) -> None:
        """A wall that turns a corner was two obstacles before this."""
        band = footprint_of(
            shape=Shape.LINE,
            x=0.0,
            y=0.0,
            width=1.0,
            depth=None,
            rotation=0.0,
            points=[[0.0, 0.0], [5.0, 0.0], [5.0, 5.0]],
        )
        assert covers(band, (2.0, 0.0))
        assert covers(band, (5.0, 3.0))

    def test_a_line_needs_its_centreline(self) -> None:
        with pytest.raises(ValueError, match="centreline"):
            footprint_of(
                shape=Shape.LINE, x=0.0, y=0.0, width=1.0,
                depth=None, rotation=0.0, points=None,
            )

    def test_a_line_needs_a_width(self) -> None:
        with pytest.raises(ValueError, match="width"):
            footprint_of(
                shape=Shape.LINE, x=0.0, y=0.0, width=None,
                depth=None, rotation=0.0, points=[[0.0, 0.0], [3.0, 0.0]],
            )
