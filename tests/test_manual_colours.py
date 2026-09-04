"""A colour entered by hand goes into the shared catalogue, marked as such.

The earlier design kept these per garden, on the volume, deliberately out of
`trait`. The gardener asked for the opposite: one general database, the entry
marked manual, and an official source allowed to override it.

Two facts make that safe, and both are asserted here rather than assumed. The
`trait` primary key includes `source`, so a manual row has no counterpart in the
shipped catalogue and `INSERT OR REPLACE` during a sync cannot touch it. And
`_rank` puts `manual` behind every other source, present or future, so the day
GIFT records a colour it simply wins.
"""
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from ninanatur.data.traits import MANUAL_SOURCE, resolve_trait
from ninanatur.garden.observations import DRAWABLE, manual_colours, record_colour
from ninanatur.ingest.catalogue import sync_catalogue
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(connection)
    for taxon_id, name in ((1, "Salvia pratensis"), (2, "Achillea millefolium")):
        connection.execute(
            "INSERT INTO taxon (taxon_id, canonical_name) VALUES (?, ?)", (taxon_id, name)
        )
    connection.commit()
    yield connection


def test_a_hand_entry_lands_in_the_catalogue(conn: sqlite3.Connection) -> None:
    record_colour(conn, taxon_id=1, colour="violet")

    row = conn.execute(
        "SELECT value_text, source, license, confidence FROM trait"
        " WHERE taxon_id = 1 AND trait_key = 'flower_colour'"
    ).fetchone()

    assert row["value_text"] == "violet"
    assert row["source"] == MANUAL_SOURCE


def test_it_says_where_it_came_from(conn: sqlite3.Connection) -> None:
    """Every trait value in this database carries provenance, and a hand entry
    is no exception. The licence is *not* an open-data one — nobody asked the
    gardener to licence their observation — and saying so is what lets an export
    leave it out."""
    record_colour(conn, taxon_id=1, colour="violet")

    row = conn.execute(
        "SELECT source, license, confidence, retrieved_at FROM trait WHERE taxon_id = 1"
    ).fetchone()

    assert row["source"] == "manual"
    assert row["license"] == "user-contributed"
    assert row["retrieved_at"] is not None
    assert row["confidence"] is not None and row["confidence"] < 0.5


def test_an_official_source_wins(conn: sqlite3.Connection) -> None:
    """The rule the gardener asked for. A hand entry fills a gap until real data
    arrives, and then gets out of the way."""
    record_colour(conn, taxon_id=1, colour="violet")
    upsert_trait(
        conn, 1, "flower_colour", source="GIFT", license="CC-BY-4.0", value_text="blue"
    )

    resolved = resolve_trait(conn, 1, "flower_colour")

    assert resolved is not None
    assert resolved.value_text == "blue"
    assert resolved.source == "GIFT"


def test_the_hand_entry_is_still_there_underneath(conn: sqlite3.Connection) -> None:
    """Overridden, not deleted. Sources never overwrite each other in this
    database — disagreement stays visible, which is the whole reason the primary
    key includes the source."""
    record_colour(conn, taxon_id=1, colour="violet")
    upsert_trait(
        conn, 1, "flower_colour", source="GIFT", license="CC-BY-4.0", value_text="blue"
    )

    resolved = resolve_trait(conn, 1, "flower_colour")

    assert resolved is not None
    assert [a.value_text for a in resolved.alternatives] == ["violet"]


def test_a_source_nobody_has_added_yet_also_wins(conn: sqlite3.Connection) -> None:
    """`manual` must rank behind *every* other source, not merely behind the two
    named today. Putting it at the end of SOURCE_PRIORITY would have made it beat
    the next source somebody adds."""
    record_colour(conn, taxon_id=1, colour="violet")
    upsert_trait(
        conn, 1, "flower_colour", source="FloraWeb", license="CC-BY-4.0", value_text="red"
    )

    resolved = resolve_trait(conn, 1, "flower_colour")

    assert resolved is not None
    assert resolved.source == "FloraWeb"


def test_it_can_be_taken_back(conn: sqlite3.Connection) -> None:
    record_colour(conn, taxon_id=1, colour="violet")
    record_colour(conn, taxon_id=1, colour=None)

    assert resolve_trait(conn, 1, "flower_colour") is None


def test_taking_it_back_leaves_the_catalogue_alone(conn: sqlite3.Connection) -> None:
    """Deleting the hand entry must delete only that row. It used to be the only
    row for this species; it is not the only one now."""
    upsert_trait(
        conn, 1, "flower_colour", source="GIFT", license="CC-BY-4.0", value_text="blue"
    )
    record_colour(conn, taxon_id=1, colour="violet")

    record_colour(conn, taxon_id=1, colour=None)

    resolved = resolve_trait(conn, 1, "flower_colour")
    assert resolved is not None and resolved.value_text == "blue"


def test_a_colour_the_plan_cannot_draw_is_refused(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValueError):
        record_colour(conn, taxon_id=1, colour="chartreuse")
    assert resolve_trait(conn, 1, "flower_colour") is None


def test_the_drawable_colours_are_the_ones_the_canvas_paints() -> None:
    assert "violet" in DRAWABLE and "chartreuse" not in DRAWABLE


