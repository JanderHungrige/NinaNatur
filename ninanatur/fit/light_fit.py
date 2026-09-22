"""Which way a spot's light is wrong for a species — one rule for both questions.

What the suggestions leave out (`api.filters.light_verdict`) and what the sun
map warns about once it is planted (`garden.misplaced`) are the same question
asked at two moments. Until 2026-09-21 they had two answers: the list judged by
the species' niche width, the warning by a fixed distance. With full sun at 9.0
on EIVE's scale, the list offered wide-niche shrubs for an open bed and the
map then said they stood too bright. One rule, here: the two differ now only in
where they read the light (a bed's average, a cluster's cell).

*Unsuitable* is more than 1.5 niche half-widths away (`03-niche-fit`);
borderline is not a mismatch.
"""
from __future__ import annotations

from typing import Literal

from ninanatur.fit.score import FitBand, FitResult, SiteVector, SpeciesNiche, score_species

#: Which way the light is wrong for a species: it wants less, or more.
LightMismatch = Literal["too_bright", "too_dark"]


def light_mismatch(fit: FitResult) -> LightMismatch | None:
    """Which way the light is wrong for a species, when it is *unsuitable*.

    None when it suits, when it is merely borderline, and when it cannot be
    judged: a species with no L value, or a site whose light was never computed.
    Unknown is not a mismatch.
    """
    axis = fit.explanation.get("ellenberg_l")
    if axis is None or axis.band is not FitBand.UNSUITABLE:
        return None
    return "too_bright" if axis.value < axis.target else "too_dark"


def light_mismatch_at(spot: float, wants: float, width: float | None) -> LightMismatch | None:
    """The same verdict for one spot's light value and one species' L and width.

    A missing width takes EIVE's median, as it does in the list.
    """
    fit = score_species(
        SiteVector({"ellenberg_l": spot}),
        SpeciesNiche(0, {"ellenberg_l": wants}, {"ellenberg_l": width}),
    )
    return light_mismatch(fit)


__all__ = ["LightMismatch", "light_mismatch", "light_mismatch_at"]
