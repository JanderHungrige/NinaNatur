"""What a suggestion list is ordered by: how well a plant grows here, then what it feeds.

The owner, 2026-09-21: "Die vorgeschlagenen Pflanzen sollten nach besten
Wachstumsbedingungen + Insektenwert gerankt werden." Two things to weigh, and
one rule for weighing them: **a plant that clearly grows worse here must not
climb over one that grows well merely because more insects visit it — and
among plants that grow equally well, the insects decide.**

    rank = growing × (1 + INSECT_WEIGHT × insect)

**Growing conditions** are `score_species`'s own fit — the geometric mean over
light and soil (L, M, N, R), each axis scored against the species' EIVE niche
width, an unknown axis at the neutral middle — with one change: an axis inside
the *optimal* band (within half a half-width, `BAND_EDGES[0]`) counts as
perfect. Inside that band EIVE cannot tell two species apart: a niche position
is a consensus of several national systems (Dengler et al. 2023), and ordering
0.99 above 0.93 would be ordering noise. So `growing` is 1.0 exactly when
every axis is optimal, the band the list's badge calls "optimal".

**Insect value** is the German insect partner count (`partner_totals.german`)
on a log scale, 0 for none and 1 for the catalogue's most visited plant
(*Salix caprea*, 1,055): the tenth partner means more than the thousandth, and
a straight count would let two willows decide every list.

**Why 0.1.** Among plants optimal everywhere `growing` is 1.0 for all, so the
insect value alone orders them, whatever the weight. The weight only says how
far below that a plant rich in insects may climb, and 0.1 puts the limit on a
band edge. A plant optimal on three axes whose fourth is `z` half-widths away
has growing = exp(−(z² − 0.25)/8); with the catalogue's top partner count it
passes an all-optimal plant with no partners only while that stays above
1/1.1, which is z < 1.006 — the end of *suitable*. So:

- A plant whose light or soil is *borderline* never outranks one optimal
  everywhere, however many insects it feeds.
- Against an all-optimal plant with a typical count (67 partners, the
  catalogue's median, insect 0.60), it takes the top count *and* z < 0.74.

Measured on the real catalogue, loam and fresh soil (doc 13): the deep-shade
list (1 h) is led by woodland herbs at L 2.3–4.4 with 100–200 partners where
it was led by the best fits alone, and the full-sun list by meadow plants with
several hundred.
"""
from __future__ import annotations

import math

from ninanatur.fit.score import BAND_EDGES, UNKNOWN_AXIS_SCORE, FitResult

#: An axis scoring this or more is inside the *optimal* band and counts as
#: perfect: exp(−½ × 0.5²) ≈ 0.8825.
OPTIMAL_AXIS_SCORE = math.exp(-0.5 * BAND_EDGES[0] ** 2)

#: How much the insect value can add, as a share of the growing conditions.
#: See the module docstring for why it is this and not more.
INSECT_WEIGHT = 0.1


def _capped(score: float) -> float:
    """One axis, with the optimal band counted as perfect."""
    return min(1.0, max(score, 1e-12) / OPTIMAL_AXIS_SCORE)


def growing_conditions(fit: FitResult, requested: int) -> float:
    """How well a plant grows here, 0–1: `score_species`'s geometric mean over
    the `requested` axes, with every optimal axis counted as perfect.

    An axis the species has no value for keeps `score_species`'s neutral
    middle, so a poorly documented species cannot reach 1.0 on what nobody
    recorded. 0.0 when there was nothing to score.
    """
    if requested <= 0 or fit.score is None:
        return 0.0
    logs = sum(math.log(_capped(axis.score)) for axis in fit.explanation.values())
    logs += (requested - len(fit.explanation)) * math.log(_capped(UNKNOWN_AXIS_SCORE))
    return math.exp(logs / requested)


def insect_value(partners: int | None, most: int) -> float:
    """German insect partners on a log scale, 0 for none, 1 for `most`.

    None (GloBI holds no relations at all) and 0 both give 0: an unrecorded
    value is no reason to rank a plant up, and it is not a penalty either —
    the plant simply competes on its growing conditions.
    """
    if not partners or most <= 0:
        return 0.0
    return min(1.0, math.log1p(partners) / math.log1p(most))


def suggestion_rank(growing: float, insect: float) -> float:
    """The combined order: growing conditions, lifted by at most `INSECT_WEIGHT`."""
    return growing * (1.0 + INSECT_WEIGHT * insect)


__all__ = [
    "INSECT_WEIGHT",
    "OPTIMAL_AXIS_SCORE",
    "growing_conditions",
    "insect_value",
    "suggestion_rank",
]
