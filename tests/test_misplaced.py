"""A plant standing in light it did not ask for."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.fit.light_fit import light_mismatch_at
from ninanatur.fit.score import MEDIAN_WIDTH
from ninanatur.garden.elements import insert_element
from ninanatur.garden.lightgrid import LightGrid, compute_grid
from ninanatur.garden.lightgrid_store import load_grid
from ninanatur.garden.lighting import recompute_light
from ninanatur.garden.misplaced import misplaced_plantings
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.plantings import add_planting, place_planting
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.solar.light import ellenberg_from_sun_hours
from ninanatur.solar.shading import Obstacle

EIVE = {"source": "EIVE-1.0", "license": "CC-BY-4.0"}
BED = [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]]
#: A tall wall right along the southern edge, so the strip behind it is dark and
#: the far end is not.
WALL = Obstacle(footprint=[(0.0, -1.0), (10.0, -1.0), (10.0, -0.4), (0.0, -0.4)],
                height=9.0)


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    c: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(c)
    # EIVE values: a plant of full sun (9.0, what an open spot gets) and one of
    # deep shade. The sun plant was 8.0 while an open spot read 8 on the old
    # staircase (until 2026-09-21).
    for tid, name, light in ((1, "Sonnenkraut", 9.0), (2, "Schattenkraut", 3.0),
                             (3, "Namenlos", None)):
        c.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (?, ?)", (tid, name))
        if light is not None:
            upsert_trait(c, tid, "ellenberg_l", value_num=light, **EIVE)
    c.commit()
    yield c


def _garden(conn: sqlite3.Connection) -> tuple[int, int]:
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    bed_id = insert_element(
        conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
        name="Beet", points=BED,
    )
    conn.commit()
    return garden_id, bed_id


def _found(conn: sqlite3.Connection, garden_id: int) -> list[object]:
    garden = load_garden(conn, garden_id)
    return list(misplaced_plantings(conn, garden, compute_grid(garden, [WALL])))


def test_a_sun_plant_in_the_shade_is_flagged(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _garden(conn)
    planting_id = add_planting(conn, bed_id, taxon_id=1, quantity=1)
    place_planting(conn, planting_id, 5.0, 0.3)  # right against the wall

    found = _found(conn, garden_id)

    assert len(found) == 1
    assert found[0].problem == "too_dark"  # type: ignore[attr-defined]
    assert found[0].name == "Sonnenkraut"  # type: ignore[attr-defined]


def test_the_same_plant_at_the_far_end_is_fine(conn: sqlite3.Connection) -> None:
    """The whole reason this needed a grid. One number per bed could only ever
    say the bed is wrong, never the corner — and "this bed is too dark" for a
    bed whose far end is in full sun teaches people to ignore advice."""
    garden_id, bed_id = _garden(conn)
    planting_id = add_planting(conn, bed_id, taxon_id=1, quantity=1)
    place_planting(conn, planting_id, 5.0, 7.5)

    assert _found(conn, garden_id) == []


def test_a_shade_plant_in_full_sun_is_flagged_too(conn: sqlite3.Connection) -> None:
    """The forgotten direction. A fern in the open is as misplaced as a sedum
    under a hedge, and only one of the two gets talked about."""
    garden_id, bed_id = _garden(conn)
    planting_id = add_planting(conn, bed_id, taxon_id=2, quantity=1)
    place_planting(conn, planting_id, 5.0, 7.5)

    found = _found(conn, garden_id)

    assert len(found) == 1
    assert found[0].problem == "too_bright"  # type: ignore[attr-defined]


def _spot_value(conn: sqlite3.Connection, garden_id: int, x: float, y: float) -> float:
    """What the spot itself gets, whatever the hours->L convention of the day
    makes of its sun."""
    grid = compute_grid(load_garden(conn, garden_id), [WALL])
    hours = None if grid is None else grid.at(x, y)
    assert hours is not None
    return ellenberg_from_sun_hours(hours)


def _species(conn: sqlite3.Connection, tid: int, light: float, width: float | None) -> None:
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (?, ?)", (tid, f"Art {tid}"))
    upsert_trait(conn, tid, "ellenberg_l", value_num=light, **EIVE)
    if width is not None:
        upsert_trait(conn, tid, "ellenberg_l_nw", value_num=width, **EIVE)
    conn.commit()


def test_a_borderline_difference_is_not_worth_saying(conn: sqlite3.Connection) -> None:
    """Inside the noise of a model whose building heights are mostly assumed,
    and a warning nobody can act on is one people learn to scroll past. The
    list keeps a borderline species; so does the map."""
    garden_id, bed_id = _garden(conn)
    spot = _spot_value(conn, garden_id, 5.0, 7.5)
    # 1.4 half-widths below, on EIVE's median width: borderline, not unsuitable.
    _species(conn, 4, spot - 1.4 * MEDIAN_WIDTH["ellenberg_l"] / 2, None)
    planting_id = add_planting(conn, bed_id, taxon_id=4, quantity=1)
    place_planting(conn, planting_id, 5.0, 7.5)

    assert _found(conn, garden_id) == []


def test_a_wide_niche_the_list_offers_for_full_sun_is_not_called_too_bright(
    conn: sqlite3.Connection,
) -> None:
    """The review of 2026-09-21: an open bed's shortlist offered *Quercus
    robur* (EIVE L 6.24, a niche 6.88 wide), and once planted the map said it
    stood too bright — two rules for one question. It is judged by its width
    now: 0.8 half-widths off in full sun, merely suitable."""
    garden_id, bed_id = _garden(conn)
    spot = _spot_value(conn, garden_id, 5.0, 7.5)
    _species(conn, 5, 6.24, 6.88)
    assert light_mismatch_at(spot, 6.24, 6.88) is None, "the list keeps it"
    planting_id = add_planting(conn, bed_id, taxon_id=5, quantity=1)
    place_planting(conn, planting_id, 5.0, 7.5)

    assert _found(conn, garden_id) == []


def test_a_narrow_niche_at_the_same_distance_is_called_too_bright(
    conn: sqlite3.Connection,
) -> None:
    """The same distance means something else for a specialist."""
    garden_id, bed_id = _garden(conn)
    spot = _spot_value(conn, garden_id, 5.0, 7.5)
    _species(conn, 6, 6.24, 1.5)
    planting_id = add_planting(conn, bed_id, taxon_id=6, quantity=1)
    place_planting(conn, planting_id, 5.0, 7.5)

    [found] = _found(conn, garden_id)
    assert found.problem == "too_bright"  # type: ignore[attr-defined]
    assert light_mismatch_at(spot, 6.24, 1.5) == "too_bright", "and the list leaves it out"


def test_a_raised_bed_is_judged_by_the_light_the_list_ranks_it_by(
    conn: sqlite3.Connection,
) -> None:
    """Its light is sampled at its own height, over a wall that darkens the
    ground grid under it: judged by that grid, a sun plant the list had just
    offered was "too dark" at the very point the bed was measured (review,
    2026-09-21)."""
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    bed_id = insert_element(
        conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0, name="Hochbeet",
        points=[[0, 0], [3, 0], [3, 1.5], [0, 1.5]], soil_type="loam", moisture="fresh",
        height_above_ground=1.0)
    insert_element(conn, garden_id, kind="wall", shape="polygon", x=0, y=0,
                   points=[[-2, -0.6], [5, -0.6], [5, -0.4], [-2, -0.4]], height=2.5)
    conn.commit()
    recompute_light(conn, garden_id)
    stored = load_grid(conn, garden_id)
    assert stored is not None
    bed = load_garden(conn, garden_id).beds[0]
    assert bed.sun_hours is not None
    ground = stored[0].at(1.5, 0.75)
    assert ground is not None and ground < bed.sun_hours - 2, "the ground is darker"
    offered = ellenberg_from_sun_hours(bed.sun_hours) - 0.5
    _species(conn, 7, offered, 2.0)
    assert light_mismatch_at(ellenberg_from_sun_hours(bed.sun_hours), offered, 2.0) is None
    add_planting(conn, bed_id, taxon_id=7, quantity=1)

    assert misplaced_plantings(conn, load_garden(conn, garden_id), stored[0]) == []


def _laid_out(conn: sqlite3.Connection, bed: list[list[float]], hours: float) -> tuple[int, int]:
    """A garden with one bed whose stored light is `hours`, as a rebuild left it."""
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    bed_id = insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=0, y=0,
                            name="Beet", points=bed, soil_type="loam", moisture="fresh")
    conn.execute("UPDATE element SET sun_hours = ?, ellenberg_l = ? WHERE element_id = ?",
                 (hours, ellenberg_from_sun_hours(hours), bed_id))
    conn.commit()
    return garden_id, bed_id


#: A metre-square grid, 10 × 10: dark along the southern row, bright above it.
def _grid(roof_at: int | None = None) -> LightGrid:
    hours: list[float | None] = [2.0 if i < 10 else 9.0 for i in range(100)]
    roof = [False] * 100
    if roof_at is not None:
        hours[roof_at], roof[roof_at] = 12.6, True
    return LightGrid(min_x=0.0, min_y=0.0, cell_m=1.0, cols=10, rows=10, hours=hours, roof=roof)


def test_a_bed_narrower_than_a_cell_is_judged_by_its_own_light(conn: sqlite3.Connection) -> None:
    """No cell centre falls inside it, so the rebuild sampled its middle; the
    cell under that middle is another place (review, 2026-09-21)."""
    garden_id, bed_id = _laid_out(conn, [[2, 0.55], [8, 0.55], [8, 0.95], [2, 0.95]], 8.0)
    _species(conn, 8, ellenberg_from_sun_hours(8.0), 2.0)
    add_planting(conn, bed_id, taxon_id=8, quantity=1)
    garden = load_garden(conn, garden_id)
    assert _grid().mean_over(garden.beds[0].polygon) is None, "narrower than a cell"

    assert misplaced_plantings(conn, garden, _grid()) == []


def test_a_cluster_on_a_roofs_cell_is_not_judged_by_the_roofs_sun(
    conn: sqlite3.Connection,
) -> None:
    """A roof's sun is a real answer to another question: nothing grows on it."""
    garden_id, bed_id = _laid_out(conn, [[0, 0], [10, 0], [10, 1], [0, 1]], 2.0)
    # Suited to the bed's own 2 h; far too dark a plant for a roof's 12.6 h.
    _species(conn, 9, ellenberg_from_sun_hours(2.0), 1.0)
    planting_id = add_planting(conn, bed_id, taxon_id=9, quantity=1)
    garden = load_garden(conn, garden_id)
    bed = garden.beds[0]
    place_planting(conn, planting_id, 4.5 - bed.x, 0.5 - bed.y)
    grid = _grid(roof_at=4)
    assert grid.at(4.5, 0.5) is None, "under a roof, as documented"

    assert misplaced_plantings(conn, load_garden(conn, garden_id), grid) == []


def test_a_species_with_no_indicator_value_is_left_alone(
    conn: sqlite3.Connection,
) -> None:
    """EIVE covers a good part of the flora and not all of it. A plant nobody
    has a value for cannot be said to be in the wrong light."""
    garden_id, bed_id = _garden(conn)
    planting_id = add_planting(conn, bed_id, taxon_id=3, quantity=1)
    place_planting(conn, planting_id, 5.0, 0.3)

    assert _found(conn, garden_id) == []


def test_nothing_is_said_without_a_grid(conn: sqlite3.Connection) -> None:
    garden_id, bed_id = _garden(conn)
    add_planting(conn, bed_id, taxon_id=1, quantity=1)

    assert misplaced_plantings(conn, load_garden(conn, garden_id), None) == []
