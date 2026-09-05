"""A plant standing in light it did not ask for."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.lightgrid import compute_grid
from ninanatur.garden.misplaced import TOLERANCE, misplaced_plantings
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.plantings import add_planting, place_planting
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.solar.shading import Obstacle

EIVE = {"source": "EIVE-1.0", "license": "CC-BY-4.0"}
BED = [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]]
#: A tall wall right along the southern edge, so the strip behind it is dark and
#: the far end is not.
WALL = Obstacle(footprint=[(0.0, -1.0), (10.0, -1.0), (10.0, -0.4), (0.0, -0.4)],
                height=9.0)


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    c: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(c)
    for tid, name, light in ((1, "Sonnenkraut", 8.0), (2, "Schattenkraut", 3.0),
                             (3, "Namenlos", None)):
        c.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (?, ?)", (tid, name))
        if light is not None:
            upsert_trait(c, tid, "ellenberg_l", value_num=light, **EIVE)
    c.commit()
    yield c


def _garden(conn: sqlite3.Connection) -> tuple[int, int]:
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    bed_id = insert_element(
        conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
        name="Beet", points=BED,
    )
    conn.commit()
    return garden_id, bed_id


def _found(conn: sqlite3.Connection, garden_id: int) -> list[object]:
    garden = load_garden(conn, garden_id)
    return list(misplaced_plantings(conn, garden, compute_grid(garden, [WALL])))


def test_a_sun_plant_in_the_shade_is_flagged(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _garden(conn)
    planting_id = add_planting(conn, bed_id, taxon_id=1, quantity=1)
    place_planting(conn, planting_id, 5.0, 0.3)  # right against the wall

    found = _found(conn, garden_id)

    assert len(found) == 1
    assert found[0].problem == "too_dark"  # type: ignore[attr-defined]
    assert found[0].name == "Sonnenkraut"  # type: ignore[attr-defined]


def test_the_same_plant_at_the_far_end_is_fine(conn: sqlite3.Connection) -> None:
    """The whole reason this needed a grid. One number per bed could only ever
    say the bed is wrong, never the corner — and "this bed is too dark" for a
    bed whose far end is in full sun teaches people to ignore advice."""
    garden_id, bed_id = _garden(conn)
    planting_id = add_planting(conn, bed_id, taxon_id=1, quantity=1)
    place_planting(conn, planting_id, 5.0, 7.5)

    assert _found(conn, garden_id) == []


def test_a_shade_plant_in_full_sun_is_flagged_too(conn: sqlite3.Connection) -> None:
    """The forgotten direction. A fern in the open is as misplaced as a sedum
    under a hedge, and only one of the two gets talked about."""
    garden_id, bed_id = _garden(conn)
    planting_id = add_planting(conn, bed_id, taxon_id=2, quantity=1)
    place_planting(conn, planting_id, 5.0, 7.5)

    found = _found(conn, garden_id)

    assert len(found) == 1
    assert found[0].problem == "too_bright"  # type: ignore[attr-defined]


def test_a_small_difference_is_not_worth_saying(conn: sqlite3.Connection) -> None:
    """One rung is inside the noise of a model whose building heights are mostly
    assumed, and a warning nobody can act on is one people learn to scroll
    past."""
    garden_id, bed_id = _garden(conn)
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (4, 'Fast')")
    upsert_trait(conn, 4, "ellenberg_l", value_num=8.0 - (TOLERANCE - 0.5), **EIVE)
    conn.commit()
    planting_id = add_planting(conn, bed_id, taxon_id=4, quantity=1)
    place_planting(conn, planting_id, 5.0, 7.5)

    assert _found(conn, garden_id) == []


def test_a_species_with_no_indicator_value_is_left_alone(
    conn: sqlite3.Connection,
) -> None:
    """EIVE covers a good part of the flora and not all of it. A plant nobody
    has a value for cannot be said to be in the wrong light."""
    garden_id, bed_id = _garden(conn)
    planting_id = add_planting(conn, bed_id, taxon_id=3, quantity=1)
    place_planting(conn, planting_id, 5.0, 0.3)

    assert _found(conn, garden_id) == []


def test_nothing_is_said_without_a_grid(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _garden(conn)
    add_planting(conn, bed_id, taxon_id=1, quantity=1)

    assert misplaced_plantings(conn, load_garden(conn, garden_id), None) == []
