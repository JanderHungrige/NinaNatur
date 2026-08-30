"""The object vocabulary, and the numbers it carries.

A dropdown that only decorates is a form field asking the user to do our
bookkeeping. Each kind here brings what it takes to be that kind: a shape, a
size, whether it stands up, and how it is drawn.
"""
import pytest

from ninanatur.garden.objects import TRAITS, ObjectKind, default_height


def test_each_kind_that_stands_up_carries_a_starting_height() -> None:
    for kind in ObjectKind:
        if TRAITS[kind].casts_shadow and kind is not ObjectKind.OTHER:
            assert default_height(kind) is not None, f"{kind.value} has no default"


def test_other_has_no_default_because_it_claims_nothing() -> None:
    # "Sonstiges" is the absence of a category; inventing 3 m for it would be a
    # number the user never gave and cannot see the reason for.
    assert default_height(ObjectKind.OTHER) is None


def test_a_surface_has_no_height_either() -> None:
    assert default_height(ObjectKind.PAVING) is None


def test_a_tree_starts_taller_than_a_fence() -> None:
    tree = default_height(ObjectKind.TREE)
    fence = default_height(ObjectKind.FENCE)
    assert tree is not None and fence is not None and tree > fence


def test_the_table_covers_the_enum_exactly() -> None:
    """A kind missing from the table would raise on first use, and a stale entry
    would describe a kind nobody can choose."""
    assert set(TRAITS) == set(ObjectKind)


def test_kinds_round_trip_through_their_stored_value() -> None:
    # They are stored as text; a renamed member would orphan every saved row.
    for kind in ObjectKind:
        assert ObjectKind(kind.value) is kind


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ValueError):
        ObjectKind("hedgehog")


# --- Wave 10: a kind says what it is ---------------------------------------

def test_the_vocabulary_covers_what_a_garden_contains() -> None:
    from ninanatur.garden.objects import ObjectKind

    named = {k.value for k in ObjectKind}
    assert {"house", "shed", "wall", "fence", "hedge", "tree", "shrub",
            "bed", "lawn", "paving", "gravel", "pond", "path", "other"} <= named


def test_a_house_defaults_to_a_rectangle_and_a_tree_to_a_circle() -> None:
    """A crown is the one thing a circle actually fits."""
    from ninanatur.garden.footprint import Shape
    from ninanatur.garden.objects import ObjectKind, default_shape

    assert default_shape(ObjectKind.HOUSE) is Shape.RECT
    assert default_shape(ObjectKind.TREE) is Shape.CIRCLE


def test_a_hedge_defaults_to_a_strip_rather_than_a_square() -> None:
    from ninanatur.garden.objects import ObjectKind, default_size

    width, depth = default_size(ObjectKind.HEDGE)
    assert depth is not None
    assert width > depth * 3


def test_surfaces_do_not_cast_shadows() -> None:
    # Paving does not shade a bed, and a model that said it did would darken
    # every terrace in the country.
    from ninanatur.garden.objects import ObjectKind, casts_shadow

    for kind in (ObjectKind.PAVING, ObjectKind.GRAVEL, ObjectKind.LAWN,
                 ObjectKind.POND, ObjectKind.PATH, ObjectKind.BED):
        assert casts_shadow(kind) is False, kind.value


def test_things_that_stand_up_do_cast_shadows() -> None:
    from ninanatur.garden.objects import ObjectKind, casts_shadow

    for kind in (ObjectKind.HOUSE, ObjectKind.SHED, ObjectKind.WALL,
                 ObjectKind.FENCE, ObjectKind.HEDGE, ObjectKind.TREE,
                 ObjectKind.SHRUB):
        assert casts_shadow(kind) is True, kind.value


def test_a_surface_is_drawn_underneath() -> None:
    """A lawn under a shed, not over it. Drawing order is a property of the
    kind, not of the order somebody happened to click."""
    from ninanatur.garden.objects import ObjectKind, is_surface

    assert is_surface(ObjectKind.LAWN) is True
    assert is_surface(ObjectKind.SHED) is False


def test_every_kind_has_a_shape_a_size_and_a_symbol() -> None:
    # A kind missing one of these would silently fall back to something, and a
    # silent fallback in a vocabulary is how "other" quietly becomes the default.
    from ninanatur.garden.objects import ObjectKind, default_shape, default_size, symbol_of

    for kind in ObjectKind:
        assert default_shape(kind) is not None, kind.value
        assert default_size(kind)[0] > 0, kind.value
        assert symbol_of(kind), kind.value


def test_a_surface_that_is_given_a_height_still_casts_nothing() -> None:
    # The user may be describing a raised gravel bed. Accepted and ignored
    # rather than refused — the shadow model has nothing to do with it either way.
    from ninanatur.garden.objects import ObjectKind, casts_shadow

    assert casts_shadow(ObjectKind.GRAVEL) is False
