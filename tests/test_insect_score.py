"""The insect score, and the property the swap search depends on."""
import sqlite3

import pytest

from ninanatur.bloom.score import (
    MONTH_SATURATION,
    ORIGIN_FACTOR,
    garden_score,
    species_forage,
)
from ninanatur.garden.models import BedInput
from ninanatur.garden.store import add_bed, add_planting, create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def conn() -> sqlite3.Connection:
    c = connect(":memory:", same_thread=False)
    init_schema(c)
    return c


def _species(c: sqlite3.Connection, tid: int, name: str, start: int, end: int,
             partners: int = 0, origin: str = "native") -> None:
    c.execute("INSERT INTO taxon (taxon_id, canonical_name, occurs_de) VALUES (?, ?, 1)",
              (tid, name))
    upsert_trait(c, tid, "flowering_start_month", value_num=float(start),
                 source="GIFT", license="CC-BY-4.0")
    upsert_trait(c, tid, "flowering_end_month", value_num=float(end),
                 source="GIFT", license="CC-BY-4.0")
    upsert_trait(c, tid, "native_de", value_text=origin,
                 source="GBIF-WCVP", license="CC-BY-4.0")
    if partners:
        c.execute("INSERT OR REPLACE INTO partner_totals (taxon_id, german, global_total,"
                  " unmatched) VALUES (?, ?, ?, 0)", (tid, partners, partners))
        c.execute("INSERT OR REPLACE INTO partner_groups (taxon_id, insect_group, german)"
                  " VALUES (?, 'bee', ?)", (tid, partners // 2))
    c.commit()


def _garden(c: sqlite3.Connection, *taxa: int) -> int:
    gid = create_garden(c, name="G", latitude=52.5, longitude=13.4)
    bed = add_bed(c, gid, BedInput(name="Beet", polygon=SQUARE))
    for t in taxa:
        add_planting(c, bed, taxon_id=t, quantity=1)
    return gid


# --- per species ----------------------------------------------------------

def test_more_partners_is_worth_more() -> None:
    a, b, c = (species_forage(n, "native") for n in (4, 49, 400))
    assert a < b < c


def test_equal_increments_of_partners_are_worth_less_the_higher_you_go() -> None:
    """Diminishing returns compares EQUAL increments — comparing 4->49 against
    49->400 measures the range, not the curve. Raw counts would let one
    well-studied plant dominate a whole garden; the square root is what stops it.
    """
    steps = [species_forage(n, "native") for n in (0, 100, 200, 300, 400)]
    gains = [b - a for a, b in zip(steps[:-1], steps[1:], strict=True)]
    assert gains == sorted(gains, reverse=True)
    assert gains[0] > 2 * gains[-1], "the first hundred partners matter far more"


def test_origin_scales_the_value_without_zeroing_it() -> None:
    """Introduced species are not worthless to insects."""
    native = species_forage(100, "native")
    introduced = species_forage(100, "introduced")
    assert 0 < introduced < native
    assert introduced == pytest.approx(native * ORIGIN_FACTOR["introduced"])


def test_unknown_origin_sits_between_the_two() -> None:
    values = [species_forage(100, o) for o in ("introduced", "unknown", "native")]
    assert values == sorted(values)


def test_a_species_with_no_records_still_has_a_base_value() -> None:
    """Unknown is not worthless — the rule the whole project runs on."""
    assert species_forage(0, "native") > 0


# --- the garden -----------------------------------------------------------

def test_an_empty_garden_scores_zero_and_says_so(conn: sqlite3.Connection) -> None:
    gid = create_garden(conn, name="Leer", latitude=52.5, longitude=13.4)
    result = garden_score(conn, load_garden(conn, gid))
    assert result.score == 0.0
    assert result.is_empty


def test_a_planted_garden_scores_above_zero(conn: sqlite3.Connection) -> None:
    _species(conn, 1, "Junibluete", 6, 7, partners=100)
    result = garden_score(conn, load_garden(conn, _garden(conn, 1)))
    assert result.score > 0


def test_spreading_the_season_beats_piling_into_one_month(
    conn: sqlite3.Connection,
) -> None:
    """Continuity is the point, and it falls out of the saturation rather than
    being bolted on as a multiplier."""
    for tid in (1, 2, 3):
        _species(conn, tid, f"Juni{tid}", 6, 6, partners=100)
    _species(conn, 4, "Fruehling", 4, 4, partners=100)
    _species(conn, 5, "Herbst", 9, 9, partners=100)

    piled = garden_score(conn, load_garden(conn, _garden(conn, 1, 2, 3))).score
    spread = garden_score(conn, load_garden(conn, _garden(conn, 1, 4, 5))).score
    assert spread > piled


# --- the property the swap search rests on --------------------------------

def test_the_score_is_submodular(conn: sqlite3.Connection) -> None:
    """Adding a species to a fuller garden must never gain more than adding it to
    a sparser one. The greedy swap search in 19 is only defensible because of this;
    asserted directly rather than trusting the formula to keep its shape."""
    for tid in (1, 2, 3):
        _species(conn, tid, f"Juni{tid}", 6, 6, partners=100)

    small = garden_score(conn, load_garden(conn, _garden(conn, 1))).score
    small_plus = garden_score(conn, load_garden(conn, _garden(conn, 1, 3))).score
    large = garden_score(conn, load_garden(conn, _garden(conn, 1, 2))).score
    large_plus = garden_score(conn, load_garden(conn, _garden(conn, 1, 2, 3))).score

    assert (small_plus - small) >= (large_plus - large) - 1e-9


def test_a_saturated_month_gains_nothing_from_one_more_species(
    conn: sqlite3.Connection,
) -> None:
    huge = int((MONTH_SATURATION * 2) ** 2)
    _species(conn, 1, "Massentracht", 6, 6, partners=huge)
    _species(conn, 2, "Nochmehr", 6, 6, partners=huge)
    alone = garden_score(conn, load_garden(conn, _garden(conn, 1))).score
    both = garden_score(conn, load_garden(conn, _garden(conn, 1, 2))).score
    assert both == pytest.approx(alone)


# --- explainability -------------------------------------------------------

def test_the_score_reports_its_components(conn: sqlite3.Connection) -> None:
    """A score a user cannot interrogate is decoration."""
    _species(conn, 1, "Junibluete", 6, 7, partners=100)
    result = garden_score(conn, load_garden(conn, _garden(conn, 1)))
    assert result.by_species[0].canonical_name == "Junibluete"
    assert result.by_species[0].german_partners == 100
    assert result.by_month[6] > 0
    assert result.by_group["bee"] == 50


def test_plantings_without_records_are_counted_and_reported(
    conn: sqlite3.Connection,
) -> None:
    _species(conn, 1, "Unerforscht", 6, 6, partners=0)
    result = garden_score(conn, load_garden(conn, _garden(conn, 1)))
    assert result.plantings_without_interaction_data == 1
    assert result.score > 0
