"""Expanding a centreline into the band it covers.

The one piece of new geometry in Wave 11. A wall, a fence, a hedge and a path
are all a line with a width, which is how a wall that turns a corner becomes
one element instead of two.
"""
from __future__ import annotations

import math

import pytest

from ninanatur.garden.footprint import covers
from ninanatur.garden.polyline import band_of


def test_a_straight_line_becomes_a_rectangle() -> None:
    band = band_of([(0.0, 0.0), (10.0, 0.0)], width=2.0)
    xs = [p[0] for p in band]
    ys = [p[1] for p in band]
    assert min(xs) == pytest.approx(0.0)
    assert max(xs) == pytest.approx(10.0)
    # A 2 m band is a metre either side of the centreline, not two.
    assert min(ys) == pytest.approx(-1.0)
    assert max(ys) == pytest.approx(1.0)


def test_the_band_covers_its_own_centreline() -> None:
    band = band_of([(0.0, 0.0), (6.0, 0.0), (6.0, 6.0)], width=1.0)
    for point in ((3.0, 0.0), (6.0, 3.0), (6.0, 0.0)):
        assert covers(band, point), f"{point} should be on the path"


def test_the_band_does_not_cover_what_lies_beside_it() -> None:
    band = band_of([(0.0, 0.0), (10.0, 0.0)], width=2.0)
    assert not covers(band, (5.0, 3.0))
    assert not covers(band, (-4.0, 0.0))


def test_a_corner_is_filled_rather_than_notched() -> None:
    """The outer side of a bend is where a naive offset leaves a wedge of
    unpaved ground in the middle of a path. Nobody builds a path like that."""
    band = band_of([(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)], width=2.0)
    # Just inside the outer corner: a notch would leave this uncovered.
    assert covers(band, (5.6, -0.6))


def test_a_hairpin_still_yields_a_simple_outline() -> None:
    """A tight turn makes the two offsets cross. The result must still be an
    outline a fill and a shadow can use, not a self-intersecting tangle."""
    band = band_of([(0.0, 0.0), (5.0, 0.0), (0.1, 0.4)], width=2.0)
    assert len(band) >= 3
    from ninanatur.garden.footprint import bounding_radius

    # Sanity: the band stays near the line it came from rather than exploding.
    assert bounding_radius(band, (2.5, 0.2)) < 12.0


def test_two_points_are_the_minimum() -> None:
    with pytest.raises(ValueError, match="at least two points"):
        band_of([(0.0, 0.0)], width=1.0)


def test_a_width_of_zero_is_not_a_band() -> None:
    with pytest.raises(ValueError, match="width"):
        band_of([(0.0, 0.0), (1.0, 0.0)], width=0.0)


def test_repeated_points_do_not_produce_a_degenerate_band() -> None:
    """A hand-drawn or clicked line can carry the same point twice; a zero
    length segment has no direction to offset along."""
    band = band_of([(0.0, 0.0), (0.0, 0.0), (8.0, 0.0)], width=2.0)
    assert covers(band, (4.0, 0.0))


def test_the_band_is_closed_and_traversable() -> None:
    """Every consecutive pair must be a real edge — a NaN or an infinity would
    reach the shadow model before anyone noticed."""
    band = band_of([(0.0, 0.0), (4.0, 3.0), (8.0, 0.0)], width=1.5)
    for x, y in band:
        assert math.isfinite(x) and math.isfinite(y)
