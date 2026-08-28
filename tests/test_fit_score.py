"""Fit scoring — the function that decides whether suggestions feel considered.

The properties asserted here are the ones the feature doc commits to, not the
arithmetic. If the formula changes but these still hold, the behaviour is intact.
"""
import pytest

from ninanatur.fit.score import (
    AXES,
    FitBand,
    SiteVector,
    SpeciesNiche,
    axis_score,
    score_species,
)


def _species(**kw: float) -> SpeciesNiche:
    """A species at the given optima, all with a median-ish niche width."""
    values = {a: kw.get(a) for a in AXES}
    widths = {a: kw.get(f"{a}_nw", 3.0) for a in AXES}
    return SpeciesNiche(taxon_id=1, values=values, widths=widths)


# --- the axis kernel -------------------------------------------------------

def test_axis_score_is_one_at_the_optimum() -> None:
    assert axis_score(target=7.0, value=7.0, width=3.0) == pytest.approx(1.0)


def test_axis_score_decays_with_distance() -> None:
    near = axis_score(target=7.0, value=6.5, width=3.0)
    far = axis_score(target=7.0, value=4.0, width=3.0)
    assert 1.0 > near > far > 0.0


def test_a_wider_niche_tolerates_the_same_distance_better() -> None:
    """The whole reason for using niche width instead of a fixed band."""
    generalist = axis_score(target=7.0, value=5.0, width=8.0)
    specialist = axis_score(target=7.0, value=5.0, width=1.0)
    assert generalist > specialist


# --- the ranking property the wave doc commits to --------------------------

def test_an_exact_match_outranks_a_generalist_at_a_distance() -> None:
    """A wide niche buys breadth, never rank — no cap needed if this holds."""
    site = SiteVector(values={"ellenberg_l": 7.0, "ellenberg_m": 4.0, "ellenberg_n": 5.0})
    exact = _species(ellenberg_l=7.0, ellenberg_m=4.0, ellenberg_n=5.0, ellenberg_l_nw=1.0)
    generalist = _species(
        ellenberg_l=4.0, ellenberg_m=7.0, ellenberg_n=2.0,
        ellenberg_l_nw=10.0, ellenberg_m_nw=10.0, ellenberg_n_nw=10.0,
    )
    assert score_species(site, exact).score > score_species(site, generalist).score


def test_one_hopeless_axis_sinks_the_whole_score() -> None:
    """Geometric mean: good soil cannot compensate for the wrong light."""
    site = SiteVector(values={"ellenberg_l": 8.0, "ellenberg_m": 5.0, "ellenberg_n": 5.0})
    balanced = _species(ellenberg_l=7.0, ellenberg_m=5.5, ellenberg_n=5.5)
    lopsided = _species(ellenberg_l=1.0, ellenberg_m=5.0, ellenberg_n=5.0)
    assert score_species(site, balanced).score > score_species(site, lopsided).score
    assert score_species(site, lopsided).score < 0.1


# --- missing data must not be misread as a bad match -----------------------

def test_a_missing_axis_is_skipped_not_scored_zero() -> None:
    site = SiteVector(values={"ellenberg_l": 7.0, "ellenberg_m": 4.0})
    complete = _species(ellenberg_l=7.0, ellenberg_m=4.0)
    partial = _species(ellenberg_l=7.0)  # no moisture value at all
    result = score_species(site, partial)
    assert result is not None and result.score == pytest.approx(1.0)
    assert result.axes_scored == ("ellenberg_l",)
    assert score_species(site, complete).axes_scored == ("ellenberg_l", "ellenberg_m")


def test_a_species_with_no_usable_axis_scores_none_not_zero() -> None:
    """'Unknown fit' and 'bad fit' are different answers."""
    site = SiteVector(values={"ellenberg_l": 7.0})
    assert score_species(site, _species()).score is None


def test_missing_niche_width_falls_back_and_says_so() -> None:
    site = SiteVector(values={"ellenberg_l": 7.0})
    species = SpeciesNiche(taxon_id=2, values={"ellenberg_l": 6.0}, widths={})
    result = score_species(site, species)
    assert result.score is not None
    assert result.explanation["ellenberg_l"].width_estimated is True


# --- the explanation Wave 4 depends on -------------------------------------

def test_explanation_names_a_band_per_axis() -> None:
    site = SiteVector(values={"ellenberg_l": 7.0, "ellenberg_m": 4.0})
    species = _species(ellenberg_l=7.0, ellenberg_m=1.0, ellenberg_m_nw=2.0)
    ex = score_species(site, species).explanation
    assert ex["ellenberg_l"].band is FitBand.OPTIMAL
    assert ex["ellenberg_m"].band is FitBand.UNSUITABLE


def test_bands_are_ordered_by_distance() -> None:
    """Values chosen well inside each band — boundaries are pinned separately."""
    site = SiteVector(values={"ellenberg_l": 5.0})
    def band_at(value: float) -> FitBand:
        species = _species(ellenberg_l=value, ellenberg_l_nw=4.0)
        return score_species(site, species).explanation["ellenberg_l"].band

    bands = [band_at(v) for v in (5.0, 6.5, 7.5, 10.0)]
    assert bands == [FitBand.OPTIMAL, FitBand.SUITABLE, FitBand.BORDERLINE, FitBand.UNSUITABLE]


@pytest.mark.parametrize(
    ("half_widths", "expected"),
    [
        (0.5, FitBand.OPTIMAL),      # edges are inclusive: the better band wins a tie
        (1.0, FitBand.SUITABLE),
        (1.5, FitBand.BORDERLINE),
        (1.5001, FitBand.UNSUITABLE),
    ],
)
def test_band_edges_are_inclusive(half_widths: float, expected: FitBand) -> None:
    """Pinned explicitly: a species exactly on an edge gets the kinder verdict."""
    width = 4.0
    site = SiteVector(values={"ellenberg_l": 5.0})
    species = _species(ellenberg_l=5.0 + half_widths * width / 2, ellenberg_l_nw=width)
    assert score_species(site, species).explanation["ellenberg_l"].band is expected
