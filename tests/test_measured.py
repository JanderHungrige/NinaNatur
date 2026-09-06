"""Measured buildings meeting a garden, and the rule that governs it.

The person standing in the garden outranks the survey. They can see the house;
the model saw it from an aeroplane, some years ago, through whatever was growing
over it.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.measured import IMPLAUSIBLE_M, MATCH_OVERLAP, apply, measure
from ninanatur.garden.models import Garden
from ninanatur.garden.roofs import Roof
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.geo.lod2 import Lod2Building
from ninanatur.geo.surface import SurfaceWindow
from ninanatur.geo.surroundings import HeightSource
from ninanatur.ingest.db import connect, init_schema

HOUSE = [[-4.0, -10.0], [4.0, -10.0], [4.0, -4.0], [-4.0, -4.0]]


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    connection: sqlite3.Connection = connect(":memory:")
    init_schema(connection)
    yield connection


def _garden(conn: sqlite3.Connection, *, height_source: str = "osm_levels") -> Garden:
    garden_id = create_garden(conn, name="G", latitude=51.0, longitude=6.0)
    # x/y zero, so `footprint` is exactly HOUSE. An element's footprint is its
    # points *plus* its origin, and putting the origin at (0, -7) as well moved
    # the house to y -17..-11 — which two of these tests then passed against by
    # luck, because a uniform window says the same thing everywhere.
    element_id = insert_element(
        conn, garden_id, kind="house", shape="polygon", x=0.0, y=0.0,
        name="Nachbarhaus", points=HOUSE, height=9.0,
    )
    conn.execute(
        "UPDATE element SET height_source = ? WHERE element_id = ?",
        (height_source, element_id),
    )
    conn.commit()
    return load_garden(conn, garden_id)


def _surveyed(height: float, roof: Roof = Roof.GABLE, at: tuple[float, float] = (0.0, -7.0),
              eaves: float | None = None) -> Lod2Building:
    x, y = at
    return Lod2Building(
        building_id="DE_X", roof=roof, height_m=height, eaves_m=eaves,
        outline=[(x - 4, y - 3), (x + 4, y - 3), (x + 4, y + 3), (x - 4, y + 3)],
    )


def _surface(height: float, size: int = 80) -> SurfaceWindow:
    return SurfaceWindow(
        min_x=-20.0, min_y=-20.0, cell_m=0.5, cols=size, rows=size,
        heights=[height] * (size * size),
        source="Test", licence="—", attribution="—",
    )


def test_a_surveyed_height_replaces_an_assumed_one(conn: sqlite3.Connection) -> None:
    garden = _garden(conn)
    [found] = measure(garden, surveyed=[_surveyed(12.4)])

    assert found.height_m == pytest.approx(12.4)
    assert found.source is HeightSource.SURVEYED

    apply(conn, [found])
    after = load_garden(conn, garden.garden_id).obstacles[0]
    assert after.height == pytest.approx(12.4)
    assert after.height_source == "surveyed"


def test_the_survey_never_overwrites_what_somebody_typed(conn: sqlite3.Connection) -> None:
    """The whole rule, and it holds in two places: nothing is even measured for
    a user-set building, and the write refuses it a second time in SQL."""
    garden = _garden(conn, height_source="user")

    assert measure(garden, surveyed=[_surveyed(12.4)]) == []

    # And if something did get through, the update itself declines.
    from ninanatur.garden.measured import Measurement

    apply(conn, [Measurement(obstacle_id=garden.obstacles[0].obstacle_id,
                             height_m=99.0, source=HeightSource.SURVEYED)])
    assert load_garden(conn, garden.garden_id).obstacles[0].height == pytest.approx(9.0)


def test_a_surveyed_roof_arrives_with_its_height(conn: sqlite3.Connection) -> None:
    """Wave 16 asks a person to pick this for buildings that are not theirs."""
    garden = _garden(conn)
    [found] = measure(garden, surveyed=[_surveyed(12.0, Roof.HIP, eaves=8.5)])
    apply(conn, [found])

    after = load_garden(conn, garden.garden_id).obstacles[0]
    assert after.roof == "hip"
    assert after.roof_source == "surveyed"
    assert after.eaves_m == pytest.approx(8.5)


def test_a_surveyed_answer_of_mix_is_stored_as_mix(conn: sqlite3.Connection) -> None:
    """Not folded into unknown. A surveyor looked."""
    garden = _garden(conn)
    apply(conn, measure(garden, surveyed=[_surveyed(12.0, Roof.MIX)]))

    assert load_garden(conn, garden.garden_id).obstacles[0].roof == "mix"


def test_the_raster_answers_where_no_survey_reaches(conn: sqlite3.Connection) -> None:
    garden = _garden(conn)
    [found] = measure(garden, surface=_surface(11.0))

    assert found.source is HeightSource.MEASURED
    assert found.height_m == pytest.approx(11.0, abs=0.2)
    assert found.roof is None, "a raster cannot see a roof shape"


def test_a_building_too_far_away_is_not_this_building(conn: sqlite3.Connection) -> None:
    """A terraced row decides this: neighbours stand five to seven metres apart,
    so a looser rule hands a house its neighbour's roof."""
    garden = _garden(conn)
    assert measure(garden, surveyed=[_surveyed(12.0, at=(40.0, -7.0))]) == []
    assert MATCH_OVERLAP > 0.3


