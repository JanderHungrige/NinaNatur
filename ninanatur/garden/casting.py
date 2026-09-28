"""What a drawn thing puts between a point and the sun — one rule for all.

The light model (`lightview.shading_obstacles`) and the day's playback
(`solar.day`) both cast the garden's elements, and until 2026-09-28 each did
it its own way: the playback kept a copy of the old rule after the model had
learnt to cast a roof as a roof (doc 120), and the page drew a block where the
map counted planes. Here once, so there is nothing left to drift.

A tree or a shrub the gardener drew, or took from the laser, casts as a crown
on a trunk (doc 121) — it was an opaque block to its top, a wall, though the
canopy model had said since Wave 9 that a tree is not one.
"""
from __future__ import annotations

import math

from ninanatur.garden.canopies import FIRST_LEAF_MONTH, transmission
from ninanatur.garden.canopy import crown_base
from ninanatur.garden.footprint import covers
from ninanatur.garden.models import Element
from ninanatur.garden.objects import ObjectKind, casts_shadow
from ninanatur.garden.roofs import Roof, shading_height
from ninanatur.garden.roofshape import surface_of
from ninanatur.solar.crown import Crown
from ninanatur.solar.shading import Obstacle
from ninanatur.solar.sweep import RoofSolid

#: The roofs the model knows the shape of, given a pitch it can place: they
#: cast as planes, or — too shallow to pitch — as the plane their cells stand
#: on, at the ridge. A pent without a surveyed fall is not among them.
_SHAPED = (Roof.GABLE, Roof.HIP)

#: What a gardener draws that is a crown on a trunk (doc 121). A hedge is not:
#: it is leaves to the ground, and stays a solid prism.
_CROWNS = frozenset({ObjectKind.TREE, ObjectKind.SHRUB})

#: How far an outline's rim may reach beyond the circle of its area and still
#: be one crown (doc 121): a square's corners reach 1.25 times as far, a 2:1
#: oblong's 1.40, a 3:1 one's 1.62.
ROUND_ENOUGH = 1.5


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
    if ObjectKind(element.kind) in _CROWNS:
        return _crown(element)
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


def _crown(element: Element) -> Obstacle:
    """A drawn tree or shrub as the crown it is (doc 121).

    Its species is nobody's guess, so it takes a broadleaf's shares, as the
    canopy model does for a planting whose leaves the catalogue does not know.
    Its base is the gardener's or the laser's, else the assumption
    (`canopy.crown_base`), which is kept inside its height. An outline no
    crown fits — a row, a band, an L — casts as itself, passing a crown's
    share whenever a ray meets it: the rule planted crowns had until now,
    rather than a disc standing where nothing was drawn (review, 2026-09-28).
    """
    height = element.height or 0.0
    leaf, bare = transmission(None, FIRST_LEAF_MONTH), transmission(None, 1)
    disc = crown_disc(element)
    if disc is None:
        return Obstacle(footprint=element.footprint, height=height, transmission=leaf,
                        bare_transmission=bare, owner=element.element_id)
    x, y, radius = disc
    base = element.crown_base_m
    if base is None:
        base = crown_base(height, element.kind)
    return Obstacle(
        footprint=element.footprint, height=height, transmission=leaf, bare_transmission=bare,
        crown=Crown(x=x, y=y, radius=radius, base=min(max(base, 0.0), height), top=height),
        owner=element.element_id,
    )


def crown_fits(element: Element) -> bool:
    """Whether one crown fits what was drawn: a tree or shrub on it casts as a
    crown on a trunk, whose base counts, where otherwise it casts as the solid
    a row is and a crown base changes nothing. Said of every outline, not only
    a tree's, so a form that turns a hedge into a tree knows it too (review
    of 45eb56a)."""
    return crown_disc(element) is not None


def crown_disc(element: Element) -> tuple[float, float, float] | None:
    """Where a drawn crown stands and how far it reaches, or None where no
    crown fits what was drawn.

    A circle says so. Any other outline gives its centroid and the radius of
    a circle of its area, so the crown holds as many leaves as the shape drawn
    — when the outline is round enough to be one crown: its centroid inside
    it, and no corner further out than `ROUND_ENOUGH` of that radius. A line
    is a row, never one crown.
    """
    if element.shape == "circle" and element.width is not None:
        return element.x, element.y, element.width / 2
    if element.shape == "line":
        return None
    ring = element.footprint
    twice = cx = cy = 0.0
    for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1], strict=True):
        cross = ax * by - bx * ay
        twice += cross
        cx += (ax + bx) * cross
        cy += (ay + by) * cross
    if abs(twice) < 1e-9:
        return None
    cx, cy = cx / (3 * twice), cy / (3 * twice)
    radius = math.sqrt(abs(twice) / 2 / math.pi)
    reach = max(math.hypot(px - cx, py - cy) for px, py in ring)
    if not covers(ring, (cx, cy)) or reach > ROUND_ENOUGH * radius:
        return None
    return cx, cy, radius


__all__ = ["ROUND_ENOUGH", "casting", "casts", "crown_disc"]
