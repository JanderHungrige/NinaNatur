"""What the things in a garden are, and the numbers that come with being one.

A vocabulary that only decorates is a form field asking the user to do our
bookkeeping. Each kind here carries a starting height, so choosing "Hecke"
answers a question instead of asking one.
"""
from __future__ import annotations

from enum import StrEnum


class ObjectKind(StrEnum):
    """The things a gardener points at and names.

    Stored as text, so a renamed member orphans every saved row — the values are
    part of the data, not an implementation detail.
    """

    TREE = "tree"
    HEDGE = "hedge"
    SHRUB = "shrub"
    BUILDING = "building"
    WALL = "wall"
    FENCE = "fence"
    OTHER = "other"


# Starting values, never constraints. A user who types 4 m for their hedge has a
# 4 m hedge; the kind picks the number they start from.
#
# OTHER is deliberately absent: "Sonstiges" is the absence of a category, and
# inventing a height for it would put a number on screen that the user never
# gave and cannot see the reason for.
DEFAULT_HEIGHT_M: dict[ObjectKind, float] = {
    ObjectKind.TREE: 8.0,
    ObjectKind.HEDGE: 2.0,
    ObjectKind.SHRUB: 1.5,
    ObjectKind.BUILDING: 6.0,
    ObjectKind.WALL: 2.0,
    ObjectKind.FENCE: 1.2,
}

# Likewise a starting radius: a tree's crown is wider than a fence post.
DEFAULT_RADIUS_M: dict[ObjectKind, float] = {
    ObjectKind.TREE: 3.0,
    ObjectKind.HEDGE: 0.6,
    ObjectKind.SHRUB: 1.0,
    ObjectKind.BUILDING: 4.0,
    ObjectKind.WALL: 0.3,
    ObjectKind.FENCE: 0.2,
}


def default_height(kind: ObjectKind) -> float | None:
    return DEFAULT_HEIGHT_M.get(kind)


def default_radius(kind: ObjectKind) -> float | None:
    return DEFAULT_RADIUS_M.get(kind)
