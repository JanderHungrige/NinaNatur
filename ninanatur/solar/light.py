"""From sun hours to a bed's light value.

Samples the sun across the growing season, asks the shading model whether each
sample reaches the bed, and converts the resulting daily average into an
Ellenberg light value.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle, Point

# March to October. A plant's light experience in December does not decide where
# it can live, and including winter would drag every German garden into shade.
SEASON_START = (3, 1)
SEASON_END = (10, 31)

# Every fifth day, every ten minutes; a month every second day. Until Wave 26 it
# was every tenth day and every half hour, a month every fifth, with the claim
# "fine enough that the answer stops moving" — measured, it was 0.22 h low over
# the season and 0.46 h in an April month, mostly from the days skipped
# (doc 115). These are the steps its convergence suite asks for, within 0.04 h
# and 0.10 h of an answer that has stopped moving, and the raster pays for
# them (doc 117).
DAY_STEP = 5
MINUTE_STEP = 10
MONTH_DAY_STEP = 2

#: Which light model computed a map. It enters every map's signature, so a map
#: an older model drew reads stale instead of showing its answer under a new
#: date, and the page names it (Wave 26: "every model change bumps a
#: MODEL_VERSION"). Raise it with every change to what the model answers:
#:
#: - "" — before Wave 26: every 10th day, every half hour, the sun from 5°.
#: - "26.2" — every 5th day, every 10 minutes, a month every 2nd day, the sun
#:   from 3°, concave shadows exact (docs 115–117).
#: - "26.3" — the sky: each cell's sky-view factor, relative illuminance in the
#:   garden's DWD climate, and the sunshine to expect; the light value never
#:   brighter than Ellenberg's classes say of the sky in leaf (doc 118). The
#:   hours are 26.2's.
MODEL_VERSION = "26.3"

# Mean daily direct sun (hours) -> light value on EIVE's own 0–10 scale, as
# anchors joined by straight lines, darkest first.
#
# THIS IS A CONVENTION, NOT A MEASUREMENT. Sun hours are physical; an indicator
# value is ecological, read from where plants are found growing. It is a table
# so it can be argued with and adjusted in one place, and so nobody mistakes it
# for physics. It decides what a bed is too bright *and* too dark for
# (`api.filters.light_verdict`), against species values on EIVE's 0–10 scale.
#
# Until 2026-09-21 it was a staircase of classic-looking Ellenberg rungs (3–8)
# compared with EIVE values, which squeezed every bed towards the middle: full
# sun read as classic 7.4, deep shade as 3.4. EIVE scaled each source system
# linearly onto 0–10 (Dengler et al. 2023, Methods), which for Ellenberg's 1–9
# is (L − 1) × 1.25. Each anchor below is the old rung at its old threshold
# carried through that rescale, so what changed is the scale and the steps,
# not the judgement: 3 → 2.5, 4 → 3.75, 5 → 5.0, 6 → 6.25, 7 → 7.5.
#
# - **Lines, not steps.** 3.99 h and 4.01 h are the same place; a step made
#   them a whole class apart, and a species could fall out of a list over it.
# - **Anchored at the lower edges,** so every value leans a little bright of
#   the middle of its old interval. Deliberate: the model counts direct sun
#   only, and a bed in the open with a wall to its south still sees most of
#   the sky — it is lighter than its hours say (`.mdd/plans/03-sonne-und-schatten-
#   genauer.md`, E2).
# - **8 h and above: 9.0,** between classic 8 (8.75) and 9 (10). A bed that
#   long in direct sun is open ground; the hours past eight are low sun at the
#   ends of the day and add little. EIVE's 9.5–10 is dunes and scree.
# - **0 h: 2.5, not lower.** Classic 1–2 is a closed forest floor; a bed with
#   no direct sun still has the sky.
#
# The words are the sun map's legend (`frontend/src/components/SunMap.tsx`,
# `BANDS`), whose steps begin at these hours; `tests/test_light_legend.py`
# holds the two together. Changing the anchors changes what every stored bed
# value means: `ingest/light_scale.py` carries them across from the stored hours.
SUN_HOUR_ANCHORS: tuple[tuple[float, float], ...] = (
    (0.0, 2.5),   # tiefer Schatten — classic 3
    (1.5, 3.75),  # Schatten — classic 4
    (2.5, 5.0),   # Halbschatten — classic 5
    (4.0, 6.25),  # sonnig — classic 6
    (6.0, 7.5),   # volle Sonne — classic 7
    (8.0, 9.0),   # open ground — between classic 8 and 9
)


# Ellenberg's own measure (doc 118): relative illuminance under an overcast
# sky in full leaf — which is what a cell's sky-view factor with the crowns in
# leaf is. His classes by their thresholds, as the plan quotes them, carried
# onto EIVE's scale the way the hours' anchors are ((L − 1) × 1.25), and flat
# at the hours' top: open ground is 9.0 by either measure.
#
# Not a second convention beside the hours but a floor under them, by the
# owner's decision of 2026-09-22 (`light_value`). His thresholds come from
# forest floors, and a garden rarely sees less than a fifth of its sky outside
# a dense crown: read alone, they put nearly every garden spot at L 9 and gave
# a bed with four hours of sun the open lawn's list. As a floor they change
# nothing where 42 % of the sky or more is seen, and under a dense beech —
# whose bare months the hours count as sun — they say what it is.
#
# **Not below 2.5, as the hours are not.** Classic 1–2 is a closed forest
# floor. And inside a tree, shrub or hedge the gardener drew — which the model
# still casts as opaque, until crowns are crowns (Wave 26, feature 6) — the
# sky reads 0: with classes 1 and 2 kept, every bed there fell from 2.5 to 0.0
# (review, 2026-09-22).
SKY_ANCHORS: tuple[tuple[float, float], ...] = (
    (0.05, 2.5),    # classic 3 — mostly below 5 %; the hours' floor too
    (0.075, 3.75),  # classic 4
    (0.10, 5.0),    # classic 5 — mostly above 10 %
    (0.20, 6.25),   # classic 6 — rarely below 20 %
    (0.30, 7.5),    # classic 7 — down to about 30 %
    (0.40, 8.75),   # classic 8 — rarely below 40 %
    (0.42, 9.0),    # the hours' top, on the way to classic 9 at 50 %
)


@dataclass(frozen=True)
class BedLight:
    """A bed's light value, with the evidence that produced it."""

    ellenberg_l: float
    sun_hours: float
    samples: int
    year: int
    #: The share of the sky it sees with the crowns in leaf (doc 118).
    sky_view: float = 1.0


