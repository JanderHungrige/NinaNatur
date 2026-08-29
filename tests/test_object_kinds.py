"""The object vocabulary, and the numbers it carries.

A dropdown that only decorates is a form field asking the user to do our
bookkeeping. Each kind here brings the height that makes it a thing.
"""
import pytest

from ninanatur.garden.objects import DEFAULT_HEIGHT_M, ObjectKind, default_height


def test_every_kind_a_gardener_would_name_is_there() -> None:
    named = {k.value for k in ObjectKind}
    assert {"tree", "hedge", "shrub", "building", "wall", "fence", "other"} <= named


def test_each_kind_carries_a_starting_height() -> None:
    for kind in ObjectKind:
        if kind is ObjectKind.OTHER:
            continue
        assert default_height(kind) is not None, f"{kind.value} has no default"


def test_other_has_no_default_because_it_claims_nothing() -> None:
    # "Sonstiges" is the absence of a category; inventing 3 m for it would be a
    # number the user never gave and cannot see the reason for.
    assert default_height(ObjectKind.OTHER) is None


def test_a_tree_starts_taller_than_a_fence() -> None:
    tree = default_height(ObjectKind.TREE)
    fence = default_height(ObjectKind.FENCE)
    assert tree is not None and fence is not None and tree > fence


def test_the_table_covers_the_enum_exactly() -> None:
    """A kind missing from the table would silently get no default, and a stale
    entry would be a height for a kind nobody can choose."""
    assert set(DEFAULT_HEIGHT_M) <= {k for k in ObjectKind}
    missing = {k for k in ObjectKind if k not in DEFAULT_HEIGHT_M} - {ObjectKind.OTHER}
    assert missing == set()


def test_kinds_round_trip_through_their_stored_value() -> None:
    # They are stored as text; a renamed member would orphan every saved row.
    for kind in ObjectKind:
        assert ObjectKind(kind.value) is kind


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ValueError):
        ObjectKind("hedgehog")
