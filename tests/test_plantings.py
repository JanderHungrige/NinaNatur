"""Plantings: the edge that turns a bed into a plan."""
import sqlite3

import pytest

from ninanatur.garden.models import BedInput
from ninanatur.garden.store import (
    UnknownTaxon,
    add_bed,
    add_planting,
    create_garden,
    delete_garden,
    load_garden,
    remove_planting,
)
from ninanatur.ingest.db import connect, init_schema

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    for tid, name in ((1, "Salvia pratensis"), (2, "Achillea millefolium")):
        c.execute(
            "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
            (tid, name),
        )
    return c


def _bed(c: sqlite3.Connection) -> tuple[int, int]:
    garden_id = create_garden(c, name="G", latitude=52.5, longitude=13.4)
    return garden_id, add_bed(c, garden_id, BedInput(name="Beet", polygon=SQUARE))


def test_a_planting_appears_on_its_bed(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _bed(conn)
    add_planting(conn, bed_id, taxon_id=1, quantity=3)
    bed = load_garden(conn, garden_id).beds[0]
    assert [(p.taxon_id, p.quantity, p.canonical_name) for p in bed.plantings] == [
        (1, 3, "Salvia pratensis")
    ]


def test_planting_the_same_species_twice_raises_the_count(
    conn: sqlite3.Connection,
) -> None:
    """One row per species per bed — a timeline must not have to deduplicate."""
    garden_id, bed_id = _bed(conn)
    add_planting(conn, bed_id, taxon_id=1, quantity=2)
    add_planting(conn, bed_id, taxon_id=1, quantity=3)
    plantings = load_garden(conn, garden_id).beds[0].plantings
    assert len(plantings) == 1
    assert plantings[0].quantity == 5


def test_an_unknown_taxon_is_rejected(conn: sqlite3.Connection) -> None:
    """A dangling reference would leave the timeline silently short a species."""
    _, bed_id = _bed(conn)
    with pytest.raises(UnknownTaxon):
        add_planting(conn, bed_id, taxon_id=999999, quantity=1)


def test_a_quantity_below_one_is_rejected(conn: sqlite3.Connection) -> None:
    """Zero would be a deletion expressed as an update."""
    _, bed_id = _bed(conn)
    with pytest.raises(ValueError):
        add_planting(conn, bed_id, taxon_id=1, quantity=0)


def test_removing_a_planting_takes_it_off_the_bed(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _bed(conn)
    planting_id = add_planting(conn, bed_id, taxon_id=1, quantity=1)
    remove_planting(conn, planting_id)
    assert load_garden(conn, garden_id).beds[0].plantings == []


def test_deleting_a_garden_cascades_all_the_way_to_plantings(
    conn: sqlite3.Connection,
) -> None:
    """Two hops. SQLite only cascades with foreign_keys ON, so prove the chain."""
    garden_id, bed_id = _bed(conn)
    add_planting(conn, bed_id, taxon_id=1, quantity=1)
    add_planting(conn, bed_id, taxon_id=2, quantity=1)
    assert conn.execute("SELECT COUNT(*) n FROM planting").fetchone()["n"] == 2

    delete_garden(conn, garden_id)
    assert conn.execute("SELECT COUNT(*) n FROM bed").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) n FROM planting").fetchone()["n"] == 0


def test_plantings_of_one_bed_do_not_leak_into_another(conn: sqlite3.Connection) -> None:
    garden_id, first = _bed(conn)
    second = add_bed(conn, garden_id, BedInput(name="Zweites", polygon=SQUARE))
    add_planting(conn, first, taxon_id=1, quantity=1)
    add_planting(conn, second, taxon_id=2, quantity=1)
    beds = {b.bed_id: b for b in load_garden(conn, garden_id).beds}
    assert [p.taxon_id for p in beds[first].plantings] == [1]
    assert [p.taxon_id for p in beds[second].plantings] == [2]
