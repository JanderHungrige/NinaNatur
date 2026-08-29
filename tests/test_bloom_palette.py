"""What colour a bed is in a given month, and what it is when we do not know.

Flower colour is recorded for 590 of 8,939 species. A bed whose plants have no
recorded colour must not come out green, grey or beige — every one of those
reads as an answer, and a fill is the most confident thing a UI can draw.
"""
import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.bloom.palette import garden_palette
from ninanatur.garden.models import BedInput
from ninanatur.garden.store import add_bed, add_planting, create_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait

GIFT = {"source": "GIFT", "license": "CC-BY-4.0"}
SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


def _species(c: sqlite3.Connection, tid: int, name: str, colour: str | None,
             flowering: tuple[int, int] | None) -> None:
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
              (tid, name))
    if colour is not None:
        upsert_trait(c, tid, "flower_colour", value_text=colour, **GIFT)
    if flowering is not None:
        upsert_trait(c, tid, "flowering_start_month", value_num=float(flowering[0]), **GIFT)
        upsert_trait(c, tid, "flowering_end_month", value_num=float(flowering[1]), **GIFT)


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    c = connect(":memory:")
    init_schema(c)
    _species(c, 1, "Gelbling", "yellow", (5, 7))
    _species(c, 2, "Blauling", "blue", (6, 8))
    _species(c, 3, "Farblos", None, (6, 8))
    _species(c, 4, "Winterbluete", "white", (12, 2))
    _species(c, 5, "Ohne Zeit", "red", None)
    yield c


def _bed(c: sqlite3.Connection) -> tuple[int, int]:
    garden_id = create_garden(c, name="G", latitude=52.5, longitude=13.4)
    bed_id = add_bed(c, garden_id, BedInput(name="B", polygon=SQUARE,
                                            soil_type="loam", moisture="fresh"))
    return garden_id, bed_id


def _month(palette: dict, bed_id: int, month: int) -> dict:
    bed = next(b for b in palette["beds"] if b["bed_id"] == bed_id)
    return next(m for m in bed["months"] if m["month"] == month)


def test_a_bed_takes_the_colours_flowering_that_month(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _bed(conn)
    add_planting(conn, bed_id, taxon_id=1)
    add_planting(conn, bed_id, taxon_id=2)
    palette = garden_palette(conn, garden_id)
    assert sorted(_month(palette, bed_id, 6)["colours"]) == ["blue", "yellow"]


def test_a_colour_out_of_season_is_not_shown(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _bed(conn)
    add_planting(conn, bed_id, taxon_id=1)  # May to July
    assert _month(palette := garden_palette(conn, garden_id), bed_id, 9)["colours"] == []
    assert _month(palette, bed_id, 6)["colours"] == ["yellow"]


def test_an_unrecorded_colour_is_counted_not_coloured(conn: sqlite3.Connection) -> None:
    """The whole point. 6.6% coverage means most beds would otherwise be a lie."""
    garden_id, bed_id = _bed(conn)
    add_planting(conn, bed_id, taxon_id=3)
    june = _month(garden_palette(conn, garden_id), bed_id, 6)
    assert june["colours"] == []
    assert june["unknown"] == 1
    assert june["flowering"] == 1


def test_wrapping_windows_are_honoured(conn: sqlite3.Connection) -> None:
    # 132 German species flower across the year end; the month filter was fixed
    # for exactly this in Wave 6 and this reads the same function.
    garden_id, bed_id = _bed(conn)
    add_planting(conn, bed_id, taxon_id=4)  # December to February
    palette = garden_palette(conn, garden_id)
    assert _month(palette, bed_id, 1)["colours"] == ["white"]
    assert _month(palette, bed_id, 6)["colours"] == []


def test_a_plant_with_no_recorded_window_flowers_in_no_month(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _bed(conn)
    add_planting(conn, bed_id, taxon_id=5)
    palette = garden_palette(conn, garden_id)
    assert all(m["flowering"] == 0 for m in palette["beds"][0]["months"])


def test_an_unidentified_planting_contributes_nothing(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _bed(conn)
    add_planting(conn, bed_id, raw_name="Bauernhortensie")
    palette = garden_palette(conn, garden_id)
    assert all(m["flowering"] == 0 for m in palette["beds"][0]["months"])


def test_every_bed_gets_all_twelve_months(conn: sqlite3.Connection) -> None:
    """The player steps through the year; a missing month would be a gap in the
    animation rather than an empty bed."""
    garden_id, bed_id = _bed(conn)
    palette = garden_palette(conn, garden_id)
    months = [m["month"] for m in palette["beds"][0]["months"]]
    assert months == list(range(1, 13))


def test_a_colour_is_listed_once_however_many_plants_have_it(
    conn: sqlite3.Connection,
) -> None:
    garden_id, bed_id = _bed(conn)
    _species(conn, 6, "Zweiter Gelbling", "yellow", (5, 7))
    conn.commit()
    add_planting(conn, bed_id, taxon_id=1)
    add_planting(conn, bed_id, taxon_id=6)
    assert _month(garden_palette(conn, garden_id), bed_id, 6)["colours"] == ["yellow"]
