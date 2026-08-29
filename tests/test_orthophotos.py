"""The imagery registry, and the rule that it is a registry at all.

Feature 0 of Wave 8 asked the licence question before anything was built on
imagery. The answer was that it clears — per Bundesland, each with its own
service, licence and required credit — and that there is no federal source.
"""
from ninanatur.geo.orthophotos import ORTHOPHOTOS, by_state


def test_every_service_names_a_licence_and_a_credit() -> None:
    """DL-DE/BY-2.0 and CC-BY-4.0 both require the named credit. Imagery shown
    without it is imagery used outside its licence."""
    for entry in ORTHOPHOTOS:
        assert entry.licence.strip(), entry.state
        assert entry.attribution.strip(), entry.state
        assert entry.attribution.startswith("©"), entry.state


def test_every_service_is_https() -> None:
    for entry in ORTHOPHOTOS:
        assert entry.url.startswith("https://"), entry.state


def test_states_are_unique() -> None:
    states = [e.state for e in ORTHOPHOTOS]
    assert len(states) == len(set(states))


def test_a_state_without_a_service_is_absent_rather_than_borrowed() -> None:
    """A Bundesland that is not in the registry is not a gap to paper over with
    a neighbour's imagery — that would be using data outside its licence area."""
    assert by_state("Hessen") is None
    assert by_state("Nordrhein-Westfalen") is not None


def test_lookup_ignores_case() -> None:
    assert by_state("bayern") is not None
