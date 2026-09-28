"""How fine the light grid is: the finest cell its cost allows (docs 64, 117).

Split out of `test_light_grid.py` when the raster's cost model (Wave 26) grew
past what that file could hold. The estimate is the model's own
(`estimate_ms`), so these assert the choice agrees with it rather than
copying its constants.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from ninanatur.garden import lightgrid
from ninanatur.garden.lightcells import Roofed, surfaces_of
from ninanatur.garden.lightgrid import GRID_BUDGET_S, cell_size_for, compute_grid
from ninanatur.garden.lightgrid_cost import estimate_ms
from ninanatur.garden.lightgrid_extent import MAX_CELLS, cells_at, stands_in
from ninanatur.garden.lightview import shading_obstacles
from ninanatur.garden.models import ObstacleInput
from ninanatur.garden.store import add_obstacle, create_garden, load_garden
from ninanatur.ingest.db import connect, init_schema


def _seconds(width: float, depth: float, cell: float, parts: int,
             near: int | None = None) -> float:
    return estimate_ms(cells_at(width, depth, cell), parts, near) / 1000


def test_a_small_garden_gets_the_finest_cell() -> None:
    assert cell_size_for(10.0, 8.0) == 0.5


def test_a_large_plot_gets_a_coarser_one_rather_than_a_long_wait() -> None:
    """The ladder exists so a big plot waits the same as a small one, not longer."""
    cell = cell_size_for(150.0, 130.0, parts=40)

    assert _seconds(150.0, 130.0, cell, 40) <= GRID_BUDGET_S
    assert cell > 1.0


def test_the_budget_is_time_rather_than_a_cell_count() -> None:
    """A cell is not a fixed price: it costs what stands around it. (Since the
    raster, doc 117, it is mostly what stands that costs.)"""
    quiet = cell_size_for(120.0, 120.0, parts=2)
    crowded = cell_size_for(120.0, 120.0, parts=40)

    assert quiet < crowded, "the same plot gets a finer grid when less stands on it"
    for cell, parts in ((quiet, 2), (crowded, 40)):
        assert _seconds(120.0, 120.0, cell, parts) <= GRID_BUDGET_S


def test_neighbours_outside_the_grid_do_not_coarsen_it() -> None:
    """A garden from the map has forty neighbours' houses round its plot, and
    their shadows reach the grid only while they are long: the ordinary case
    keeps the finest cell, where forty houses standing on it do not (doc 117)."""
    around = cell_size_for(60.0, 60.0, parts=41, near=1)
    on_it = cell_size_for(60.0, 60.0, parts=41, near=41)
    assert around == 0.5 and on_it > around
    assert _seconds(60.0, 60.0, around, 41, near=1) <= GRID_BUDGET_S


def test_an_ordinary_garden_is_no_longer_held_at_a_metre() -> None:
    """The complaint this replaced: a 24 x 33 m plot with three buildings was
    given 2 m cells by a flat 600-cell cap, and the map read coarse."""
    assert cell_size_for(24.0, 33.0, parts=3) == 0.5


def test_even_a_field_stays_bounded() -> None:
    cell = cell_size_for(1000.0, 1000.0, parts=40)
    assert cell == 5.0, "the ladder ends; it does not grow without limit"


def test_the_cap_on_cells_holds_for_the_grid_that_is_built() -> None:
    """A map is a list kept and sent. With cells nearly free, a plain 480 m
    plot was given 0.5 m cells — 923,000 of them, 16 MB a page load (review,
    2026-09-22). The cap stops at the rung that fits it."""
    cell = cell_size_for(480.0, 480.0)
    assert cells_at(480.0, 480.0, cell) <= MAX_CELLS
    assert cells_at(480.0, 480.0, 0.5) > MAX_CELLS, "the case is one the cap decides"


def test_terrain_costs_every_cell_a_little() -> None:
    assert estimate_ms(10_000, 5, 1, terrain=True) > estimate_ms(10_000, 5, 1)


def test_a_cell_with_a_surface_of_its_own_is_priced_by_the_cell() -> None:
    """Weighing every moment on each cell's own surface (doc 119) costs per
    cell, not per part — and it is the cells' surfaces that turn it on, so a
    pitched roof does even where nothing was surveyed (review, 2026-09-22)."""
    from ninanatur.garden.lightgrid_cost import TILTED_CELL_MS

    for parts, near in ((1, 1), (40, 5)):
        level = estimate_ms(10_000, parts, near)
        tilted = estimate_ms(10_000, parts, near, tilted=True)
        assert tilted - level == pytest.approx(10_000 * TILTED_CELL_MS)


def test_a_pitched_roof_alone_buys_the_tilted_cell(conn: sqlite3.Connection,
                                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """No terrain at all, one gabled house: its roof cells have surfaces, so
    the sweep takes the dearer path and the estimate must know."""
    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    add_obstacle(conn, garden_id, ObstacleInput(kind="house", x=0, y=0, shape="rect",
                                                width=12, depth=10, height=9, roof="gable",
                                                label="H"))
    conn.commit()
    garden = load_garden(conn, garden_id)
    asked: list[tuple[bool, int, int]] = []

    def spy(width: float, depth: float, parts: int = 0, near: int | None = None,
            terrain: bool = False, deciduous: bool = False, tilted: bool = False,
            near_planes: int = 0, far_planes: int = 0, **crowns_and_more: object) -> float:
        asked.append((tilted, near_planes, far_planes))
        return 1.0

    monkeypatch.setattr(lightgrid, "cell_size_for", spy)
    compute_grid(garden, shading_obstacles(conn, garden))
    # Its two pitch planes stand on the grid, and are priced as near planes.
    assert asked == [(True, 2, 0)]


def test_a_roofs_planes_are_priced_per_plane_like_the_walls_they_resemble() -> None:
    """A plane is one more cut of the ray at every moment its part is asked
    about, so it costs per plane — near dearer than far, like parts — and only
    a little per cell. Priced per cell alone, 36 hipped houses were estimated
    at 4.7 s and took 7.1 (review, 2026-09-28)."""
    from ninanatur.garden import lightgrid_cost as cost

    swept = 1.0 + cost.SKY_DIRECTIONS / cost.SEASON_MOMENTS
    plain = estimate_ms(10_000, 5, 5)
    for near, far in ((10, 0), (0, 10), (6, 4)):
        roofed = estimate_ms(10_000, 5, 5, near_planes=near, far_planes=far)
        per_plane = cost.NEAR_PLANE_MS * near + cost.FAR_PLANE_MS * far
        per_cell = 10_000 * cost.PLANE_CELL_MS * (near + far)
        assert roofed - plain == pytest.approx(swept * (per_plane + per_cell))
    assert cost.NEAR_PLANE_MS > cost.FAR_PLANE_MS
    # A small grid still pays for its planes: they do not cost by the cell.
    assert estimate_ms(100, 5, 5, near_planes=72) - estimate_ms(100, 5, 5) > 1_000


def test_the_sky_is_priced_by_the_directions_it_sweeps() -> None:
    """The estimate's constants were fitted to the sun alone; the sky adds its
    patches to every part and cell (doc 118). Its counts are the sky's and the
    season's as they are, not numbers copied once."""
    from ninanatur.garden import lightgrid_cost as extent
    from ninanatur.solar.position import Location
    from ninanatur.solar.raster import moments_for
    from ninanatur.solar.sky import TREGENZA, sky_directions

    assert len(sky_directions(7).azimuth) == extent.SKY_DIRECTIONS
    assert len(sky_directions(3, split=TREGENZA).azimuth) == extent.BARE_SKY_DIRECTIONS
    assert len(moments_for(Location(51.25, 7.15)).azimuth) == extent.SEASON_MOMENTS
    evergreen = estimate_ms(10_000, 5, 1) - extent.GRID_FIXED_MS
    deciduous = estimate_ms(10_000, 5, 1, deciduous=True) - extent.GRID_FIXED_MS
    swept = extent.SEASON_MOMENTS + extent.SKY_DIRECTIONS
    assert deciduous / evergreen == pytest.approx((swept + extent.BARE_SKY_DIRECTIONS) / swept)