def _on_lines(x: float, anchors: tuple[tuple[float, float], ...]) -> float:
    """Straight lines between the anchors, flat beyond both ends, rounded to
    two places — already finer than the model knows."""
    first_x, first_value = anchors[0]
    if x <= first_x:
        return first_value
    for (x0, l0), (x1, l1) in zip(anchors, anchors[1:], strict=False):
        if x <= x1:
            return round(l0 + (l1 - l0) * (x - x0) / (x1 - x0), 2)
    return anchors[-1][1]


def ellenberg_from_sky(sky: float) -> float:
    """Ellenberg's classes on EIVE's scale from the share of the sky seen in
    leaf (`SKY_ANCHORS`)."""
    return _on_lines(sky, SKY_ANCHORS)


def light_value(sun_hours: float, sky: float | None) -> float:
    """The light value a bed is matched by (owner, 2026-09-22): the hours'
    convention, never brighter than Ellenberg's classes say of the sky it
    sees in leaf. Without a sky — a bed computed before the sky counted — the
    hours alone. The one rule for a bed, a cell and a point."""
    by_hours = ellenberg_from_sun_hours(sun_hours)
    return by_hours if sky is None else min(by_hours, ellenberg_from_sky(sky))


def ellenberg_from_sun_hours(sun_hours: float) -> float:
    """Apply the documented convention: EIVE 0–10 from mean daily sun hours.

    Straight lines between `SUN_HOUR_ANCHORS`, flat beyond both ends. Rounded
    to two places, which is already finer than the model knows.
    """
    return _on_lines(sun_hours, SUN_HOUR_ANCHORS)


def season_days(year: int, month: int | None = None) -> list[datetime]:
    """The days a light answer is averaged over.

    March to October by default — a plant's whole growing season, which is what
    decides where it can live. `month` narrows it to one, because *where does
    the sun reach in April* and *where does it reach in July* are different
    questions in a garden with a house on its south side, and the season average
    answers neither on its own.
    """
    if month is not None:
        start = datetime(year, month, 1, tzinfo=UTC)
        end = start.replace(day=28) + timedelta(days=4)
        end = end.replace(day=1) - timedelta(days=1)
        step = MONTH_DAY_STEP
    else:
        start = datetime(year, *SEASON_START, tzinfo=UTC)
        end = datetime(year, *SEASON_END, tzinfo=UTC)
        step = DAY_STEP
    days: list[datetime] = []
    day = start
    while day <= end:
        days.append(day)
        day += timedelta(days=step)
    return days


def bed_light_value(
    location: Location,
    bed: Point,
    obstacles: list[Obstacle],
    year: int = 2026,
    height_above_ground: float = 0.0,
) -> BedLight:
    """Mean daily hours of direct sun on a bed, the sky it sees, and the light
    value they imply (`light_value`).

    Returns the sun hours alongside the value: a bare number the user cannot
    trace back to their own obstacles is not explainable, and this one will
    surprise people.

    A crown passes what it passes, as it does on the map: until Wave 26 this
    point path counted any shadow as a wall, trees included, and a raised bed
    under an apple tree read darker than the ground beside it.
    """
    # The raster's point path, every moment at once (doc 117). It imports
    # this module's sampling, so it is imported here rather than at the top.
    from ninanatur.solar.raster import moments_for, parts_of, point_hours, point_sums
    from ninanatur.solar.relative import LEAF_MONTH
    from ninanatur.solar.sky import sky_directions

    moments = moments_for(location, year)
    parts = parts_of(obstacles)
    before, after = point_hours(parts, moments, bed.x, bed.y, height_above_ground)
    sky = float(point_sums(parts, sky_directions(LEAF_MONTH), bed.x, bed.y,
                           height_above_ground)[0])
    # The value from the hours and the sky as stored, so they always agree: on
    # lines rather than steps, a rounding of either moves the value too.
    sun_hours, sky_view = round(before + after, 2), round(sky, 3)
    return BedLight(
        ellenberg_l=light_value(sun_hours, sky_view),
        sun_hours=sun_hours,
        samples=moments.days * (24 * 60 // MINUTE_STEP),
        year=year,
        sky_view=sky_view,
    )