def test_two_sources_that_disagree_wildly_mean_the_match_is_wrong(
    conn: sqlite3.Connection,
) -> None:
    """Position alone will occasionally pair a garage with the house behind it,
    and the tell is that the numbers are nowhere near each other. Then the
    raster wins — it was measured over the footprint actually drawn here."""
    garden = _garden(conn)

    [found] = measure(garden, surveyed=[_surveyed(30.0)], surface=_surface(9.0))

    assert found.source is HeightSource.MEASURED
    assert abs(30.0 - 9.0) > IMPLAUSIBLE_M


def test_two_sources_that_agree_leave_it_to_the_survey(conn: sqlite3.Connection) -> None:
    """It measured this building against its own ground plan and states its
    accuracy; the raster is a percentile over an outline somebody drew in OSM."""
    garden = _garden(conn)

    [found] = measure(garden, surveyed=[_surveyed(11.5)], surface=_surface(10.8))

    assert found.source is HeightSource.SURVEYED
    assert found.height_m == pytest.approx(11.5)


def _with_crown(window: SurfaceWindow, over: float, height: float) -> SurfaceWindow:
    """Put a crown over the northern `over` metres of the window."""
    values = list(window.heights)
    for row in range(window.rows):
        y = window.min_y + (row + 0.5) * window.cell_m
        if y > -4.0 - over:
            for col in range(window.cols):
                values[row * window.cols + col] = height
    return SurfaceWindow(**{**vars(window), "heights": values})


def test_a_roof_with_a_tree_over_one_end_is_not_written(conn: sqlite3.Connection) -> None:
    """The Cologne case: a 30 m² outbuilding read 17.0 m because a beech hangs
    over it. The honest response is to keep the assumption, not to publish a
    number that is probably the tree."""
    garden = _garden(conn)
    window = _with_crown(_surface(9.0), over=2.0, height=24.0)

    changed = apply(conn, measure(garden, surface=window))

    assert changed == 0
    assert load_garden(conn, garden.garden_id).obstacles[0].height == pytest.approx(9.0)


def test_a_building_mostly_under_canopy_is_measured_as_the_canopy(
    conn: sqlite3.Connection,
) -> None:
    """A limitation, asserted so that nobody removes it by accident.

    The detector compares the top of the distribution against its middle. When a
    crown covers most of a roof the crown *is* the middle, the distribution is
    uniform, and it looks clean. There is no signal left in the raster to find.

    Where the official 3D model reaches, this cannot happen — it measured the
    building rather than what is over it, which is the strongest argument for
    preferring the survey wherever it exists.
    """
    garden = _garden(conn)
    window = _with_crown(_surface(9.0), over=100.0, height=24.0)

    [found] = measure(garden, surface=window)

    assert found.suspect is False
    assert found.height_m == pytest.approx(24.0), "the crown, and nothing says so"


def test_nothing_at_all_is_an_ordinary_answer(conn: sqlite3.Connection) -> None:
    """No service for this state, nothing near enough to match, or every
    building already spoken for."""
    garden = _garden(conn)
    assert measure(garden) == []
    assert apply(conn, []) == 0


def test_a_garage_beside_a_house_is_not_the_house(conn: sqlite3.Connection) -> None:
    """The failure a centre-distance rule produced against Cologne: a 47 m²
    terraced house was handed the 2.7 m pent roof of the garage beside it,
    because the garage's centre was nearer than the tolerance and nothing else
    was consulted.

    A garage does not overlap a house, which is why the rule is overlap.
    """
    garden = _garden(conn)
    garage = Lod2Building(
        building_id="DE_GARAGE", roof=Roof.PENT, height_m=2.7, eaves_m=2.15,
        # Six metres east of the house, so its centre is well inside any
        # sensible distance tolerance — and it shares no ground with it.
        outline=[(6.0, -9.0), (12.0, -9.0), (12.0, -5.0), (6.0, -5.0)],
    )

    assert measure(garden, surveyed=[garage]) == []


def test_the_house_wins_over_the_garage_when_both_are_offered(
    conn: sqlite3.Connection,
) -> None:
    """Not merely "the garage is rejected" — the right building is chosen from a
    tile that contains both, which is every tile."""
    garden = _garden(conn)
    garage = Lod2Building(
        building_id="DE_GARAGE", roof=Roof.PENT, height_m=2.7, eaves_m=None,
        outline=[(6.0, -9.0), (12.0, -9.0), (12.0, -5.0), (6.0, -5.0)],
    )

    [found] = measure(garden, surveyed=[garage, _surveyed(11.4, Roof.MIX)])

    assert found.height_m == pytest.approx(11.4)
    assert found.roof is Roof.MIX
