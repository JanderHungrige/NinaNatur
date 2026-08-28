"""Native or introduced — the claim the landing page has been making unbacked.

Every fixture below is a real GBIF response shape, checked before the parser was
written. The unstructured form is where the invasive species live, because they
are the ones with sprawling introduced ranges.
"""
import pytest

from ninanatur.ingest.sources.nativeness import (
    Establishment,
    parse_german_establishment,
)


def _structured(locality: str, means: str | None) -> list[dict[str, object]]:
    return [{"locality": locality, "establishmentMeans": means}]


# --- the clean shape -------------------------------------------------------

def test_a_structured_native_entry_is_read_directly() -> None:
    # Achillea millefolium
    assert parse_german_establishment(_structured("Germany", "NATIVE")) is Establishment.NATIVE


def test_a_structured_introduced_entry_is_read_directly() -> None:
    # Tsuga canadensis
    assert (
        parse_german_establishment(_structured("Germany", "INTRODUCED"))
        is Establishment.INTRODUCED
    )


def test_other_countries_are_ignored() -> None:
    entries = _structured("Krym", "NATIVE") + _structured("Jiangxi", "INTRODUCED")
    assert parse_german_establishment(entries) is Establishment.UNKNOWN


# --- the wall-of-text shape ------------------------------------------------

SALIX = (
    "England (England, Wales); Ireland; Denmark; Netherlands; Belgium; Luxembourg; "
    "Germany (Brandenburg, Berlin, Baden-Württemberg, Bayern, Hessen); Switzerland; "
    "Austria; Poland; USA [I] (Alabama [I], Connecticut [I]); Argentina [I]"
)
IMPATIENS = (
    "England [I] (England [I], Wales [I]); Denmark [I]; Netherlands [I]; Belgium [I]; "
    "Luxembourg [I]; Germany [I]; Switzerland [I]; Austria [I]; Pakistan; Nepal"
)


def test_an_unmarked_germany_in_a_long_string_is_native() -> None:
    """Salix caprea — native here, introduced in the Americas."""
    assert parse_german_establishment(_structured(SALIX, None)) is Establishment.NATIVE


def test_a_marked_germany_in_a_long_string_is_introduced() -> None:
    """Impatiens glandulifera — the invasive the product should steer away from."""
    assert parse_german_establishment(_structured(IMPATIENS, None)) is Establishment.INTRODUCED


def test_a_later_countrys_marker_does_not_bleed_onto_germany() -> None:
    """'Germany; ... USA [I]' must stay native — the marker binds to its own segment."""
    assert parse_german_establishment(_structured(SALIX, None)) is Establishment.NATIVE


def test_region_detail_in_parentheses_is_not_mistaken_for_a_marker() -> None:
    entries = _structured("Germany (Bayern, Hessen, Sachsen); France", None)
    assert parse_german_establishment(entries) is Establishment.NATIVE


def test_a_marker_after_region_detail_is_still_found() -> None:
    entries = _structured("Germany (Bayern) [I]; France", None)
    assert parse_german_establishment(entries) is Establishment.INTRODUCED


# --- absence ---------------------------------------------------------------

def test_no_german_entry_at_all_is_unknown_not_native() -> None:
    """A gap in the data is not evidence of belonging here."""
    assert parse_german_establishment(_structured("Japan; Korea", None)) is Establishment.UNKNOWN
    assert parse_german_establishment([]) is Establishment.UNKNOWN


def test_germania_does_not_count_as_germany() -> None:
    """Substring matching would quietly mislabel unrelated localities."""
    entries = _structured("Germaniella Reserve", None)
    assert parse_german_establishment(entries) is Establishment.UNKNOWN


@pytest.mark.parametrize("means", ["native", "Native", "NATIVE"])
def test_establishment_means_is_case_insensitive(means: str) -> None:
    assert parse_german_establishment(_structured("Germany", means)) is Establishment.NATIVE


def test_the_structured_value_wins_over_the_string(
) -> None:
    """When GBIF says INTRODUCED outright, an unmarked string must not override it."""
    entries = [{"locality": "Germany", "establishmentMeans": "INTRODUCED"}]
    assert parse_german_establishment(entries) is Establishment.INTRODUCED
