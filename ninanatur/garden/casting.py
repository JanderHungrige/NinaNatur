"""What a drawn thing puts between a point and the sun — one rule for all.

The light model (`lightview.shading_obstacles`) and the day's playback
(`solar.day`) both cast the garden's elements, and until 2026-09-28 each did
it its own way: the playback kept a copy of the old rule after the model had
learnt to cast a roof as a roof (doc 120), and the page drew a block where the
map counted planes. Here once, so there is nothing left to drift.
"""
from __future__ import annotations

from ninanatur.garden.models import Element
from ninanatur.garden.objects import ObjectKind, casts_shadow
from ninanatur.garden.roofs import Roof, shading_height
from ninanatur.garden.roofshape import surface_of
from ninanatur.solar.shading import Obstacle
from ninanatur.solar.sweep import RoofSolid

#: The roofs the model knows the shape of, given a pitch it can place: they
#: cast as planes, or — too shallow to pitch — as the plane their cells stand
#: on, at the ridge. A pent without a surveyed fall is not among them.
_SHAPED = (Roof.GABLE, Roof.HIP)


def casts(element: Element) -> bool:
    """Whether this element throws a shadow at all. A height of None is an
    element nobody has said the height of, and treating it as zero would be
    a claim; skipping it is the answer Wave 8 gave."""
    return element.height is not None and casts_shadow(ObjectKind(element.kind))


def casting(element: Element) -> Obstacle:
    """What this drawn thing casts (doc 120).

    A roof whose planes the model knows casts as those planes, to its full
    ridge: the roof the sun is asked about on top of the building is the roof
    that shades the garden beside it. One the model would pitch but that is
    too shallow to (under `roofshape.MIN_PITCH_DEG`) casts at the height its
    cells stand on, the ridge. A shape nobody has identified — mixed, other,
    unknown, a pent whose fall nobody surveyed — keeps `shading_height`'s
    guess and casts as a block.
    """
    height = element.height or 0.0
    roof = Roof(element.roof)
    surface = surface_of(element.footprint, roof, height, element.eaves_m,
                         element.roof_fall_deg)
    solid = None if surface is None or not surface.pitched else RoofSolid(
        planes=surface.planes(), ridge=surface.ridge, eaves=surface.eaves_m)
    shaped = roof in _SHAPED or (roof is Roof.PENT and element.roof_fall_deg is not None)
    return Obstacle(
        footprint=element.footprint,
        # The ridge is a line, not a wall. Without a shape this is the guess.
        height=height if solid or shaped else shading_height(height, roof, element.eaves_m),
        roof=solid,
        # So a point on this building's own roof can leave it out.
        owner=element.element_id,
    )


__all__ = ["casting", "casts"]
