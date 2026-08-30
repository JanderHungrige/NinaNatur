"""What is growing where.

Split out of `store.py` in Wave 11. A planting is the one thing on a plan that
is not geometry, and keeping it beside the element CRUD made `store.py` the
file everything landed in.
"""
from __future__ import annotations

import sqlite3

from ninanatur.garden.canopy import shades
from ninanatur.garden.elements import now as _now
from ninanatur.garden.lighting import _relight_if_woody, _woody_heights, recompute_light
from ninanatur.garden.models import Planting


class UnknownTaxon(ValueError):
    """A planting pointing at a species that is not in the catalogue.

    Rejected rather than stored: a dangling reference would leave the bloom
    timeline silently short a species instead of failing where it can be seen.
    """


def add_planting(
    conn: sqlite3.Connection,
    bed_id: int,
    taxon_id: int | None = None,
    quantity: int = 1,
    raw_name: str | None = None,
) -> int:
    """Put a plant in a bed, named or not.

    `taxon_id` identifies it against the catalogue; `raw_name` is what the user
    typed. A planting with only a raw name is one the catalogue could not name —
    an ordinary answer, since it holds 8,939 German species and no cultivars at
    all. Refusing it would tell someone their garden is wrong because our data
    is incomplete.
    """
    if quantity < 1:
        # Zero would be a deletion expressed as an update, and the two would then
        # disagree about whether the species is in the bed at all.
        raise ValueError(f"quantity must be at least 1, got {quantity}")
    if taxon_id is None and not (raw_name or "").strip():
        raise ValueError("a planting needs either a taxon or a name")

    if taxon_id is not None:
        known = conn.execute(
            "SELECT 1 FROM taxon WHERE taxon_id = ?", (taxon_id,)
        ).fetchone()
        if known is None:
            raise UnknownTaxon(f"no such taxon in the catalogue: {taxon_id}")

    if taxon_id is None:
        # No conflict target: NULLs are distinct, so two unidentified roses are
        # two rows, which is what should happen.
        cursor = conn.execute(
            "INSERT INTO planting (element_id, taxon_id, raw_name, quantity, added_at)"
            " VALUES (?, NULL, ?, ?, ?)",
            (bed_id, raw_name, quantity, _now()),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)

    conn.execute(
        """
        INSERT INTO planting (element_id, taxon_id, raw_name, quantity, added_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (element_id, taxon_id) DO UPDATE SET
            quantity = planting.quantity + excluded.quantity,
            -- Never overwrite the words the user typed with nothing.
            raw_name = COALESCE(excluded.raw_name, planting.raw_name)
        """,
        (bed_id, taxon_id, raw_name, quantity, _now()),
    )
    conn.commit()
    _relight_if_woody(conn, bed_id, taxon_id)
    row = conn.execute(
        "SELECT planting_id FROM planting WHERE element_id = ? AND taxon_id = ?",
        (bed_id, taxon_id),
    ).fetchone()
    return int(row["planting_id"])


def remove_planting(conn: sqlite3.Connection, planting_id: int) -> None:
    # Read the bed before the row is gone: removing a tree gives the light back,
    # and afterwards there is nothing left to say which garden to recompute.
    row = conn.execute(
        "SELECT p.element_id, p.taxon_id, e.garden_id FROM planting p"
        " JOIN element e ON e.element_id = p.element_id WHERE p.planting_id = ?",
        (planting_id,),
    ).fetchone()
    conn.execute("DELETE FROM planting WHERE planting_id = ?", (planting_id,))
    conn.commit()
    if row is None:
        return
    canopy = _woody_heights(conn, [int(row["taxon_id"])]).get(int(row["taxon_id"]))
    if shades(canopy):
        recompute_light(conn, int(row["garden_id"]))


def _plantings_for(conn: sqlite3.Connection, bed_id: int) -> list[Planting]:
    return [
        Planting(
            planting_id=int(r["planting_id"]),
            taxon_id=None if r["taxon_id"] is None else int(r["taxon_id"]),
            canonical_name=r["canonical_name"],
            quantity=int(r["quantity"]),
            added_at=r["added_at"],
            raw_name=r["raw_name"],
        )
        for r in conn.execute(
            """
            -- LEFT, not INNER: an inner join drops exactly the rows this
            -- feature exists to keep — the plants the catalogue cannot name.
            SELECT p.planting_id, p.taxon_id, p.quantity, p.added_at, p.raw_name,
                   x.canonical_name
            FROM planting p LEFT JOIN taxon x ON x.taxon_id = p.taxon_id
            WHERE p.element_id = ? ORDER BY COALESCE(x.canonical_name, p.raw_name)
            """,
            (bed_id,),
        )
    ]
