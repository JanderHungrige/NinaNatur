"""Turning a score into something to do about it."""
import sqlite3

import pytest

from ninanatur.bloom.improve import (
    Change,
    garden_improvements,
    marginal_gain,
)
from ninanatur.bloom.score import MONTH_SATURATION, garden_score
from ninanatur.garden.models import BedInput
from ninanatur.garden.store import add_bed, add_planting, create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


# --- the gain arithmetic ---------------------------------------------------

def test_a_candidate_gains_its_full_value_in_an_empty_month() -> None:
    current = dict.fromkeys(range(3, 11), 0.0)
    assert marginal_gain(current, forage=10.0, months=(4,)) == pytest.approx(10.0)


def test_a_candidate_gains_nothing_in_a_saturated_month() -> None:
    """The cap is what makes 'more of the same' worthless."""
    current = dict.fromkeys(range(3, 11), 0.0)
    current[7] = MONTH_SATURATION
    assert marginal_gain(current, forage=10.0, months=(7,)) == pytest.approx(0.0)


def test_a_partly_full_month_gains_only_the_headroom() -> None:
    current = dict.fromkeys(range(3, 11), 0.0)
    current[7] = MONTH_SATURATION - 3
    assert marginal_gain(current, forage=10.0, months=(7,)) == pytest.approx(3.0)


def test_months_outside_the_season_contribute_nothing() -> None:
    current = dict.fromkeys(range(3, 11), 0.0)
    assert marginal_gain(current, forage=10.0, months=(1, 12)) == pytest.approx(0.0)


def test_gain_never_goes_negative() -> None:
    current = dict.fromkeys(range(3, 11), MONTH_SATURATION)
    assert marginal_gain(current, forage=50.0, months=(4, 5, 6)) == pytest.approx(0.0)


# --- against a real garden -------------------------------------------------

@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    return c


