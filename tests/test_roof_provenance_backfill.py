"""Giving existing roofs the provenance their history makes certain (doc 93).

Until Wave 21 the form sent the pre-filled height on every save, so any element
somebody saved carries `height_source = 'user'`. The survey writes a roof, its
source and the eaves together; the raster never writes a roof; the import is the
only other writer of eaves. Those facts decide every row below — and where they
decide nothing, the row is left unmarked rather than guessed at.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.store import create_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.one_time import ROOF_PROVENANCE_KEY, roof_provenance


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:")
    init_schema(connection)
    # A database from before the wave: the marker is not there yet.
    connection.execute("DELETE FROM catalogue_meta WHERE key = ?", (ROOF_PROVENANCE_KEY,))
    connection.commit()
    yield connection


def _element(conn: sqlite3.Connection, **fields: object) -> int:
    garden_id = create_garden(conn, name="G", latitude=51.0, longitude=6.0)
    fields.setdefault("kind", "house")
    return insert_element(
        conn, garden_id, shape="polygon", x=0.0, y=0.0,
        points=[[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]], height=9.0, **fields,
    )


def _sources(conn: sqlite3.Connection, element_id: int) -> tuple[str, str | None]:
    row = conn.execute(
        "SELECT roof_source, eaves_source FROM element WHERE element_id = ?", (element_id,)
    ).fetchone()
    return str(row[0]), row[1]


def test_a_surveyed_roof_somebody_saved_since_is_theirs(conn: sqlite3.Connection) -> None:
    saved = _element(conn, height_source="user", roof="gable", roof_source="surveyed",
                     eaves_m=6.0)
    roof_provenance(conn)
    assert _sources(conn, saved) == ("user", "user")


def test_an_imported_roof_nobody_saved_came_from_openstreetmap(
    conn: sqlite3.Connection,
) -> None:
    imported = _element(conn, height_source="osm_levels", roof="hip", eaves_m=6.0)
    measured = _element(conn, height_source="measured", roof="unknown", eaves_m=3.0)
    roof_provenance(conn)
    assert _sources(conn, imported) == ("osm", "osm_levels")
    assert _sources(conn, measured) == ("osm", "osm_levels")


def test_eaves_the_survey_may_or_may_not_have_written_stay_unmarked(
    conn: sqlite3.Connection,
) -> None:
    surveyed = _element(conn, height_source="surveyed", roof="gable",
                        roof_source="surveyed", eaves_m=6.2)
    roof_provenance(conn)
    assert _sources(conn, surveyed) == ("surveyed", None)


def test_what_nobody_said_stays_unsaid(conn: sqlite3.Connection) -> None:
    drawn = _element(conn, height_source="user", roof="unknown")
    tree = _element(conn, kind="tree", height_source="measured")
    roof_provenance(conn)
    assert _sources(conn, drawn) == ("user", None)
    # Only a roofed kind has a roof to come from somewhere.
    assert _sources(conn, tree) == ("user", None)


def test_it_runs_once(conn: sqlite3.Connection) -> None:
    _element(conn, height_source="osm_levels", roof="hip", eaves_m=6.0)
    assert roof_provenance(conn) is not None
    later = _element(conn, height_source="osm_levels", roof="hip", eaves_m=6.0)
    assert roof_provenance(conn) is None
    # A row written after the backfill is the new code's to mark, not the backfill's.
    assert _sources(conn, later) == ("user", None)


def test_a_new_database_is_marked_without_anything_to_do() -> None:
    fresh: sqlite3.Connection = connect(":memory:")
    init_schema(fresh)
    marked = fresh.execute(
        "SELECT 1 FROM catalogue_meta WHERE key = ?", (ROOF_PROVENANCE_KEY,)
    ).fetchone()
    assert marked is not None
