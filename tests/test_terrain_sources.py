"""The registry's rules, not its current contents.

A test that names Saarland would pass for the wrong reason and would have to be
rewritten the day Saarland opens its data. What must hold is the *rule* that
kept Saarland out: nothing chargeable, nothing without attribution, nothing
whose axes or projection are guessed.
"""
from __future__ import annotations

from ninanatur.geo.terrain_sources import (
    AXES_EN,
    AXES_XY,
    TERRAIN_SOURCES,
    by_state,
)

#: Words that appear in an `AccessConstraints` that forbids this use. Saarland's
#: says "kostenpflichtig" for any embedding in another application, which is
#: exactly what this project does.
FORBIDDING = ("kostenpflichtig", "gebührenpflichtig", "non-commercial", "nc-")


def test_every_source_names_its_licence_and_its_credit() -> None:
    """The rule that keeps this project's licence position defensible: a height
    shown without its required credit is a height used outside its licence."""
    for source in TERRAIN_SOURCES:
        assert source.licence.strip(), source.state
        assert source.attribution.strip(), source.state


def test_no_source_charges_for_this_use() -> None:
    """The gate that excluded Saarland. Its service answers and every aggregator
    lists it as open; its own constraints say embedding it in another
    application costs money."""
    for source in TERRAIN_SOURCES:
        licence = source.licence.lower()
        for word in FORBIDDING:
            assert word not in licence, f"{source.state}: {source.licence}"


def test_every_source_says_which_axes_it_wants() -> None:
    """Not cosmetic. A SUBSET with the wrong axis name is a 404 rather than an
    error message, and both conventions are in use among these six."""
    for source in TERRAIN_SOURCES:
        assert source.axes in (AXES_XY, AXES_EN), source.state


def test_every_source_is_in_a_german_utm_zone() -> None:
    """25832 or 25833. A request sent in the wrong one does not fail — it lands
    a few hundred kilometres away and returns somebody else's ground."""
    for source in TERRAIN_SOURCES:
        assert source.epsg in (25832, 25833), source.state


def test_vertical_step_is_recorded_even_when_it_is_coarse() -> None:
    """Baden-Württemberg delivers whole metres where the DGM1 specification says
    0.01 m. That is not a reason to drop it — it is a reason to say so, and it
    can only be said if it is written down."""
    steps = {s.state: s.vertical_step_m for s in TERRAIN_SOURCES}
    assert all(v > 0 for v in steps.values())
    assert any(v >= 1.0 for v in steps.values()), (
        "a coarse entry existed when this was written; if all are fine now, "
        "check that the value is still being read from the service"
    )


def test_no_state_appears_twice() -> None:
    """Two entries for one state means `by_state` silently picks the first, and
    which one that is depends on the order somebody happened to type them in."""
    states = [s.state for s in TERRAIN_SOURCES]
    assert len(states) == len(set(states))


def test_a_state_without_a_service_is_an_answer() -> None:
    """The whole point of the registry. A gap stays a gap: no neighbour's data,
    no coarser federal substitute quietly swapped in."""
    assert by_state("Bayern") is None
    assert by_state("Freie Republik Erfundenien") is None


def test_lookup_does_not_care_about_case() -> None:
    assert by_state("nordrhein-westfalen") is not None
    assert by_state("NORDRHEIN-WESTFALEN") is not None
