"""Keeping the trees the surface model proposed, and what became of them.

A suggestion has three fates and all of them have to be remembered. Accepted, it
becomes an obstacle and the suggestion records which. Dismissed, it must not
come back on the next recomputation — the only way to know that is to remember
the refusal. Untouched, it is offered again.

Matched by position rather than by identity, because a suggestion has no
identity: the next surface fetch finds the same tree and computes a fresh centre
a few decimetres away.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ninanatur.garden.elements import now
from ninanatur.geo.canopy import Canopy

#: How far two centres may sit apart and still be the same tree.
#:
#: Three metres. A crown's centroid moves when its edge cells change, and they
#: change with the season the flight was made in and with where the mask fell —
#: so a fresh fetch will not reproduce a centre exactly. Wider than that and two
#: neighbouring trees merge into one refusal.
SAME_TREE_M = 3.0


@dataclass(frozen=True)
class Suggestion:
    """A proposed tree, and whether anybody has answered it."""

    suggestion_id: int
    x: float
    y: float
    radius_m: float
    height_m: float
    dismissed: bool
    accepted_id: int | None


def remember(conn: sqlite3.Connection, garden_id: int, found: list[Canopy]) -> int:
    """Store what was found, without disturbing what was already answered.

    Returns how many are new. A tree already accepted or already dismissed is
    left exactly as it was — re-proposing something somebody rejected is how a
    suggestion becomes a nuisance.
    """
    known = _known(conn, garden_id)
    added = 0
    for canopy in found:
        if any(_same(canopy, seen) for seen in known):
            continue
        conn.execute(
            "INSERT INTO canopy_suggestion (garden_id, x, y, radius_m, height_m,"
            " found_at) VALUES (?, ?, ?, ?, ?, ?)",
            (garden_id, canopy.x, canopy.y, canopy.radius_m, canopy.height_m, now()),
        )
        added += 1
    conn.commit()
    return added


def open_suggestions(conn: sqlite3.Connection, garden_id: int) -> list[Suggestion]:
    """The ones still waiting for an answer, tallest first."""
    rows = conn.execute(
        "SELECT suggestion_id, x, y, radius_m, height_m, dismissed, accepted_id"
        " FROM canopy_suggestion WHERE garden_id = ? AND dismissed = 0"
        " AND accepted_id IS NULL ORDER BY height_m DESC",
        (garden_id,),
    ).fetchall()
    return [
        Suggestion(
            suggestion_id=int(r["suggestion_id"]), x=float(r["x"]), y=float(r["y"]),
            radius_m=float(r["radius_m"]), height_m=float(r["height_m"]),
            dismissed=bool(r["dismissed"]),
            accepted_id=None if r["accepted_id"] is None else int(r["accepted_id"]),
        )
        for r in rows
    ]


def dismiss(conn: sqlite3.Connection, garden_id: int, suggestion_id: int) -> bool:
    """Refuse one. Returns whether there was one to refuse."""
    cursor = conn.execute(
        "UPDATE canopy_suggestion SET dismissed = 1"
        " WHERE suggestion_id = ? AND garden_id = ?",
        (suggestion_id, garden_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def mark_accepted(
    conn: sqlite3.Connection, garden_id: int, suggestion_id: int, element_id: int
) -> None:
    """Record which object a suggestion became."""
    conn.execute(
        "UPDATE canopy_suggestion SET accepted_id = ?"
        " WHERE suggestion_id = ? AND garden_id = ?",
        (element_id, suggestion_id, garden_id),
    )
    conn.commit()


def _known(conn: sqlite3.Connection, garden_id: int) -> list[tuple[float, float]]:
    return [
        (float(r["x"]), float(r["y"]))
        for r in conn.execute(
            "SELECT x, y FROM canopy_suggestion WHERE garden_id = ?", (garden_id,)
        )
    ]


def _same(canopy: Canopy, seen: tuple[float, float]) -> bool:
    return abs(canopy.x - seen[0]) <= SAME_TREE_M and abs(canopy.y - seen[1]) <= SAME_TREE_M


__all__ = [
    "SAME_TREE_M",
    "Suggestion",
    "dismiss",
    "mark_accepted",
    "open_suggestions",
    "remember",
]