@pytest.fixture()
def conn() -> Iterator[sqlite3.Connection]:
    made: sqlite3.Connection = connect(":memory:", same_thread=False)
    init_schema(made)
    yield made


def test_the_grid_counts_the_parts_standing_on_it(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What is asked about: two houses drawn on the plot stand on the grid,
    three neighbours from the map stand outside it. Counted wrong either way,
    forty drawn houses would be given a cell the budget cannot pay for."""
    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    add_obstacle(conn, garden_id, ObstacleInput(kind="garden", x=0, y=0, shape="rect",
                                                width=20, depth=30, label="Grundstück"))
    for x in (-4.0, 4.0):
        add_obstacle(conn, garden_id, ObstacleInput(kind="shed", x=x, y=0, shape="rect",
                                                    width=3, depth=3, height=2.5, label="S"))
    for y in (60.0, 80.0, 100.0):
        add_obstacle(conn, garden_id, ObstacleInput(kind="house", x=0, y=y, shape="rect",
                                                    width=10, depth=8, height=9, label="N"))
    conn.execute("UPDATE element SET roof_source = 'osm', height_source = 'osm'"
                 " WHERE kind = 'house'")
    conn.commit()
    garden = load_garden(conn, garden_id)
    asked: list[tuple[int, int | None]] = []

    def spy(width: float, depth: float, parts: int = 0, near: int | None = None,
            *what: object, **more: object) -> float:
        asked.append((parts, near))  # the rest is terrain, leaves, tilt and crowns
        return 1.0

    monkeypatch.setattr(lightgrid, "cell_size_for", spy)
    compute_grid(garden, shading_obstacles(conn, garden))
    assert asked == [(5, 2)]
    box = (-10.0, -15.0, 10.0, 15.0)
    assert stands_in([(9.0, 14.0), (12.0, 14.0), (12.0, 18.0)], box)
    assert not stands_in([(10.5, 15.5), (12.0, 15.5), (12.0, 18.0)], box)


def test_a_roof_nobody_measured_stands_on_the_lowest_ground() -> None:
    """Unanswered, and at the lowest ground: at zero on a garden 150 m up, it
    swept every shadow from 150 m below the garden and tripled the grid's cost
    (review, 2026-09-22)."""
    roof = Roofed(outline=[(-2.0, -2.0), (2.0, -2.0), (2.0, 2.0), (-2.0, 2.0)],
                  surface=None, element_id=7, base=150.0)
    rows = surfaces_of([-1.0, 0.0, 1.0, 5.0], [0.0], None, None, 150.0, [roof])
    unanswered = [s for s in rows[0] if not s.answered]
    assert len(unanswered) == 3 and all(s.z == 150.0 for s in unanswered)


def test_a_crown_off_the_grid_is_priced_above_a_far_part(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A crown just past the grid's edge throws its shadow in at most moments,
    and cost more than the far price said (doc 121, review 2026-09-28): the
    grid counts the crowns that stand off it, and each is priced above a far
    part — one on the grid is priced as the part it is."""
    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    add_obstacle(conn, garden_id, ObstacleInput(kind="garden", x=0, y=0, shape="rect",
                                                width=20, depth=20, label="Garten"))
    for x in (0.0, 40.0):
        add_obstacle(conn, garden_id, ObstacleInput(kind="tree", x=x, y=0, shape="circle",
                                                    width=6, height=10, label="Linde"))
    conn.execute("UPDATE element SET height_source = 'measured' WHERE kind = 'tree' AND x > 20")
    conn.commit()
    garden = load_garden(conn, garden_id)
    asked: list[tuple[int | None, int]] = []

    def spy(width: float, depth: float, parts: int = 0, near: int | None = None,
            *what: object, far_crowns: int = 0, **more: object) -> float:
        asked.append((near, far_crowns))
        return 1.0

    monkeypatch.setattr(lightgrid, "cell_size_for", spy)
    compute_grid(garden, shading_obstacles(conn, garden))
    assert asked == [(1, 1)], "the tree on the plot is near; the laser's, 40 m out, is not"
    assert estimate_ms(10_000, 1, 0, far_crowns=1) > estimate_ms(10_000, 1, 0)


def test_a_neighbour_within_its_height_of_the_grid_is_priced_above_a_far_part(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A house from the map 5 m past the grid's edge throws its shadow in at
    most moments; one 30 m out only while shadows are long. 36 of the first
    kind took 1.8 s where the far price said 1.0 (review of feature 5,
    2026-09-28): each is counted as reaching, and priced above a far part."""
    garden_id = create_garden(conn, name="G", latitude=51.25, longitude=7.15)
    add_obstacle(conn, garden_id, ObstacleInput(kind="garden", x=0, y=0, shape="rect",
                                                width=20, depth=20, label="Garten"))
    # The grid's box is the plot and 5 m: its edge at y = 15.
    for y in (24.0, 49.0):
        add_obstacle(conn, garden_id, ObstacleInput(kind="house", x=0, y=y, shape="rect",
                                                    width=10, depth=8, height=9, label="N"))
    conn.execute("UPDATE element SET roof_source = 'osm', height_source = 'osm'"
                 " WHERE kind = 'house'")
    conn.commit()
    garden = load_garden(conn, garden_id)
    asked: list[tuple[int | None, int]] = []

    def spy(width: float, depth: float, parts: int = 0, near: int | None = None,
            *what: object, reaching: int = 0, **more: object) -> float:
        asked.append((near, reaching))
        return 1.0

    monkeypatch.setattr(lightgrid, "cell_size_for", spy)
    compute_grid(garden, shading_obstacles(conn, garden))
    assert asked == [(0, 1)], "5 m past the edge it reaches in; 30 m out it does not"
    assert estimate_ms(10_000, 2, 0, reaching=1) > estimate_ms(10_000, 2, 0)