def test_the_entries_can_be_listed(conn: sqlite3.Connection) -> None:
    record_colour(conn, taxon_id=1, colour="violet")
    record_colour(conn, taxon_id=2, colour="white")

    assert manual_colours(conn) == {1: "violet", 2: "white"}


def test_a_deployment_does_not_wipe_it(conn: sqlite3.Connection, tmp_path: Path) -> None:
    """The reason this can live in the catalogue at all.

    The shipped build is re-synced whenever the stamps differ, with
    `INSERT OR REPLACE`. That matches on the primary key — which includes the
    source — so a `manual` row has no counterpart in the image and is never
    replaced. Asserted against a real sync rather than reasoned about.
    """
    shipped = tmp_path / "catalogue.sqlite"
    image: sqlite3.Connection = connect(str(shipped), same_thread=False)
    init_schema(image)
    image.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Salvia pratensis')")
    image.execute(
        "INSERT INTO catalogue_meta (key, value) VALUES ('catalogue_build', 'v2')"
    )
    image.commit()
    image.close()

    record_colour(conn, taxon_id=1, colour="violet")
    sync_catalogue(conn, shipped)

    resolved = resolve_trait(conn, 1, "flower_colour")
    assert resolved is not None
    assert resolved.value_text == "violet"
    assert resolved.source == MANUAL_SOURCE


def test_the_bulk_loader_respects_the_source_order(conn: sqlite3.Connection) -> None:
    """`load_candidates` reads every trait row in one query and used to let the
    last one win, with no regard for the source at all.

    It never mattered: EIVE and GIFT overlap in zero trait keys, so nothing was
    ever arbitrated. Putting hand entries in `trait` is the first time two
    sources claim the same key for the same species, and the suggestion list
    would otherwise have shown whichever row SQLite happened to return last.
    """
    from ninanatur.api.candidates import load_candidates

    conn.execute("UPDATE taxon SET occurs_de = 1 WHERE taxon_id = 1")
    record_colour(conn, taxon_id=1, colour="violet")
    upsert_trait(
        conn, 1, "flower_colour", source="GIFT", license="CC-BY-4.0", value_text="blue"
    )
    conn.commit()

    plant = next(p for p in load_candidates(conn) if p.taxon_id == 1)

    assert plant.text("flower_colour") == "blue"


def test_a_hand_entry_still_answers_where_nothing_else_does(
    conn: sqlite3.Connection,
) -> None:
    """The whole point of allowing it. Colour is recorded for 590 of 8,939
    species, so for most of the catalogue the hand entry is the only answer
    there is."""
    from ninanatur.api.candidates import load_candidates

    conn.execute("UPDATE taxon SET occurs_de = 1 WHERE taxon_id = 1")
    record_colour(conn, taxon_id=1, colour="violet")
    conn.commit()

    plant = next(p for p in load_candidates(conn) if p.taxon_id == 1)

    assert plant.text("flower_colour") == "violet"


def test_notes_made_before_the_change_are_carried_over(tmp_path: Path) -> None:
    """The notes somebody already made. Deciding where these belong by throwing
    them away would be a poor answer, and there are real gardens now."""
    from ninanatur.ingest.migrations import COLOURS_MOVED_KEY, move_observed_colours

    db: sqlite3.Connection = connect(str(tmp_path / "g.sqlite"), same_thread=False)
    init_schema(db)
    db.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Salvia')")
    db.execute(
        "INSERT INTO garden (garden_id, share_token, name, latitude, longitude,"
        " created_at, updated_at) VALUES (1, 'tok', 'G', 52.5, 13.4, 'x', 'x')"
    )
    db.execute("DELETE FROM catalogue_meta WHERE key = ?", (COLOURS_MOVED_KEY,))
    db.execute(
        "INSERT INTO observed_colour (garden_id, taxon_id, colour, noted_at)"
        " VALUES (1, 1, 'violet', '2026-09-01T10:00:00+00:00')"
    )
    db.commit()

    note = move_observed_colours(db)

    assert note is not None and "1" in note
    resolved = resolve_trait(db, 1, "flower_colour")
    assert resolved is not None
    assert (resolved.value_text, resolved.source) == ("violet", MANUAL_SOURCE)


def test_the_move_runs_once(tmp_path: Path) -> None:
    """Run twice it would resurrect a note somebody has since taken back."""
    from ninanatur.ingest.migrations import COLOURS_MOVED_KEY, move_observed_colours

    db: sqlite3.Connection = connect(str(tmp_path / "g.sqlite"), same_thread=False)
    init_schema(db)
    db.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (1, 'Salvia')")
    db.execute(
        "INSERT INTO garden (garden_id, share_token, name, latitude, longitude,"
        " created_at, updated_at) VALUES (1, 'tok', 'G', 52.5, 13.4, 'x', 'x')"
    )
    db.execute("DELETE FROM catalogue_meta WHERE key = ?", (COLOURS_MOVED_KEY,))
    db.execute(
        "INSERT INTO observed_colour (garden_id, taxon_id, colour, noted_at)"
        " VALUES (1, 1, 'violet', 'x')"
    )
    db.commit()
    move_observed_colours(db)
    record_colour(db, taxon_id=1, colour=None)

    assert move_observed_colours(db) is None
    assert resolve_trait(db, 1, "flower_colour") is None
