"""EIVE parsing: the 0-10 indicator scale and the header layout must be handled exactly."""
import pandas as pd
import pytest

from dbnatura.ingest.sources.eive import EIVE_TRAIT_MAP, parse_eive_frame


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


def test_parse_maps_every_eive_column_to_a_canonical_trait_key() -> None:
    records = parse_eive_frame(_frame())
    keys = {r.trait_key for r in records if r.name == "Achillea millefolium"}
    assert keys == set(EIVE_TRAIT_MAP.values())


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
