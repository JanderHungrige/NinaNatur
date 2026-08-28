"""Persisting a garden — and the share token that is its only lock."""
import json
import sqlite3

import pytest

from ninanatur.garden.models import BedInput, ObstacleInput
from ninanatur.garden.store import (
    PolygonError,
    add_bed,
    add_obstacle,
    create_garden,
    delete_garden,
    garden_by_token,
    load_garden,
    recompute_light,
)
from ninanatur.ingest.db import connect, init_schema

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    return c


def _garden(c: sqlite3.Connection) -> int:
    return create_garden(c, name="Testgarten", latitude=52.52, longitude=13.40)


# --- the share token is the entire access model ---------------------------

def test_each_garden_gets_a_distinct_unguessable_token(conn: sqlite3.Connection) -> None:
    tokens = {load_garden(conn, _garden(conn)).share_token for _ in range(20)}
    assert len(tokens) == 20, "tokens must not repeat"
    assert all(len(t) >= 22 for t in tokens), "too short to resist guessing"


def test_tokens_are_not_sequential_or_derived_from_the_name(
    conn: sqlite3.Connection,
) -> None:
    """A guessable token is not a weaker lock, it is no lock."""
    first = load_garden(conn, _garden(conn)).share_token
    second = load_garden(conn, _garden(conn)).share_token
    assert first != second
    assert "Testgarten" not in first
    assert not first.isdigit()


def test_a_garden_can_be_fetched_by_its_token(conn: sqlite3.Connection) -> None:
    garden = load_garden(conn, _garden(conn))
    assert garden_by_token(conn, garden.share_token).garden_id == garden.garden_id


def test_an_unknown_token_returns_none(conn: sqlite3.Connection) -> None:
    assert garden_by_token(conn, "definitely-not-a-real-token") is None


# --- storage rules --------------------------------------------------------

def test_location_is_stored_rounded_to_a_tenth_of_a_degree(
    conn: sqlite3.Connection,
) -> None:
    gid = create_garden(conn, name="Präzise", latitude=52.5170365, longitude=13.3888599)
    garden = load_garden(conn, gid)
    assert (garden.latitude, garden.longitude) == (52.5, 13.4)


def test_a_bed_stores_its_polygon_and_derived_axes(conn: sqlite3.Connection) -> None:
    gid = _garden(conn)
    bed_id = add_bed(conn, gid, BedInput(name="Südbeet", polygon=SQUARE,
                                         soil_type="loam", moisture="fresh"))
    bed = next(b for b in load_garden(conn, gid).beds if b.bed_id == bed_id)
    assert json.loads(json.dumps(bed.polygon)) == SQUARE
    assert bed.ellenberg_m == 5.0
    assert bed.ellenberg_r == 6.5


def test_a_polygon_with_too_few_points_is_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(PolygonError):
        add_bed(conn, _garden(conn), BedInput(name="Linie", polygon=[[0, 0], [1, 1]]))


def test_deleting_a_garden_removes_its_beds_and_obstacles(
    conn: sqlite3.Connection,
) -> None:
    gid = _garden(conn)
    add_bed(conn, gid, BedInput(name="Beet", polygon=SQUARE))
    add_obstacle(conn, gid, ObstacleInput(kind="wall", x=0, y=-3, radius=5, height=6))
    delete_garden(conn, gid)
    assert conn.execute("SELECT COUNT(*) n FROM bed").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) n FROM obstacle").fetchone()["n"] == 0


# --- light is computed on save --------------------------------------------

def test_recompute_fills_the_light_value_and_records_when(
    conn: sqlite3.Connection,
) -> None:
    gid = _garden(conn)
    add_bed(conn, gid, BedInput(name="Beet", polygon=SQUARE))
    recompute_light(conn, gid)
    bed = load_garden(conn, gid).beds[0]
    assert bed.ellenberg_l is not None
    assert bed.sun_hours is not None
    assert bed.light_computed_at, "a stale value must be detectable"


def test_an_obstacle_to_the_south_lowers_the_light_value(
    conn: sqlite3.Connection,
) -> None:
    """The end-to-end point of the whole wave, asserted through the store."""
    gid = _garden(conn)
    add_bed(conn, gid, BedInput(name="Beet", polygon=SQUARE))
    recompute_light(conn, gid)
    before = load_garden(conn, gid).beds[0].sun_hours

    add_obstacle(conn, gid, ObstacleInput(kind="wall", x=2, y=-3, radius=8, height=9))
    recompute_light(conn, gid)
    after = load_garden(conn, gid).beds[0].sun_hours
    assert after < before
