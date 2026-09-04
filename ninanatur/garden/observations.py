"""Flower colours entered by hand, in the shared catalogue.

Flower colour is recorded for 590 of 8,939 species. Since the info panel shows a
photograph, somebody standing in front of their own bed can often say what the
catalogue cannot — and for a cultivar they are the better witness anyway.

**These go into `trait`, marked `manual`.** That is a change of mind, asked for
by the gardener and worth stating plainly, because the first version deliberately
did the opposite:

- It is **everyone's**. One person's entry answers for every garden on this
  server. That is the point of putting it in the general database; it is also
  the cost, and two people who disagree overwrite each other.
- It **survives a deployment**. The shipped catalogue is re-synced whenever the
  build stamps differ, with `INSERT OR REPLACE` — which matches on the primary
  key, and that key includes `source`. A `manual` row has no counterpart in the
  image, so nothing replaces it. `test_a_deployment_does_not_wipe_it` asserts
  this against a real sync rather than trusting the reasoning.
- It **loses to an official source**, which is the rule as given: a hand entry
  fills a gap until real data arrives. `MANUAL_SOURCE` ranks behind every other
  source, including ones nobody has added yet. It is not deleted when it loses —
  sources never overwrite each other here, and the disagreement stays visible.
"""
from __future__ import annotations

import sqlite3

from ninanatur.data.traits import MANUAL_SOURCE
from ninanatur.ingest.provenance import upsert_trait

#: The colours the plan can draw. A free string would reach the canvas as a dot
#: with no colour, which is worse than drawing it grey for "not recorded".
DRAWABLE = frozenset(
    {
        "yellow", "white", "pink", "violet", "blue",
        "red", "green", "orange", "brown", "black",
    }
)

#: Not an open-data licence, and it must not pretend to be one. Nobody asked the
#: gardener to license their observation, so an export that has to respect
#: licences can filter on exactly this string.
MANUAL_LICENCE = "user-contributed"

#: One person looking at one plant. Lower than any published dataset, and said
#: rather than implied — the number is what a UI can show beside the value.
MANUAL_CONFIDENCE = 0.4

TRAIT_KEY = "flower_colour"


def record_colour(
    conn: sqlite3.Connection, *, taxon_id: int, colour: str | None
) -> None:
    """Record the colour this species flowers in. `None` takes the entry back.

    Taking it back removes only the hand-entered row. It used to be the only row
    for a species with no recorded colour; once an official source has one, it is
    not.
    """
    if colour is None:
        conn.execute(
            "DELETE FROM trait WHERE taxon_id = ? AND trait_key = ? AND source = ?",
            (taxon_id, TRAIT_KEY, MANUAL_SOURCE),
        )
        conn.commit()
        return

    if colour not in DRAWABLE:
        raise ValueError(
            f"not a colour the plan can draw: {colour!r}; expected one of {sorted(DRAWABLE)}"
        )

    # Through the one write path, which raises without provenance. A hand entry
    # is held to the same rule as GIFT and EIVE: it says where it came from.
    upsert_trait(
        conn,
        taxon_id,
        TRAIT_KEY,
        source=MANUAL_SOURCE,
        license=MANUAL_LICENCE,
        value_text=colour,
        confidence=MANUAL_CONFIDENCE,
    )
    # `upsert_trait` deliberately does not commit: the ingest pipeline writes
    # thousands of rows and commits once at the end. This is the first caller
    # that is one request rather than a batch, so the commit belongs here — and
    # without it the write is visible to the very request that made it and to
    # nothing afterwards, which is exactly how it behaved in production.
    conn.commit()


def manual_colours(conn: sqlite3.Connection) -> dict[int, str]:
    """Every hand-entered colour, by taxon.

    What the form needs to show which species already carry one — including the
    ones an official source has since overruled, because "you entered violet and
    the catalogue now says blue" is the honest thing to show somebody.
    """
    rows = conn.execute(
        "SELECT taxon_id, value_text FROM trait"
        " WHERE trait_key = ? AND source = ? AND value_text IS NOT NULL",
        (TRAIT_KEY, MANUAL_SOURCE),
    ).fetchall()
    return {int(r["taxon_id"]): str(r["value_text"]) for r in rows}
