"""The bloom year, and the gaps in it."""
import sqlite3

import pytest

from ninanatur.bloom.timeline import (
    GAP_THRESHOLD,
    SEASON_MONTHS,
    TimelineMode,
    flowering_months,
    garden_timeline,
)
from ninanatur.garden.models import BedInput
from ninanatur.garden.store import add_bed, add_planting, create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


# --- interval expansion ---------------------------------------------------

def test_a_normal_interval_covers_its_months() -> None:
    assert flowering_months(5, 8) == (5, 6, 7, 8)


def test_a_single_month_interval_works() -> None:
    assert flowering_months(6, 6) == (6,)


def test_an_interval_wrapping_the_year_end_is_expanded_both_sides() -> None:
    """132 species do this. range(start, end+1) silently yields nothing for them,
    and they are the ones covering the hardest part of the year."""
    assert flowering_months(11, 2) == (11, 12, 1, 2)


def test_a_missing_bound_yields_nothing_rather_than_guessing() -> None:
    assert flowering_months(None, 8) == ()
    assert flowering_months(5, None) == ()


# --- the timeline ---------------------------------------------------------

@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    return c


def _species(c: sqlite3.Connection, tid: int, name: str, start: int, end: int,
             partners: int = 0) -> None:
    c.execute(
        "INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
        (tid, name),
    )
    upsert_trait(c, tid, "flowering_start_month", value_num=float(start),
                 source="GIFT", license="CC-BY-4.0")
    upsert_trait(c, tid, "flowering_end_month", value_num=float(end),
                 source="GIFT", license="CC-BY-4.0")
    for i in range(partners):
        c.execute(
            "INSERT OR IGNORE INTO insect_de (canonical_name, occurrences) VALUES (?, 9)",
            (f"Insectum {tid}-{i}",),
        )
        c.execute(
            "INSERT INTO interaction (taxon_id, partner_name, interaction_type, source, license)"
            " VALUES (?, ?, 'visitedBy', 'GloBI', 'CC0-1.0')",
            (tid, f"Insectum {tid}-{i}"),
        )
    c.commit()


def _garden_with(c: sqlite3.Connection, *taxa: int) -> int:
    garden_id = create_garden(c, name="G", latitude=52.5, longitude=13.4)
    bed_id = add_bed(c, garden_id, BedInput(name="Beet", polygon=SQUARE))
    for taxon_id in taxa:
        add_planting(c, bed_id, taxon_id=taxon_id, quantity=1)
    return garden_id


def test_an_empty_garden_has_no_gaps_because_it_has_nothing(
    conn: sqlite3.Connection,
) -> None:
    """A plan with nothing planted has no gaps; it has nothing."""
    garden_id = create_garden(conn, name="Leer", latitude=52.5, longitude=13.4)
    timeline = garden_timeline(conn, load_garden(conn, garden_id))
    assert timeline.gaps == []
    assert timeline.is_empty


def test_a_planted_month_is_covered(conn: sqlite3.Connection) -> None:
    _species(conn, 1, "Junibluete", 6, 7, partners=5)
    timeline = garden_timeline(conn, load_garden(conn, _garden_with(conn, 1)))
    assert timeline.months[6].coverage > 0
    assert timeline.months[4].coverage == 0


def test_a_gap_is_found_inside_the_season_only(conn: sqlite3.Connection) -> None:
    """The winter trough is not a finding — reporting it would train users to ignore this."""
    _species(conn, 1, "Sommerbluete", 6, 8, partners=5)
    timeline = garden_timeline(conn, load_garden(conn, _garden_with(conn, 1)))
    gap_months = {m for gap in timeline.gaps for m in gap.months}
    assert gap_months
    assert gap_months <= set(SEASON_MONTHS)
    assert 1 not in gap_months and 12 not in gap_months


def test_filling_the_gap_removes_it(conn: sqlite3.Connection) -> None:
    _species(conn, 1, "Sommerbluete", 6, 8, partners=5)
    _species(conn, 2, "Fruehbluete", 3, 5, partners=5)
    _species(conn, 3, "Spaetbluete", 9, 10, partners=5)
    before = garden_timeline(conn, load_garden(conn, _garden_with(conn, 1)))
    after = garden_timeline(conn, load_garden(conn, _garden_with(conn, 1, 2, 3)))
    assert len(after.gaps) < len(before.gaps)


def test_a_wrapping_species_covers_the_early_months(conn: sqlite3.Connection) -> None:
    _species(conn, 1, "Winterbluete", 11, 3, partners=5)
    timeline = garden_timeline(conn, load_garden(conn, _garden_with(conn, 1)))
    assert timeline.months[3].coverage > 0, "March must be covered by a Nov-Mar species"
    assert timeline.months[12].coverage > 0


# --- the two weightings ---------------------------------------------------

def test_forage_mode_ranks_an_insect_plant_above_a_showy_one(
    conn: sqlite3.Connection,
) -> None:
    """A month of nectarless cultivars is correctly a gap — only this view can say so."""
    _species(conn, 1, "Insektenmagnet", 6, 6, partners=40)
    _species(conn, 2, "Ziersorte", 7, 7, partners=0)
    conn.execute("INSERT INTO interaction (taxon_id, partner_name, interaction_type,"
                 " source, license) VALUES (2, 'Nichtdeutsch', 'visitedBy', 'GloBI', 'CC0-1.0')")
    conn.commit()
    timeline = garden_timeline(conn, load_garden(conn, _garden_with(conn, 1, 2)),
                               mode=TimelineMode.FORAGE)
    assert timeline.months[6].coverage > timeline.months[7].coverage


def test_visual_mode_treats_them_equally(conn: sqlite3.Connection) -> None:
    _species(conn, 1, "Insektenmagnet", 6, 6, partners=40)
    _species(conn, 2, "Ziersorte", 7, 7, partners=0)
    timeline = garden_timeline(conn, load_garden(conn, _garden_with(conn, 1, 2)),
                               mode=TimelineMode.VISUAL)
    assert timeline.months[6].coverage == timeline.months[7].coverage


def test_a_species_without_interaction_data_still_counts_in_forage_mode(
    conn: sqlite3.Connection,
) -> None:
    """Unknown is not the same as worthless — the rule this whole project runs on."""
    _species(conn, 1, "Unerforscht", 6, 6, partners=0)
    timeline = garden_timeline(conn, load_garden(conn, _garden_with(conn, 1)),
                               mode=TimelineMode.FORAGE)
    assert timeline.months[6].coverage > 0
    assert timeline.plantings_without_interaction_data == 1


def test_each_month_names_the_species_that_contributed(
    conn: sqlite3.Connection,
) -> None:
    """A gap that cannot explain itself is just a red bar."""
    _species(conn, 1, "Junibluete", 6, 6, partners=3)
    timeline = garden_timeline(conn, load_garden(conn, _garden_with(conn, 1)))
    assert timeline.months[6].species == ("Junibluete",)


def test_the_gap_threshold_is_a_named_constant_not_a_literal() -> None:
    assert 0.0 < GAP_THRESHOLD < 1.0
