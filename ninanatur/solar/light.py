"""From sun hours to a bed's light value.

Samples the sun across the growing season, asks the shading model whether each
sample reaches the bed, and converts the resulting daily average into an
Ellenberg light value.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ninanatur.solar.position import Location, sun_position
from ninanatur.solar.shading import MIN_ALTITUDE, Obstacle, Point, is_shaded

# March to October. A plant's light experience in December does not decide where
# it can live, and including winter would drag every German garden into shade.
SEASON_START = (3, 1)
SEASON_END = (10, 31)

# One day every ten, sampled every half hour. Fine enough that the answer stops
# moving, coarse enough to stay well under a second per bed.
DAY_STEP = 10
MINUTE_STEP = 30

# A single month gets a finer step, because ten days would sample it three
# times. Six samples over four weeks, at a quarter of the season's cost.
MONTH_DAY_STEP = 5

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


@dataclass(frozen=True)
class BedLight:
    """A bed's light value, with the evidence that produced it."""

    ellenberg_l: float
    sun_hours: float
    samples: int
    year: int


def ellenberg_from_sun_hours(sun_hours: float) -> float:
    """Apply the documented convention: EIVE 0–10 from mean daily sun hours.

    Straight lines between `SUN_HOUR_ANCHORS`, flat beyond both ends. Rounded
    to two places, which is already finer than the model knows.
    """
    first_hours, first_value = SUN_HOUR_ANCHORS[0]
    if sun_hours <= first_hours:
        return first_value
    for (h0, l0), (h1, l1) in zip(SUN_HOUR_ANCHORS, SUN_HOUR_ANCHORS[1:], strict=False):
        if sun_hours <= h1:
            return round(l0 + (l1 - l0) * (sun_hours - h0) / (h1 - h0), 2)
    return SUN_HOUR_ANCHORS[-1][1]


def _season_days(year: int, month: int | None = None) -> list[datetime]:
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
    """Mean daily hours of direct sun on a bed, and the light value it implies.

    Returns the sun hours alongside the value: a bare number the user cannot
    trace back to their own obstacles is not explainable, and this one will
    surprise people.
    """
    days = _season_days(year)
    lit_minutes = 0
    samples = 0
    step = timedelta(minutes=MINUTE_STEP)

    for day in days:
        moment = day
        end_of_day = day + timedelta(days=1)
        while moment < end_of_day:
            samples += 1
            sun = sun_position(location, moment)
            if sun.altitude > MIN_ALTITUDE and not any(
                is_shaded(bed, obstacle, sun, height_above_ground)
                for obstacle in obstacles
            ):
                lit_minutes += MINUTE_STEP
            moment += step

    # The value from the hours as stored, so the two always agree: on lines
    # rather than steps, a rounding of the hours moves the value too.
    sun_hours = round((lit_minutes / 60) / len(days), 2) if days else 0.0
    return BedLight(
        ellenberg_l=ellenberg_from_sun_hours(sun_hours),
        sun_hours=sun_hours,
        samples=samples,
        year=year,
    )
