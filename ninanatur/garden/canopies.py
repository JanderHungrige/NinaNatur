"""How much light a crown lets through, and when.

A tree was modelled as a wall. It is not one: a broadleaf crown in full leaf
passes some light, a spruce passes almost none, and — the part that matters most
— **a deciduous tree is bare in March**. The light season starts on 1 March, and
until now the model shaded a garden under a leafless oak exactly as hard as
under masonry, in the two months when somebody is deciding what to plant.

The leaf state comes from GIFT trait 2.4.1, ingested as `deciduousness`. It
covers 452 of 954 German woody species — 47 %, measured before this was planned.
Where it is missing the crown is treated as a broadleaf in leaf, which is what
most of a German garden's trees are; the alternative was to keep calling them
walls.
"""
from __future__ import annotations

import sqlite3

from ninanatur.data.traits import resolve_trait

#: Fraction of direct sun a crown lets through.
#:
#: Rules of thumb rather than measurements, and here rather than inline so that
#: somebody who disagrees has one place to argue. A dense conifer transmits a
#: few per cent; a broadleaf canopy in leaf rather more; bare winter branches
#: take perhaps a quarter of the light and are nowhere near a wall.
TRANSMISSION_EVERGREEN = 0.08
TRANSMISSION_IN_LEAF = 0.20
TRANSMISSION_BARE = 0.75

#: When a German broadleaf is in leaf. Leaf-out runs through April and leaf-fall
#: through late October, and both vary by species and by year — so this is an
#: assumption, stated as one, in the same way assumed building heights are.
FIRST_LEAF_MONTH = 5
LAST_LEAF_MONTH = 10


def transmission(deciduousness: str | None, month: int) -> float:
    """What fraction of the sun this crown passes in this month.

    `variable` is a third answer GIFT actually gives — 6 of the German woody
    species — and it is neither of the other two. It is treated as evergreen
    for shade, because a plant that keeps some of its leaves keeps some of its
    shade, and pretending otherwise would make a garden brighter than it is.
    """
    if deciduousness == "evergreen" or deciduousness == "variable":
        return TRANSMISSION_EVERGREEN
    if FIRST_LEAF_MONTH <= month <= LAST_LEAF_MONTH:
        return TRANSMISSION_IN_LEAF
    return TRANSMISSION_BARE


def deciduousness_of(conn: sqlite3.Connection, taxon_id: int) -> str | None:
    """What the catalogue says about this species' leaves, or nothing."""
    trait = resolve_trait(conn, taxon_id, "deciduousness")
    if trait is None or trait.value_text is None:
        return None
    return str(trait.value_text).strip().lower()