def _species(c: sqlite3.Connection, tid: int, name: str, start: int, end: int,
             partners: int, light: float = 8.0) -> None:
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
              (tid, name))
    for key, val in (("ellenberg_l", light), ("ellenberg_m", 5.0), ("ellenberg_n", 5.0)):
        upsert_trait(c, tid, key, value_num=val, source="EIVE-1.0", license="CC-BY-4.0")
    upsert_trait(c, tid, "ellenberg_l_nw", value_num=3.0, source="EIVE-1.0", license="CC-BY-4.0")
    upsert_trait(c, tid, "flowering_start_month", value_num=float(start),
                 source="GIFT", license="CC-BY-4.0")
    upsert_trait(c, tid, "flowering_end_month", value_num=float(end),
                 source="GIFT", license="CC-BY-4.0")
    upsert_trait(c, tid, "native_de", value_text="native", source="GBIF-WCVP", license="CC-BY-4.0")
    upsert_trait(c, tid, "growth_form", value_text="forb", source="GIFT", license="CC-BY-4.0")
    c.execute("INSERT OR REPLACE INTO partner_totals (taxon_id, german, global_total, unmatched)"
              " VALUES (?, ?, ?, 0)", (tid, partners, partners))
    c.execute("INSERT OR REPLACE INTO partner_groups (taxon_id, insect_group, german)"
              " VALUES (?, 'bee', ?)", (tid, partners // 2))
    c.commit()


def _garden_with_a_june_only_planting(c: sqlite3.Connection) -> int:
    _species(c, 1, "Junikraut", 6, 6, partners=400)
    _species(c, 2, "Aprilkraut", 4, 4, partners=400)     # fills the spring gap
    _species(c, 3, "Nochmehrjuni", 6, 6, partners=400)   # piles into a full month
    _species(c, 4, "Schattenkraut", 4, 4, partners=400, light=1.0)  # wrong site
    gid = create_garden(c, name="G", latitude=52.5, longitude=13.4)
    bed = add_bed(c, gid, BedInput(name="Beet", polygon=SQUARE,
                                   soil_type="loam", moisture="fresh"))
    add_planting(c, bed, taxon_id=1, quantity=1)
    return gid


def test_the_species_filling_a_gap_is_ranked_above_one_piling_into_a_full_month(
    conn: sqlite3.Connection,
) -> None:
    gid = _garden_with_a_june_only_planting(conn)
    result = garden_improvements(conn, load_garden(conn, gid))
    names = [c.canonical_name for c in result.additions]
    assert names.index("Aprilkraut") < names.index("Nochmehrjuni")


def test_a_species_that_does_not_suit_the_bed_is_not_proposed(
    conn: sqlite3.Connection,
) -> None:
    """A swap that raises the score and kills the plant is not an improvement."""
    gid = _garden_with_a_june_only_planting(conn)
    result = garden_improvements(conn, load_garden(conn, gid))
    assert "Schattenkraut" not in [c.canonical_name for c in result.additions]


def test_something_already_planted_is_not_proposed_again(
    conn: sqlite3.Connection,
) -> None:
    gid = _garden_with_a_june_only_planting(conn)
    result = garden_improvements(conn, load_garden(conn, gid))
    assert "Junikraut" not in [c.canonical_name for c in result.additions]


def test_suggestions_with_no_gain_are_not_shown(conn: sqlite3.Connection) -> None:
    """Padding the list would train users to ignore it."""
    gid = _garden_with_a_june_only_planting(conn)
    result = garden_improvements(conn, load_garden(conn, gid))
    assert all(c.gain > 0 for c in result.additions)


def test_each_suggestion_says_why_in_a_sentence(conn: sqlite3.Connection) -> None:
    gid = _garden_with_a_june_only_planting(conn)
    result = garden_improvements(conn, load_garden(conn, gid))
    april = next(c for c in result.additions if c.canonical_name == "Aprilkraut")
    assert isinstance(april, Change)
    assert "April" in april.reason


def test_the_reported_gain_matches_what_actually_happens(
    conn: sqlite3.Connection,
) -> None:
    """The cheap delta must agree with rescoring the garden for real."""
    gid = _garden_with_a_june_only_planting(conn)
    garden = load_garden(conn, gid)
    before = garden_score(conn, garden).score
    best = garden_improvements(conn, garden).additions[0]

    add_planting(conn, garden.beds[0].bed_id, taxon_id=best.taxon_id, quantity=1)
    after = garden_score(conn, load_garden(conn, gid)).score
    assert after - before == pytest.approx(best.gain, abs=0.15)


def test_a_swap_replaces_a_weaker_planting(conn: sqlite3.Connection) -> None:
    _species(conn, 1, "Schwachtracht", 6, 6, partners=1)
    _species(conn, 2, "Starktracht", 6, 6, partners=900)
    gid = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    bed = add_bed(conn, gid, BedInput(name="Beet", polygon=SQUARE,
                                      soil_type="loam", moisture="fresh"))
    add_planting(conn, bed, taxon_id=1, quantity=1)

    result = garden_improvements(conn, load_garden(conn, gid))
    swap = result.swaps[0]
    assert swap.replaces_name == "Schwachtracht"
    assert swap.canonical_name == "Starktracht"
    assert swap.gain > 0


def test_an_empty_garden_gets_additions_but_no_swaps(conn: sqlite3.Connection) -> None:
    _species(conn, 1, "Irgendwas", 6, 6, partners=100)
    gid = create_garden(conn, name="Leer", latitude=52.5, longitude=13.4)
    add_bed(conn, gid, BedInput(name="Beet", polygon=SQUARE, soil_type="loam", moisture="fresh"))
    result = garden_improvements(conn, load_garden(conn, gid))
    assert result.swaps == []
    assert result.additions, "there is nothing to swap, but plenty to add"


def test_a_barely_fitting_species_is_not_proposed_even_with_few_candidates(
    conn: sqlite3.Connection,
) -> None:
    """Top-N alone relies on there being enough good candidates. A bed with
    unusual conditions would otherwise be handed the least bad of a bad lot."""
    _species(conn, 1, "Passt", 6, 6, partners=100, light=8.0)
    _species(conn, 2, "Passt nicht", 4, 4, partners=900, light=1.0)
    gid = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    add_bed(conn, gid, BedInput(name="Beet", polygon=SQUARE,
                                soil_type="loam", moisture="fresh"))
    names = [c.canonical_name for c in garden_improvements(conn, load_garden(conn, gid)).additions]
    assert "Passt" in names
    assert "Passt nicht" not in names, "900 partners cannot buy a place in the wrong bed"
