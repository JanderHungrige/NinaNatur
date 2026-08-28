"""EIVE parsing: the 0-10 indicator scale and the header layout must be handled exactly."""
import pandas as pd
import pytest

from ninanatur.ingest.sources.eive import EIVE_TRAIT_MAP, parse_eive_frame


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TaxonConcept": ["Achillea millefolium", "Salvia pratensis", "Bad taxon"],
            "TaxonRank": ["Species", "Species", "Genus"],
            "EIVEres-M": [4.5, 3.2, 1.0],
            "EIVEres-N": [5.0, 3.0, 1.0],
            "EIVEres-R": [6.5, 7.8, 1.0],
            "EIVEres-L": [7.0, 8.1, 1.0],
            "EIVEres-T": [5.5, 6.0, 1.0],
        }
    )


def test_parse_maps_every_present_column_to_a_canonical_trait_key() -> None:
    """Columns absent from the sheet are skipped; those present must all map."""
    frame = _frame()
    expected = {key for col, key in EIVE_TRAIT_MAP.items() if col in frame.columns}
    records = parse_eive_frame(frame)
    keys = {r.trait_key for r in records if r.name == "Achillea millefolium"}
    assert keys == expected
    assert len(expected) == 5, "fixture covers the five indicator columns"


def test_parse_keeps_values_on_the_native_zero_to_ten_scale() -> None:
    records = parse_eive_frame(_frame())
    light = next(
        r for r in records if r.name == "Achillea millefolium" and r.trait_key == "ellenberg_l"
    )
    assert light.value == pytest.approx(7.0)


def test_parse_skips_non_species_ranks() -> None:
    names = {r.name for r in parse_eive_frame(_frame())}
    assert "Bad taxon" not in names


def test_parse_skips_missing_values_rather_than_writing_zero() -> None:
    frame = _frame()
    frame.loc[0, "EIVEres-L"] = None
    records = parse_eive_frame(frame)
    assert not [
        r for r in records if r.name == "Achillea millefolium" and r.trait_key == "ellenberg_l"
    ]


def test_parse_reads_the_niche_width_columns() -> None:
    """Fit scoring is meaningless without them — they must survive the parse."""
    frame = _frame()
    frame["EIVEres-L.nw3"] = [4.93, 2.10, 1.0]
    records = parse_eive_frame(frame)
    width = next(
        r for r in records if r.name == "Achillea millefolium" and r.trait_key == "ellenberg_l_nw"
    )
    assert width.value == pytest.approx(4.93)


def test_every_indicator_axis_has_a_matching_width_key() -> None:
    """A value without its width would silently fall back to the population median."""
    for column, key in EIVE_TRAIT_MAP.items():
        if not column.endswith(".nw3"):
            assert f"{key}_nw" in EIVE_TRAIT_MAP.values(), f"{key} has no width counterpart"
