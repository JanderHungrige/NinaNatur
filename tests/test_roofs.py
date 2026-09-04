"""A gable is not a box, and the model used to think it was."""
from __future__ import annotations

import pytest

from ninanatur.garden.roofs import (
    DEFAULT_EAVES_FRACTION,
    Roof,
    eaves_from_levels,
    shading_height,
)


def test_a_flat_roof_shades_with_its_whole_height() -> None:
    assert shading_height(12.0, Roof.FLAT) == 12.0


def test_an_unanswered_roof_behaves_exactly_as_before() -> None:
    """Nobody has said, so nothing changes. A default that quietly shortened
    every building would move every existing garden's light without anybody
    asking for it."""
    assert shading_height(12.0, Roof.UNKNOWN) == 12.0
    assert shading_height(12.0) == 12.0


def test_a_gable_shades_less_than_a_box_and_more_than_its_eaves() -> None:
    """The whole point. OSM's height is the ridge, and a ridge is a line."""
    ridge = 10.0
    eaves = 6.0

    gabled = shading_height(ridge, Roof.GABLE, eaves)

    assert eaves < gabled < ridge
    assert gabled == pytest.approx(8.0)


def test_a_hip_shades_less_than_a_gable() -> None:
    """It slopes on four sides rather than two."""
    assert shading_height(10.0, Roof.HIP, 6.0) < shading_height(10.0, Roof.GABLE, 6.0)


def test_a_pent_shades_more_than_a_gable() -> None:
    """One whole edge stays at full height."""
    assert shading_height(10.0, Roof.PENT, 6.0) > shading_height(10.0, Roof.GABLE, 6.0)


def test_the_eaves_are_assumed_when_nothing_says() -> None:
    """And the assumption is a fraction of the height, stated in one place."""
    ridge = 8.0

    assumed = shading_height(ridge, Roof.GABLE)

    expected_eaves = DEFAULT_EAVES_FRACTION * ridge
    assert assumed == pytest.approx(expected_eaves + 0.5 * (ridge - expected_eaves))


def test_eaves_above_the_ridge_are_refused_rather_than_believed() -> None:
    """OSM is user-entered and a `building:levels` of 5 on a 6 m building
    happens. Trusting it would make a roof raise a house."""
    assert shading_height(6.0, Roof.GABLE, eaves_m=15.0) == 6.0


def test_a_roof_never_makes_a_building_taller() -> None:
    for roof in Roof:
        assert shading_height(9.0, roof, 4.0) <= 9.0


def test_levels_become_eaves() -> None:
    assert eaves_from_levels(2) == 6.0
    assert eaves_from_levels(None) is None
    assert eaves_from_levels(0) is None, "a building with no storeys says nothing"


def test_the_api_offers_exactly_the_shapes_the_model_knows() -> None:
    """Two lists of the same thing drift. The kind vocabulary already learnt
    this once — the object editor kept offering "Gebäude" after the server had
    stopped knowing it, and a dropdown that writes a value the server rejects is
    a form that fails on save."""
    from ninanatur.api.schemas import RoofShape

    assert {r.value for r in RoofShape} == {r.value for r in Roof}


def test_a_roof_reaches_the_shading_model(tmp_path: object) -> None:
    """The whole point, end to end: a gable shades less than a flat roof of the
    same recorded height."""
    import sqlite3

    from ninanatur.garden.lighting import recompute_light
    from ninanatur.garden.models import BedInput, ObstacleInput
    from ninanatur.garden.store import add_bed, add_obstacle, create_garden, load_garden
    from ninanatur.ingest.db import connect, init_schema

    def sun_with(roof: str) -> float:
        conn: sqlite3.Connection = connect(":memory:", same_thread=False)
        init_schema(conn)
        garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
        add_bed(conn, garden_id, BedInput(
            name="Beet", polygon=[[0, 0], [4, 0], [4, 4], [0, 4]],
            soil_type="loam", moisture="fresh"))
        # Due south, close enough that the roof's own rise decides the answer.
        add_obstacle(conn, garden_id, ObstacleInput(
            kind="house", x=2.0, y=-7.0, shape="rect", width=10.0, depth=8.0,
            height=12.0, roof=roof))
        recompute_light(conn, garden_id)
        bed = load_garden(conn, garden_id).beds[0]
        assert bed.sun_hours is not None
        return float(bed.sun_hours)

    assert sun_with("gable") > sun_with("flat"), "a wedge shades less than a box"
    assert sun_with("unknown") == sun_with("flat"), "silence changes nothing"
