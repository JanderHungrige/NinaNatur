"""Which light a cluster is judged by, on a grid laid out by hand.

Split from `test_misplaced.py` as the review of 2026-09-21 added the cases: a
cluster with a cell of its own reads it; one without — unplaced, in a raised or
too narrow bed, under a roof — is judged by its bed's own light, the value the
list ranks the bed by.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden.elements import insert_element
from ninanatur.garden.lightgrid import LightGrid
from ninanatur.garden.misplaced import misplaced_plantings
from ninanatur.garden.models import PLANTING_KIND
from ninanatur.garden.plantings import add_planting, place_planting
from ninanatur.garden.store import create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema
from ninanatur.ingest.provenance import upsert_trait
from ninanatur.solar.light import ellenberg_from_sun_hours

EIVE = {"source": "EIVE-1.0", "license": "CC-BY-4.0"}


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    c: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(c)
    yield c


def _species(conn: sqlite3.Connection, tid: int, light: float, width: float | None) -> None:
    conn.execute("INSERT INTO taxon (taxon_id, canonical_name) VALUES (?, ?)", (tid, f"Art {tid}"))
    upsert_trait(conn, tid, "ellenberg_l", value_num=light, **EIVE)
    if width is not None:
        upsert_trait(conn, tid, "ellenberg_l_nw", value_num=width, **EIVE)
    conn.commit()


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


def test_a_placed_cluster_in_a_narrow_border_is_not_judged_by_a_cell_outside_it(
    conn: sqlite3.Connection,
) -> None:
    """No cell centre lies inside a border narrower than a cell, so a cluster's
    cell is centred outside it — here in the dark row standing for the wall it
    borders — and a plant the list had just offered was warned as too dark
    (review, 2026-09-21). The border is judged as a whole, by its own light."""
    garden_id, bed_id = _laid_out(conn, [[0, 0.55], [10, 0.55], [10, 0.95], [0, 0.95]], 9.0)
    _species(conn, 10, 9.0, 2.0)
    planting_id = add_planting(conn, bed_id, taxon_id=10, quantity=1)
    place_planting(conn, planting_id, 1.0, 0.75)
    assert _grid().at(1.0, 0.75) == 2.0, "the cell under the cluster is the dark one"

    assert misplaced_plantings(conn, load_garden(conn, garden_id), _grid()) == []


def test_an_unplaced_cluster_is_judged_by_what_the_list_ranked_its_bed_by(
    conn: sqlite3.Connection,
) -> None:
    """Planted from the list, a cluster has no position. Read at the bed's middle
    — a bright cell of a bed half in shade — a species the list had just offered
    was warned about at once (review, 2026-09-21)."""
    garden_id, bed_id = _laid_out(conn, [[0, 0], [10, 0], [10, 2], [0, 2]], 5.5)
    _species(conn, 11, ellenberg_from_sun_hours(5.5), 1.0)
    add_planting(conn, bed_id, taxon_id=11, quantity=1)
    assert _grid().at(5.0, 1.0) == 9.0, "the middle is in the bright row"

    assert misplaced_plantings(conn, load_garden(conn, garden_id), _grid()) == []


def test_a_bed_drawn_since_the_last_press_is_judged_where_it_stands(
    conn: sqlite3.Connection,
) -> None:
    """It has no stored light yet, but the stored map covers its ground: an
    unplaced sun plant in its dark half-and-half is still warned about
    (review, 2026-09-21)."""
    garden_id, bed_id = _laid_out(conn, [[0, 0], [10, 0], [10, 2], [0, 2]], 5.5)
    conn.execute("UPDATE element SET sun_hours = NULL, ellenberg_l = NULL WHERE element_id = ?",
                 (bed_id,))
    _species(conn, 12, 9.0, 1.0)
    add_planting(conn, bed_id, taxon_id=12, quantity=1)

    [found] = misplaced_plantings(conn, load_garden(conn, garden_id), _grid())
    assert (found.problem, found.sun_hours) == ("too_dark", 5.5)  # type: ignore[attr-defined]


def test_a_cluster_whose_cell_is_centred_outside_its_bed_is_judged_by_the_bed(
    conn: sqlite3.Connection,
) -> None:
    """A metre-wide border set a little off the grid: its northern row of cells
    counts toward its mean, its southern row is centred outside it — in the
    hedge it borders — and read 0 h for a plant the list had just offered
    (review, 2026-09-22). A cell is the cluster's only where it is the bed's."""
    garden_id, bed_id = _laid_out(conn, [[0, 0.55], [10, 0.55], [10, 1.55], [0, 1.55]], 9.0)
    _species(conn, 13, 9.0, 2.0)
    planting_id = add_planting(conn, bed_id, taxon_id=13, quantity=1)
    bed = load_garden(conn, garden_id).beds[0]
    place_planting(conn, planting_id, 1.0, 0.75)
    assert _grid().mean_over(bed.polygon) == 9.0, "only the northern row is the bed's"

    assert misplaced_plantings(conn, load_garden(conn, garden_id), _grid()) == []


def test_a_placed_cluster_is_judged_where_the_plan_put_it(conn: sqlite3.Connection) -> None:
    """The plan drags and draws a cluster in garden metres, and a bed is stored
    round its own centre; the server added that centre once more, and judged
    every placed cluster somewhere else (review, 2026-09-22)."""
    garden_id = create_garden(conn, name="G", latitude=52.5, longitude=13.4)
    # As `store.add_bed` keeps it: the corners round its centre, which is x, y.
    bed_id = insert_element(conn, garden_id, kind=PLANTING_KIND, shape="polygon", x=5, y=1,
                            name="Beet", points=[[-5, -1], [5, -1], [5, 1], [-5, 1]],
                            soil_type="loam", moisture="fresh")
    conn.execute("UPDATE element SET sun_hours = 5.5 WHERE element_id = ?", (bed_id,))
    conn.commit()
    _species(conn, 14, 9.0, 1.0)
    planting_id = add_planting(conn, bed_id, taxon_id=14, quantity=1)
    place_planting(conn, planting_id, 1.0, 0.5)  # as useClusterDrag sends it: the dark row
    bed = load_garden(conn, garden_id).beds[0]
    assert (bed.x, bed.polygon[0]) == (5, [0, 0]), "stored round its centre"

    [found] = misplaced_plantings(conn, load_garden(conn, garden_id), _grid())
    assert (found.problem, found.sun_hours) == ("too_dark", 2.0)  # type: ignore[attr-defined]


def test_a_cluster_on_a_roofs_cell_is_not_judged_by_the_roofs_sun(
    conn: sqlite3.Connection,
) -> None:
    """A roof's sun is a real answer to another question: nothing grows on it."""
    garden_id, bed_id = _laid_out(conn, [[0, 0], [10, 0], [10, 1], [0, 1]], 2.0)
    # Suited to the bed's own 2 h; far too dark a plant for a roof's 12.6 h.
    _species(conn, 9, ellenberg_from_sun_hours(2.0), 1.0)
    planting_id = add_planting(conn, bed_id, taxon_id=9, quantity=1)
    place_planting(conn, planting_id, 4.5, 0.5)
    grid = _grid(roof_at=4)
    assert grid.at(4.5, 0.5) is None, "under a roof, as documented"

    assert misplaced_plantings(conn, load_garden(conn, garden_id), grid) == []
