"""What the things in a garden are, and the numbers that come with being one.

A vocabulary that only decorates is a form field asking the user to do our
bookkeeping. Each kind here carries a starting height, so choosing "Hecke"
answers a question instead of asking one.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ninanatur.garden.footprint import Shape


class ObjectKind(StrEnum):
    """The things a gardener points at and names.

    Stored as text, so a renamed member orphans every saved row — the values are
    part of the data, not an implementation detail.
    """

    # Things that stand up and cast a shadow
    HOUSE = "house"
    SHED = "shed"
    WALL = "wall"
    FENCE = "fence"
    HEDGE = "hedge"
    TREE = "tree"
    SHRUB = "shrub"
    # Surfaces: drawn underneath, and they shade nothing
    BED = "bed"
    LAWN = "lawn"
    PAVING = "paving"
    GRAVEL = "gravel"
    POND = "pond"
    PATH = "path"
    # From the map, not from the garden. A ten-metre carriageway and a
    # one-metre slab path are not the same thing to look at, and giving the
    # street its own kind is what lets the plan say which is which.
    STREET = "street"
    OTHER = "other"


# What each kind *is*. A vocabulary that only decorates is a form field asking
# the user to do our bookkeeping; choosing "Hecke" should answer questions
# rather than ask them.
#
# Every kind appears in every table below. A silent fallback in a vocabulary is
# how "other" quietly becomes the default for something nobody meant.


@dataclass(frozen=True)
class KindTraits:
    """Everything the rest of the system needs to know about a kind."""

    shape: Shape
    #: Metres. `depth` is None for a circle, where width is the diameter.
    width: float
    depth: float | None
    #: Starting height. None for surfaces and for "other", which claims nothing.
    height: float | None
    #: Whether it stands up. Paving does not shade a bed, and a model that said
    #: it did would darken every terrace in the country.
    casts_shadow: bool
    #: Drawn underneath everything else — a lawn under a shed, not over it.
    #: Drawing order is a property of the kind, not of the order somebody
    #: happened to click.
    is_surface: bool
    #: What feature 41 draws.
    symbol: str


TRAITS: dict[ObjectKind, KindTraits] = {
    ObjectKind.HOUSE:  KindTraits(Shape.RECT, 10.0, 8.0, 6.0, True, False, "building"),
    ObjectKind.SHED:   KindTraits(Shape.RECT, 3.0, 2.5, 2.4, True, False, "building"),
    ObjectKind.WALL:   KindTraits(Shape.RECT, 6.0, 0.3, 2.0, True, False, "masonry"),
    ObjectKind.FENCE:  KindTraits(Shape.RECT, 6.0, 0.1, 1.2, True, False, "fence"),
    ObjectKind.HEDGE:  KindTraits(Shape.RECT, 6.0, 0.6, 2.0, True, False, "foliage"),
    ObjectKind.TREE:   KindTraits(Shape.CIRCLE, 6.0, None, 8.0, True, False, "crown"),
    ObjectKind.SHRUB:  KindTraits(Shape.CIRCLE, 2.0, None, 1.5, True, False, "crown"),
    ObjectKind.BED:    KindTraits(Shape.RECT, 3.0, 1.5, None, False, True, "planting"),
    ObjectKind.LAWN:   KindTraits(Shape.RECT, 8.0, 6.0, None, False, True, "grass"),
    ObjectKind.PAVING: KindTraits(Shape.RECT, 4.0, 3.0, None, False, True, "slabs"),
    ObjectKind.GRAVEL: KindTraits(Shape.RECT, 3.0, 2.0, None, False, True, "stipple"),
    ObjectKind.POND:   KindTraits(Shape.CIRCLE, 3.0, None, None, False, True, "water"),
    ObjectKind.PATH:   KindTraits(Shape.RECT, 6.0, 1.0, None, False, True, "slabs"),
    ObjectKind.STREET: KindTraits(Shape.RECT, 20.0, 6.0, None, False, True, "tarmac"),
    ObjectKind.OTHER:  KindTraits(Shape.RECT, 2.0, 2.0, None, True, False, "plain"),
}


def traits(kind: ObjectKind) -> KindTraits:
    return TRAITS[kind]


def default_shape(kind: ObjectKind) -> Shape:
    return TRAITS[kind].shape


def default_size(kind: ObjectKind) -> tuple[float, float | None]:
    t = TRAITS[kind]
    return (t.width, t.depth)


def casts_shadow(kind: ObjectKind) -> bool:
    return TRAITS[kind].casts_shadow


def is_surface(kind: ObjectKind) -> bool:
    return TRAITS[kind].is_surface


def symbol_of(kind: ObjectKind) -> str:
    return TRAITS[kind].symbol


def default_height(kind: ObjectKind) -> float | None:
    """Starting value, never a constraint. A user who types 4 m for their hedge
    has a 4 m hedge; the kind picks the number they start from.

    None for a surface and for "other": inventing a height there would put a
    number on screen that the user never gave and cannot see the reason for.
    """
    return TRAITS[kind].height


def default_radius(kind: ObjectKind) -> float | None:
    """Half the default width, for the kinds a circle fits."""
    t = TRAITS[kind]
    return t.width / 2 if t.shape is Shape.CIRCLE else None
