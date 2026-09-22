"""The light value a bed is matched by — Wave 26, feature 3, part 2 (doc 118).

The owner's decision of 2026-09-22: the hours' convention, never brighter than
Ellenberg's thresholds say of the overcast sky in full leaf, which is how he
measured. Checked by what the rule must do: nothing in the open, his classes
where the sky is hidden, and the same answer wherever a value is given.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from ninanatur.solar.light import (
    SKY_ANCHORS,
    SUN_HOUR_ANCHORS,
    bed_light_value,
    ellenberg_from_sky,
    ellenberg_from_sun_hours,
    light_value,
)
from ninanatur.solar.position import Location
from ninanatur.solar.shading import Obstacle, Point

#: Every thousandth of the sky, and every tenth of an hour from none to fourteen.
SKIES = [s / 1000 for s in range(0, 1001)]
HOURS = [h / 10 for h in range(0, 141)]


def test_the_sky_mapping_rises_without_steps_and_is_flat_beyond_its_ends() -> None:
    values = [ellenberg_from_sky(s) for s in SKIES]
    assert values == sorted(values)
    assert values[0] == SKY_ANCHORS[0][1]
    # The top is the hours' top: open ground is 9.0 by either measure.
    assert values[-1] == SUN_HOUR_ANCHORS[-1][1]
    slopes = [(l1 - l0) / (s1 - s0)
              for (s0, l0), (s1, l1) in zip(SKY_ANCHORS, SKY_ANCHORS[1:], strict=False)]
    # No thousandth of the sky moves it by more than the steepest line does,
    # give or take the rounding to two places: lines, not steps.
    biggest = max(abs(b - a) for a, b in zip(values, values[1:], strict=False))
    assert biggest <= max(slopes) * 0.001 + 0.01 + 1e-9


@pytest.mark.parametrize(("share", "classic"),
                         [(0.05, 3), (0.075, 4), (0.10, 5), (0.20, 6), (0.30, 7), (0.40, 8)])
def test_ellenbergs_classes_sit_on_eives_scale_as_the_hours_anchors_do(share: float,
                                                                      classic: int) -> None:
    """Each class at its threshold, carried onto EIVE's 0–10 the way the
    hours' anchors are: (L − 1) × 1.25 (Dengler et al. 2023)."""
    assert ellenberg_from_sky(share) == pytest.approx(1.25 * (classic - 1))


def test_nothing_reads_below_the_hours_floor() -> None:
    """Classic 1–2 is a closed forest floor, and inside a tree or hedge drawn
    as opaque the sky reads 0: with those classes kept, every bed there fell
    from 2.5 to 0.0 (review, 2026-09-22)."""
    floor = SUN_HOUR_ANCHORS[0][1]
    assert ellenberg_from_sky(0.0) == ellenberg_from_sky(0.03) == floor == 2.5
    assert light_value(0.0, 0.0) == floor
    assert min(light_value(h, s) for h in HOURS for s in SKIES[::10]) == floor


def test_in_the_open_nothing_changes() -> None:
    """Where 42 % of the sky or more is seen — every open spot measured, walls
    and fences beside them included — the value is the hours' exactly."""
    for hours in HOURS:
        for sky in (0.42, 0.5, 0.66, 0.8, 1.0):
            assert light_value(hours, sky) == ellenberg_from_sun_hours(hours)


def test_the_value_is_the_lower_of_the_two_and_the_hours_without_a_sky() -> None:
    for hours in HOURS:
        assert light_value(hours, None) == ellenberg_from_sun_hours(hours)
        for sky in SKIES[::25]:
            assert light_value(hours, sky) == min(ellenberg_from_sun_hours(hours),
                                                  ellenberg_from_sky(sky))


def _beech(transmission: float) -> Obstacle:
    return Obstacle(footprint=[(5 * math.cos(a), 5 * math.sin(a))
                               for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)],
                    height=14.0, transmission=transmission, bare_transmission=0.75)


def test_under_a_dense_beech_the_value_is_the_woodland_floors() -> None:
    """Its bare months let the sun through, and the hours alone read it as
    half shade (doc 118): 5.2, meadow plants. In leaf it passes a twentieth
    of the sky, which Ellenberg's classes call deep shade."""
    light = bed_light_value(Location(51.25, 7.15), Point(0.0, 0.0), [_beech(0.05)])
    assert light.sky_view == pytest.approx(0.05, abs=0.005)
    assert light.ellenberg_l == light_value(light.sun_hours, light.sky_view)
    assert light.ellenberg_l < ellenberg_from_sun_hours(light.sun_hours) - 2


def test_in_the_open_the_one_point_answer_is_the_hours() -> None:
    light = bed_light_value(Location(51.25, 7.15), Point(0.0, 0.0), [])
    assert light.sky_view == pytest.approx(1.0)
    assert light.ellenberg_l == ellenberg_from_sun_hours(light.sun_hours)


def test_a_bed_under_a_dense_crown_is_stored_by_the_floor(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """What the list ranks by, as `recompute_light` stores it: below the hours'
    value where the sky is hidden (review, 2026-09-22 — the only stored beds
    tested saw more than 42 % of the sky, where the rule cannot bite)."""
    from ninanatur.garden import lighting
    from ninanatur.garden.elements import insert_element
    from ninanatur.garden.models import PLANTING_KIND
    from ninanatur.garden.store import create_garden, load_garden
    from ninanatur.ingest.db import connect, init_schema

    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
                   name="Beet", points=[[-2, -2], [2, -2], [2, 2], [-2, 2]],
                   soil_type="loam", moisture="fresh")
    conn.commit()
    monkeypatch.setattr(lighting, "shading_obstacles", lambda _c, _g: [_beech(0.05)])
    lighting.recompute_light(conn, garden_id)
    bed = load_garden(conn, garden_id).beds[0]
    assert bed.sun_hours is not None and bed.sky_view is not None and bed.sky_view < 0.1
    assert bed.ellenberg_l == light_value(bed.sun_hours, bed.sky_view)
    assert bed.ellenberg_l is not None
    assert bed.ellenberg_l < ellenberg_from_sun_hours(bed.sun_hours) - 2
