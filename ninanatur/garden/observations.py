"""What the gardener saw, as opposed to what the catalogue says.

Flower colour is recorded for 590 of 8,939 species. Since the info panel shows
a photograph, somebody standing in front of their own bed can often say what
the catalogue cannot — and for a cultivar they are the better witness anyway.

**This never touches the catalogue.** That ships inside the image and is
re-synced at startup whenever the build stamps differ, so a row written into
`trait` would be overwritten by the next deployment — and until it was, it would
change the suggestions of every other garden on this server. An observation
belongs to the garden that made it and lives on the volume with the rest of the
user's data.
"""
from __future__ import annotations

import sqlite3

from ninanatur.garden.elements import now

#: The colours the plan can draw. A free string would reach the canvas as a dot
#: with no colour, which is worse than the honest hatch for "not recorded".
DRAWABLE = frozenset(
    {
        "yellow", "white", "pink", "violet", "blue",
        "red", "green", "orange", "brown", "black",
    }
)


def record_colour(
    conn: sqlite3.Connection, garden_id: int, *, taxon_id: int, colour: str | None
) -> None:
    """Note the colour this species flowers in, here. `None` takes it back.

    Taking it back returns the catalogue's answer — its silence included. A
    gardener who guessed wrong should get the hatch back rather than a colour
    they no longer believe.
    """
    if colour is None:
        conn.execute(
            "DELETE FROM observed_colour WHERE garden_id = ? AND taxon_id = ?",
            (garden_id, taxon_id),
        )
        conn.commit()
        return

    if colour not in DRAWABLE:
        raise ValueError(
            f"not a colour the plan can draw: {colour!r};"
            f" expected one of {sorted(DRAWABLE)}"
        )
    conn.execute(
        "INSERT INTO observed_colour (garden_id, taxon_id, colour, noted_at)"
        " VALUES (?, ?, ?, ?)"
        " ON CONFLICT (garden_id, taxon_id) DO UPDATE SET"
        "   colour = excluded.colour, noted_at = excluded.noted_at",
        (garden_id, taxon_id, colour, now()),
    )
    conn.commit()


def observed_colours(conn: sqlite3.Connection, garden_id: int) -> dict[int, str]:
    """Every colour this garden has recorded, by taxon."""
    return {
        int(row["taxon_id"]): str(row["colour"])
        for row in conn.execute(
            "SELECT taxon_id, colour FROM observed_colour WHERE garden_id = ?",
            (garden_id,),
        )
    }
