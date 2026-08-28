"""How well a species fits a bed.

Uses the niche width EIVE ships alongside each indicator value rather than one
tolerance band applied to every species: the same absolute distance means
something different for a generalist than for a fussy species.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

AXES: tuple[str, ...] = (
    "ellenberg_l",
    "ellenberg_m",
    "ellenberg_n",
    "ellenberg_r",
    "ellenberg_t",
)

# Population medians from EIVE 1.0, used when a species has a value but no width.
# Refusing to score would discard otherwise usable species.
MEDIAN_WIDTH: dict[str, float] = {
    "ellenberg_l": 3.03,
    "ellenberg_m": 2.83,
    "ellenberg_n": 3.46,
    "ellenberg_r": 3.10,
    "ellenberg_t": 2.90,
}

# Band edges in half-niche-widths.
BAND_EDGES: tuple[float, float, float] = (0.5, 1.0, 1.5)


class FitBand(Enum):
    """Human-facing verdict per axis — Wave 4 renders these, not the number."""

    OPTIMAL = "optimal"
    SUITABLE = "suitable"
    BORDERLINE = "borderline"
    UNSUITABLE = "unsuitable"


@dataclass(frozen=True)
class SiteVector:
    """A bed's target conditions. Axes the bed does not specify are ignored."""

    values: dict[str, float]


@dataclass(frozen=True)
class SpeciesNiche:
    """A species' optimum and tolerance per axis, as ingested from EIVE."""

    taxon_id: int
    values: dict[str, float | None]
    widths: dict[str, float | None] = field(default_factory=dict)


@dataclass(frozen=True)
class AxisFit:
    """Why an axis scored what it did."""

    axis: str
    target: float
    value: float
    width: float
    half_widths_away: float
    score: float
    band: FitBand
    width_estimated: bool


@dataclass(frozen=True)
class FitResult:
    """A species' fit, with the reasoning kept attached to the number."""

    taxon_id: int
    score: float | None
    axes_scored: tuple[str, ...]
    explanation: dict[str, AxisFit]


def axis_score(target: float, value: float, width: float) -> float:
    """Score one axis: 1.0 at the optimum, decaying with distance in half-widths.

    Dividing the distance by the niche width is the entire point of this
    function — it is what separates a generalist from a specialist.
    """
    half = max(width, 1e-6) / 2.0
    z = abs(target - value) / half
    return math.exp(-0.5 * z * z)


def _band(half_widths_away: float) -> FitBand:
    optimal, suitable, borderline = BAND_EDGES
    if half_widths_away <= optimal:
        return FitBand.OPTIMAL
    if half_widths_away <= suitable:
        return FitBand.SUITABLE
    if half_widths_away <= borderline:
        return FitBand.BORDERLINE
    return FitBand.UNSUITABLE


def _axis_fit(axis: str, target: float, value: float, raw_width: float | None) -> AxisFit:
    estimated = raw_width is None or raw_width <= 0
    width = MEDIAN_WIDTH.get(axis, 3.0) if estimated else float(raw_width or 0.0)
    z = abs(target - value) / (max(width, 1e-6) / 2.0)
    return AxisFit(
        axis=axis,
        target=target,
        value=value,
        width=width,
        half_widths_away=z,
        score=math.exp(-0.5 * z * z),
        band=_band(z),
        width_estimated=estimated,
    )


def score_species(site: SiteVector, species: SpeciesNiche) -> FitResult:
    """Combine the per-axis fits into one score, with the reasoning preserved.

    Axes combine as a **geometric** mean: a species cannot offset hopeless light
    with excellent moisture, and an arithmetic mean would let it. Axes the bed
    does not specify, or the species has no value for, are skipped rather than
    scored zero — absent data is not a bad match.

    Returns `score=None` when no axis could be scored at all. "Unknown fit" and
    "bad fit" are different answers and must not render the same.
    """
    explanation: dict[str, AxisFit] = {}
    for axis, target in site.values.items():
        value = species.values.get(axis)
        if value is None:
            continue
        explanation[axis] = _axis_fit(axis, float(target), float(value), species.widths.get(axis))

    axes_scored = tuple(sorted(explanation))
    if not axes_scored:
        return FitResult(species.taxon_id, None, (), {})

    log_sum = sum(math.log(max(explanation[a].score, 1e-12)) for a in axes_scored)
    return FitResult(
        taxon_id=species.taxon_id,
        score=math.exp(log_sum / len(axes_scored)),
        axes_scored=axes_scored,
        explanation=explanation,
    )
